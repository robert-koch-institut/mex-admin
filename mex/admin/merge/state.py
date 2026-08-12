from collections.abc import Generator, Iterable
from typing import Literal

import reflex as rx
from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error, response_payload
from mex.admin.label_var import label_var
from mex.admin.models import SearchResult, ValueLabelCheckboxItem
from mex.admin.state import State
from mex.admin.transform import transform_models_to_search_results
from mex.admin.utils import resolve_editor_value
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.models import MERGED_MODEL_CLASSES
from mex.common.transform import ensure_prefix


class MergeState(State):
    """State management for the merge items page."""

    results_extracted: list[SearchResult] = []
    results_merged: list[SearchResult] = []
    entity_types_merged: dict[str, bool] = {
        k.stemType: False for k in MERGED_MODEL_CLASSES
    }
    entity_types_extracted: dict[str, bool] = {
        k.stemType: False for k in MERGED_MODEL_CLASSES
    }
    is_loading: bool = True
    limit: int = 50
    query_strings: dict[Literal["merged", "extracted"], str] = {
        "merged": "",
        "extracted": "",
    }
    results_count: dict[str, int] = {
        "merged": 0,
        "extracted": 0,
    }
    total_count: dict[str, int] = {
        "merged": 0,
        "extracted": 0,
    }
    selected_items: dict[str, int | None] = {
        "merged": None,
        "extracted": None,
    }

    @rx.var
    def label_entity_types_merged(self) -> list[ValueLabelCheckboxItem]:
        """Get entity_types_merged with value, label and checked."""
        return sorted(
            [
                ValueLabelCheckboxItem(
                    label=self._locale_service.get_ui_label(self.current_locale, key),
                    value=key,
                    checked=self.entity_types_merged[key],
                )
                for key in self.entity_types_merged
            ],
            key=lambda x: x.label,
        )

    @rx.var
    def label_entity_types_extracted(self) -> list[ValueLabelCheckboxItem]:
        """Get entity_types_extracted with value, label and checked."""
        return sorted(
            [
                ValueLabelCheckboxItem(
                    label=self._locale_service.get_ui_label(self.current_locale, key),
                    value=key,
                    checked=self.entity_types_extracted[key],
                )
                for key in self.entity_types_extracted
            ],
            key=lambda x: x.label,
        )

    @rx.event
    def select_item(self, category: Literal["merged", "extracted"], index: int) -> None:
        """Select or deselect a merged or extracted item based on the index."""
        if self.selected_items[category] == index:
            self.selected_items[category] = None
            return
        self.selected_items[category] = index

    @rx.event
    def handle_submit(
        self, category: Literal["merged", "extracted"], form_data: str
    ) -> None:
        """Handle the extracted or merged form submit."""
        self.query_strings[category] = form_data

    @rx.event
    def set_entity_type_merged(
        self,
        index: str,
        value: bool,  # noqa: FBT001
    ) -> None:
        """Set the entity type for filtering and refresh the merged results."""
        self.entity_types_merged[index] = value

    @rx.event
    def set_entity_type_extracted(
        self,
        index: str,
        value: bool,  # noqa: FBT001
    ) -> None:
        """Set the entity type for filtering and refresh the extracted results."""
        self.entity_types_extracted[index] = value

    @rx.event
    def clear_input(self, category: Literal["merged", "extracted"]) -> None:
        """Clear the merged or extracted search input and reset the results."""
        self.query_strings[category] = ""
        self.selected_items[category] = None
        self.results_count[category] = 0
        self.total_count[category] = 0
        if category == "merged":
            self.entity_types_merged = dict.fromkeys(self.entity_types_merged, False)
            self.results_merged = []
        else:
            self.entity_types_extracted = dict.fromkeys(
                self.entity_types_extracted, False
            )
            self.results_extracted = []

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for result_list in (self.results_merged, self.results_extracted):
            for result in result_list:
                for preview in result.preview:
                    if preview.identifier and not preview.text:
                        async with self:
                            await resolve_editor_value(preview)

    @rx.event
    def refresh(
        self,
        categories: Iterable[Literal["merged", "extracted"]] = ("merged", "extracted"),
    ) -> Generator[EventSpec | None]:
        """Refresh the search results for the specified category."""
        if "merged" in categories:
            self.selected_items["merged"] = None
            yield from self._refresh_merged()
        if "extracted" in categories:
            self.selected_items["extracted"] = None
            yield from self._refresh_extracted()

    def _refresh_merged(self) -> Generator[EventSpec | None]:
        """Refresh the search results for merged items."""
        connector = BackendApiConnector.get()
        entity_type = [
            ensure_prefix(k, "Merged") for k, v in self.entity_types_merged.items() if v
        ]
        self.is_loading = True
        yield None
        try:
            response = connector.fetch_preview_items(
                query_string=self.query_strings["merged"],
                entity_type=entity_type,
                limit=self.limit,
            )
        except RequestException as exc:
            self.is_loading = False
            self.results_merged = []
            self.results_count["merged"] = 0
            self.total_count["merged"] = 0
            yield None
            yield from escalate_error(
                "backend", "error fetching merged items", response_payload(exc)
            )
        else:
            self.is_loading = False
            self.results_merged = transform_models_to_search_results(response.items)
            self.results_count["merged"] = len(self.results_merged)
            self.total_count["merged"] = response.total

    def _refresh_extracted(self) -> Generator[EventSpec | None]:
        """Refresh the search results for extracted items."""
        connector = BackendApiConnector.get()
        entity_type = [
            ensure_prefix(k, "Extracted")
            for k, v in self.entity_types_extracted.items()
            if v
        ]
        self.results_extracted = self.results_extracted
        self.is_loading = True
        yield None
        try:
            response = connector.fetch_extracted_items(
                query_string=self.query_strings["extracted"],
                entity_type=entity_type,
                limit=self.limit,
            )
        except RequestException as exc:
            self.is_loading = False
            self.results_extracted = []
            self.results_count["extracted"] = 0
            self.total_count["extracted"] = 0
            yield None
            yield from escalate_error(
                "backend", "error fetching extracted items", response_payload(exc)
            )
        else:
            self.is_loading = False
            self.results_extracted = transform_models_to_search_results(response.items)
            self.results_count["extracted"] = len(self.results_extracted)
            self.total_count["extracted"] = response.total

    @rx.event
    def submit_merge_items(self) -> Generator[EventSpec]:
        """Submit merging of the items."""
        yield rx.toast.error(
            title="Not Implemented",
            description="Item merging is not yet implemented.",
            class_name="editor-toast",
            close_button=True,
            dismissible=True,
            duration=5000,
        )

    @label_var(
        label_id="merge.result_summary.format", deps=["results_count", "total_count"]
    )
    def label_result_summary_format_merged(self) -> list[int]:
        """Label for result_summary.format."""
        return [self.results_count["merged"], self.total_count["merged"]]

    @label_var(
        label_id="merge.result_summary.format", deps=["results_count", "total_count"]
    )
    def label_result_summary_format_extracted(self) -> list[int]:
        """Label for result_summary.format."""
        return [self.results_count["extracted"], self.total_count["extracted"]]

    @label_var(label_id="merge.submit_button")
    def label_submit_button(self) -> None:
        """Label for submit_button."""

    @label_var(label_id="merge.search_input.placeholder")
    def label_search_input_placeholder(self) -> None:
        """Label for search_input.placeholder."""

    @label_var(label_id="merge.search.title_format")
    def label_search_title_merged(self) -> list[str]:
        """Label for search.title_merged."""
        return ["merged"]

    @label_var(label_id="merge.search.title_format")
    def label_search_title_extracted(self) -> list[str]:
        """Label for search.title_merged."""
        return ["extracted"]

    @label_var(label_id="merge.search.clear_button")
    def label_search_clear_button(self) -> None:
        """Label for search.clear_button."""

    @label_var(label_id="merge.filter_entity_type.title")
    def label_filter_entity_type_title(self) -> None:
        """Label for filter_entity_type.title."""

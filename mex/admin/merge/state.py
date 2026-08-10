import time
from collections.abc import Generator, Iterable
from typing import Literal

import reflex as rx
from reflex.event import EventSpec
from requests import HTTPError

from mex.admin.exceptions import escalate_error
from mex.admin.label_var import label_var
from mex.admin.models import SearchResult
from mex.admin.state import State
from mex.admin.transform import transform_models_to_search_results
from mex.admin.utils import resolve_editor_value
from mex.admin.value_label_select import ValueLabelSelectItem
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.models import MERGED_MODEL_CLASSES
from mex.common.transform import ensure_prefix


class MergeState(State):
    """State management for the merge items page."""

    results_extracted: list[SearchResult] = []
    results_merged: list[SearchResult] = []
    stem_type: str = min(k.stemType for k in MERGED_MODEL_CLASSES)
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
    search_duration_seconds: dict[str, float] = {
        "merged": 0.0,
        "extracted": 0.0,
    }
    selected_items: dict[str, int | None] = {
        "merged": None,
        "extracted": None,
    }

    @rx.var
    def value_label_stem_types(self) -> list[ValueLabelSelectItem]:
        """Get the mergeable stem types with translation."""
        return sorted(
            [
                ValueLabelSelectItem(
                    value=k.stemType,
                    label=self._locale_service.get_ui_label(
                        self.current_locale, k.stemType
                    ),
                )
                for k in MERGED_MODEL_CLASSES
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
    def set_stem_type(self, stem_type: str) -> None:
        """Set the stem type both search panels are filtered by."""
        self.stem_type = stem_type

    @rx.event
    def reset_stem_type(self) -> None:
        """Set the stem type to the first available one in alphabetical order."""
        self.stem_type = self.value_label_stem_types[0].value

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
        entity_type = [ensure_prefix(self.stem_type, "Merged")]
        self.is_loading = True
        yield None
        start_time = time.monotonic()
        try:
            response = connector.fetch_preview_items(
                query_string=self.query_strings["merged"],
                entity_type=entity_type,
                limit=self.limit,
            )
        except HTTPError as exc:
            self.search_duration_seconds["merged"] = time.monotonic() - start_time
            self.is_loading = False
            self.results_merged = []
            self.results_count["merged"] = 0
            self.total_count["merged"] = 0
            yield None
            yield from escalate_error(
                "backend", "error fetching merged items", exc.response.text
            )
        else:
            self.search_duration_seconds["merged"] = time.monotonic() - start_time
            self.is_loading = False
            self.results_merged = transform_models_to_search_results(response.items)
            self.results_count["merged"] = len(self.results_merged)
            self.total_count["merged"] = response.total

    def _refresh_extracted(self) -> Generator[EventSpec | None]:
        """Refresh the search results for extracted items."""
        connector = BackendApiConnector.get()
        entity_type = [ensure_prefix(self.stem_type, "Extracted")]
        self.results_extracted = self.results_extracted
        self.is_loading = True
        yield None
        start_time = time.monotonic()
        try:
            response = connector.fetch_extracted_items(
                query_string=self.query_strings["extracted"],
                entity_type=entity_type,
                limit=self.limit,
            )
        except HTTPError as exc:
            self.search_duration_seconds["extracted"] = time.monotonic() - start_time
            self.is_loading = False
            self.results_extracted = []
            self.results_count["extracted"] = 0
            self.total_count["extracted"] = 0
            yield None
            yield from escalate_error(
                "backend", "error fetching extracted items", exc.response.text
            )
        else:
            self.search_duration_seconds["extracted"] = time.monotonic() - start_time
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

    def _result_summary_args(
        self, category: Literal["merged", "extracted"]
    ) -> list[float]:
        # the range is 1-based and inclusive, but collapses to 0-0 without results
        return [
            1 if self.results_count[category] else 0,
            self.results_count[category],
            self.total_count[category],
            self.search_duration_seconds[category],
        ]

    @label_var(
        label_id="merge.result_summary.format",
        deps=["results_count", "total_count", "search_duration_seconds"],
    )
    def label_result_summary_format_merged(self) -> list[float]:
        """Label for result_summary.format."""
        return self._result_summary_args("merged")

    @label_var(
        label_id="merge.result_summary.format",
        deps=["results_count", "total_count", "search_duration_seconds"],
    )
    def label_result_summary_format_extracted(self) -> list[float]:
        """Label for result_summary.format."""
        return self._result_summary_args("extracted")

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

    @label_var(label_id="merge.title.merge_items")
    def label_title_merge_items(self) -> None:
        """Label for title.merge_items."""

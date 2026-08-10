import math
import time
from collections.abc import Generator, Iterable
from typing import Literal

import reflex as rx
from reflex.event import EventSpec
from requests import HTTPError

from mex.admin.exceptions import escalate_error
from mex.admin.label_var import label_var
from mex.admin.models import SearchResult
from mex.admin.pagination_component import build_page_selection
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
    current_pages: dict[Literal["merged", "extracted"], int] = {
        "merged": 1,
        "extracted": 1,
    }
    selected_items: dict[str, int | None] = {
        "merged": None,
        "extracted": None,
    }

    def _max_page(self, category: Literal["merged", "extracted"]) -> int:
        """Return the maximum page of a category, based on its total and the limit."""
        return math.ceil(self.total_count[category] / self.limit)

    def _skip(self, category: Literal["merged", "extracted"]) -> int:
        """Return the skip/offset of a category, based on its page and the limit."""
        return self.limit * (self.current_pages[category] - 1)

    @rx.var
    def page_selections(self) -> dict[str, list[str]]:
        """Get the selectable pages per category, thinned out when there are many."""
        return {
            category: build_page_selection(
                self._max_page(category), self.current_pages[category]
            )
            for category in self.current_pages
        }

    @rx.var
    def disable_page_selections(self) -> dict[str, bool]:
        """Whether the page selection should be disabled, per category."""
        return {
            category: page >= self._max_page(category)
            for category, page in self.current_pages.items()
        }

    @rx.var
    def disable_previous_pages(self) -> dict[str, bool]:
        """Whether the 'Previous' button should be disabled, per category."""
        return {category: page <= 1 for category, page in self.current_pages.items()}

    @rx.var
    def disable_next_pages(self) -> dict[str, bool]:
        """Whether the 'Next' button should be disabled, per category."""
        return {
            category: page >= self._max_page(category)
            for category, page in self.current_pages.items()
        }

    @rx.var
    def disable_submit_button(self) -> bool:
        """Whether the merge can be submitted, which needs a selection on both sides."""
        return None in self.selected_items.values()

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
        # the previous pages are meaningless for a different entity type
        self.current_pages = dict.fromkeys(self.current_pages, 1)

    @rx.event
    def reset_stem_type(self) -> None:
        """Set the stem type to the first available one in alphabetical order."""
        self.set_stem_type(self.value_label_stem_types[0].value)  # type: ignore[operator]

    @rx.event
    def set_current_page(
        self, category: Literal["merged", "extracted"], page_number: str | int
    ) -> None:
        """Set the current page of a category (coerced to be between 1 and max_page)."""
        page_number = int(page_number) if page_number else 1
        max_page = self._max_page(category)
        self.current_pages[category] = max(min(page_number, max_page), 1)

    @rx.event
    def go_to_first_page(self, category: Literal["merged", "extracted"]) -> None:
        """Navigate to the first page of a category."""
        self.current_pages[category] = 1

    @rx.event
    def go_to_previous_page(self, category: Literal["merged", "extracted"]) -> None:
        """Navigate to the previous page of a category."""
        self.set_current_page(category, self.current_pages[category] - 1)  # type: ignore[operator]

    @rx.event
    def go_to_next_page(self, category: Literal["merged", "extracted"]) -> None:
        """Navigate to the next page of a category."""
        self.set_current_page(category, self.current_pages[category] + 1)  # type: ignore[operator]

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
                skip=self._skip("merged"),
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
            # the current page can fall outside the range when the total shrinks
            self.set_current_page("merged", self.current_pages["merged"])  # type: ignore[operator]

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
                skip=self._skip("extracted"),
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
            # the current page can fall outside the range when the total shrinks
            self.set_current_page("extracted", self.current_pages["extracted"])  # type: ignore[operator]

    @rx.event
    def submit_merge_items(self) -> Generator[EventSpec]:
        """Submit merging the selected extracted item into the selected merged item."""
        merged_index = self.selected_items["merged"]
        extracted_index = self.selected_items["extracted"]
        if merged_index is None or extracted_index is None:
            # the submit button is disabled until both sides have a selection
            return
        keeper_identifier = self.results_merged[merged_index].identifier
        goner_identifier = self.results_extracted[extracted_index].identifier
        connector = BackendApiConnector.get()
        try:
            # TODO(ND): use the dedicated connector method once it is available
            connector.request(
                method="POST",
                endpoint="merge",
                payload={
                    "gonerIdentifier": str(goner_identifier),
                    "keeperIdentifier": str(keeper_identifier),
                },
            )
        except HTTPError as exc:
            yield from escalate_error(
                "backend", "error merging items", exc.response.text
            )
        else:
            yield rx.toast.success(
                title=self.label_toast_success_title,
                description=self.label_toast_success_message_format.format(
                    goner_identifier, keeper_identifier
                ),
                class_name="editor-toast",
                close_button=True,
                dismissible=True,
                duration=5000,
            )

    def _result_summary_args(
        self, category: Literal["merged", "extracted"]
    ) -> list[float]:
        # the range is 1-based and inclusive, but collapses to 0-0 without results
        first_item = self._skip(category) + 1 if self.results_count[category] else 0
        return [
            first_item,
            self._skip(category) + self.results_count[category],
            self.total_count[category],
            self.search_duration_seconds[category],
        ]

    @label_var(
        label_id="merge.result_summary.format",
        deps=[
            "results_count",
            "total_count",
            "search_duration_seconds",
            "current_pages",
            "limit",
        ],
    )
    def label_result_summary_format_merged(self) -> list[float]:
        """Label for result_summary.format."""
        return self._result_summary_args("merged")

    @label_var(
        label_id="merge.result_summary.format",
        deps=[
            "results_count",
            "total_count",
            "search_duration_seconds",
            "current_pages",
            "limit",
        ],
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

    @label_var(label_id="merge.toast_success.title")
    def label_toast_success_title(self) -> None:
        """Label for toast_success.title."""

    @label_var(label_id="merge.toast_success.message_format")
    def label_toast_success_message_format(self) -> None:
        """Label for toast_success.message_format."""

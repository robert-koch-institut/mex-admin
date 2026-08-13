import math
import time
from collections.abc import Generator, Iterable
from typing import Literal

import reflex as rx
from pydantic import BaseModel
from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error, response_payload
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

# The item that is superseded (left) and the one that survives the merge (right).
# This has to stay a plain assignment: a PEP 695 `type` alias would be a
# `TypeAliasType`, which reflex's runtime field validation cannot resolve.
MergeSide = Literal["goner", "keeper"]

# marks the identifier placeholders while splitting the dialog description
PLACEHOLDER_MARKER = "\x00"


class DescriptionSegment(BaseModel):
    """A chunk of the submit dialog description, optionally linking to an item."""

    text: str
    identifier: str = ""


class MergeState(State):
    """State management for the merge items page."""

    results_goner: list[SearchResult] = []
    results_keeper: list[SearchResult] = []
    stem_type: str = min(k.stemType for k in MERGED_MODEL_CLASSES)
    is_loading: bool = True
    limit: int = 50
    query_strings: dict[MergeSide, str] = {
        "goner": "",
        "keeper": "",
    }
    results_count: dict[str, int] = {
        "goner": 0,
        "keeper": 0,
    }
    total_count: dict[str, int] = {
        "goner": 0,
        "keeper": 0,
    }
    search_duration_seconds: dict[str, float] = {
        "goner": 0.0,
        "keeper": 0.0,
    }
    current_pages: dict[MergeSide, int] = {
        "goner": 1,
        "keeper": 1,
    }
    selected_items: dict[str, int | None] = {
        "goner": None,
        "keeper": None,
    }

    def _results(self, side: MergeSide) -> list[SearchResult]:
        """Return the search results of one side."""
        return self.results_goner if side == "goner" else self.results_keeper

    def _set_results(self, side: MergeSide, results: list[SearchResult]) -> None:
        """Set the search results of one side."""
        if side == "goner":
            self.results_goner = results
        else:
            self.results_keeper = results

    def _selected_identifier(self, side: MergeSide) -> str:
        """Return the identifier selected on one side, or an empty string if none."""
        index = self.selected_items[side]
        results = self._results(side)
        if index is None or index >= len(results):
            return ""
        return results[index].identifier

    def _max_page(self, side: MergeSide) -> int:
        """Return the maximum page of one side, based on its total and the limit."""
        return math.ceil(self.total_count[side] / self.limit)

    def _skip(self, side: MergeSide) -> int:
        """Return the skip/offset of one side, based on its page and the limit."""
        return self.limit * (self.current_pages[side] - 1)

    @rx.var
    def page_selections(self) -> dict[str, list[str]]:
        """Get the selectable pages per side, thinned out when there are many."""
        return {
            side: build_page_selection(self._max_page(side), self.current_pages[side])
            for side in self.current_pages
        }

    @rx.var
    def disable_page_selections(self) -> dict[str, bool]:
        """Whether the page selection should be disabled, per side."""
        return {
            side: page >= self._max_page(side)
            for side, page in self.current_pages.items()
        }

    @rx.var
    def disable_previous_pages(self) -> dict[str, bool]:
        """Whether the 'Previous' button should be disabled, per side."""
        return {side: page <= 1 for side, page in self.current_pages.items()}

    @rx.var
    def disable_next_pages(self) -> dict[str, bool]:
        """Whether the 'Next' button should be disabled, per side."""
        return {
            side: page >= self._max_page(side)
            for side, page in self.current_pages.items()
        }

    @rx.var
    def disable_submit_button(self) -> bool:
        """Whether the merge can be submitted, which needs a selection on both sides."""
        return None in self.selected_items.values()

    @rx.var(
        deps=["current_locale", "selected_items", "results_goner", "results_keeper"],
        auto_deps=False,
    )
    def submit_dialog_description_segments(self) -> list[DescriptionSegment]:
        """Split the submit dialog description around its identifier placeholders.

        The sentence stays one translatable unit, but the two identifiers are
        handed out separately so they can be rendered as links.
        """
        label = self._locale_service.get_ui_label(
            self.current_locale, "merge.submit_dialog.description_format"
        )
        # marking rather than splitting on "{0}"/"{1}" keeps this working for a
        # translation that puts the two placeholders in the other order
        sides: list[MergeSide] = ["goner", "keeper"]
        marked = label.format(
            *(f"{PLACEHOLDER_MARKER}{side}{PLACEHOLDER_MARKER}" for side in sides)
        )
        segments = []
        for index, part in enumerate(marked.split(PLACEHOLDER_MARKER)):
            if index % 2:
                # odd chunks are the markers, so `part` is the side's name
                identifier = self._selected_identifier(part)  # type: ignore[arg-type]
                segments.append(
                    DescriptionSegment(text=identifier, identifier=identifier)
                )
            elif part:
                segments.append(DescriptionSegment(text=part))
        return segments

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
    def select_item(self, side: MergeSide, index: int) -> None:
        """Select or deselect an item on one side based on the index."""
        if self.selected_items[side] == index:
            self.selected_items[side] = None
            return
        self.selected_items[side] = index

    @rx.event
    def handle_submit(self, side: MergeSide, form_data: str) -> None:
        """Handle the search form submit of one side."""
        self.query_strings[side] = form_data

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
    def set_current_page(self, side: MergeSide, page_number: str | int) -> None:
        """Set the current page of one side (coerced to be between 1 and max_page)."""
        page_number = int(page_number) if page_number else 1
        max_page = self._max_page(side)
        self.current_pages[side] = max(min(page_number, max_page), 1)

    @rx.event
    def go_to_first_page(self, side: MergeSide) -> None:
        """Navigate to the first page of one side."""
        self.current_pages[side] = 1

    @rx.event
    def go_to_previous_page(self, side: MergeSide) -> None:
        """Navigate to the previous page of one side."""
        self.set_current_page(side, self.current_pages[side] - 1)  # type: ignore[operator]

    @rx.event
    def go_to_next_page(self, side: MergeSide) -> None:
        """Navigate to the next page of one side."""
        self.set_current_page(side, self.current_pages[side] + 1)  # type: ignore[operator]

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for result_list in (self.results_goner, self.results_keeper):
            for result in result_list:
                for preview in result.preview:
                    if preview.identifier and not preview.text:
                        async with self:
                            await resolve_editor_value(preview)

    @rx.event
    def refresh(
        self,
        sides: Iterable[MergeSide] = ("goner", "keeper"),
    ) -> Generator[EventSpec | None]:
        """Refresh the search results for the specified sides."""
        for side in ("goner", "keeper"):
            if side in sides:
                self.selected_items[side] = None
                yield from self._refresh(side)

    def _refresh(self, side: MergeSide) -> Generator[EventSpec | None]:
        """Refresh the search results for one side."""
        connector = BackendApiConnector.get()
        entity_type = [ensure_prefix(self.stem_type, "Merged")]
        self.is_loading = True
        yield None
        start_time = time.monotonic()
        try:
            response = connector.fetch_preview_items(
                query_string=self.query_strings[side],
                entity_type=entity_type,
                skip=self._skip(side),
                limit=self.limit,
            )
        except RequestException as exc:
            self.search_duration_seconds[side] = time.monotonic() - start_time
            self.is_loading = False
            self._set_results(side, [])
            self.results_count[side] = 0
            self.total_count[side] = 0
            yield None
            yield from escalate_error(
                "backend", "error fetching merged items", response_payload(exc)
            )
        else:
            self.search_duration_seconds[side] = time.monotonic() - start_time
            self.is_loading = False
            self._set_results(side, transform_models_to_search_results(response.items))
            self.results_count[side] = len(self._results(side))
            self.total_count[side] = response.total
            # the current page can fall outside the range when the total shrinks
            self.set_current_page(side, self.current_pages[side])  # type: ignore[operator]

    @rx.event
    def submit_merge_items(self) -> Generator[EventSpec | None]:
        """Submit merging the selected goner into the selected keeper."""
        goner_identifier = self._selected_identifier("goner")
        keeper_identifier = self._selected_identifier("keeper")
        if not (goner_identifier and keeper_identifier):
            # the submit button is disabled until both sides have a selection
            return
        connector = BackendApiConnector.get()
        try:
            # TODO(ND): use the dedicated connector method once it is available
            # TODO(ND): use user auth for backend requests (stop-gap MX-1616)
            connector.request(
                method="POST",
                endpoint="merge",
                payload={
                    "gonerIdentifier": str(goner_identifier),
                    "keeperIdentifier": str(keeper_identifier),
                },
            )
        except RequestException as exc:
            # keep the selections, so a transient error can be retried as-is
            yield from escalate_error(
                "backend", "error merging items", response_payload(exc)
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
            # the goner is a tombstone now, so both result lists are stale
            yield from self.refresh()  # type: ignore[operator]
            yield MergeState.resolve_identifiers()  # type: ignore[misc]

    def _result_summary_args(self, side: MergeSide) -> list[float]:
        # the range is 1-based and inclusive, but collapses to 0-0 without results
        first_item = self._skip(side) + 1 if self.results_count[side] else 0
        return [
            first_item,
            self._skip(side) + self.results_count[side],
            self.total_count[side],
            self.search_duration_seconds[side],
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
    def label_result_summary_format_goner(self) -> list[float]:
        """Label for result_summary.format."""
        return self._result_summary_args("goner")

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
    def label_result_summary_format_keeper(self) -> list[float]:
        """Label for result_summary.format."""
        return self._result_summary_args("keeper")

    @label_var(label_id="merge.submit_button")
    def label_submit_button(self) -> None:
        """Label for submit_button."""

    @label_var(label_id="merge.search_input.placeholder")
    def label_search_input_placeholder(self) -> None:
        """Label for search_input.placeholder."""

    @label_var(label_id="merge.search.title_goner")
    def label_search_title_goner(self) -> None:
        """Label for search.title_goner."""

    @label_var(label_id="merge.search.title_keeper")
    def label_search_title_keeper(self) -> None:
        """Label for search.title_keeper."""

    @label_var(label_id="merge.title.merge_items")
    def label_title_merge_items(self) -> None:
        """Label for title.merge_items."""

    @label_var(label_id="merge.submit_dialog.title")
    def label_submit_dialog_title(self) -> None:
        """Label for submit_dialog.title."""

    @label_var(label_id="merge.submit_dialog.cancel_button")
    def label_submit_dialog_cancel_button(self) -> None:
        """Label for submit_dialog.cancel_button."""

    @label_var(label_id="merge.submit_dialog.confirm_button")
    def label_submit_dialog_confirm_button(self) -> None:
        """Label for submit_dialog.confirm_button."""

    @label_var(label_id="merge.toast_success.title")
    def label_toast_success_title(self) -> None:
        """Label for toast_success.title."""

    @label_var(label_id="merge.toast_success.message_format")
    def label_toast_success_message_format(self) -> None:
        """Label for toast_success.message_format."""

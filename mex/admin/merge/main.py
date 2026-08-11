from typing import Literal

import reflex as rx

from mex.admin.layout import page
from mex.admin.merge.state import MergeState
from mex.admin.models import SearchResult
from mex.admin.pagination_component import (
    PaginationButtonOptions,
    PaginationOptions,
    PaginationPageOptions,
)
from mex.admin.search_results_component import (
    SearchResultsComponentOptions,
    SearchResultsListItemOptions,
    SearchResultsListOptions,
    search_results_component,
)
from mex.admin.value_label_select import value_label_select


def merge_title() -> rx.Component:
    """Return the title with a select for the entity type to merge."""
    return rx.hstack(
        rx.heading(
            MergeState.label_title_merge_items,
            style=rx.Style(userSelect="none"),
        ),
        value_label_select(
            MergeState.value_label_stem_types,
            value=MergeState.stem_type,
            on_change=[
                MergeState.set_stem_type,
                MergeState.refresh(["merged", "extracted"]),  # type: ignore[operator]
                MergeState.resolve_identifiers,
            ],
            disabled=MergeState.is_loading,
            custom_attrs={"data-testid": "entity-type-select"},
        ),
        align="center",
        custom_attrs={"data-testid": "merge-heading"},
    )


def build_pagination_options(
    category: Literal["merged", "extracted"],
) -> PaginationOptions:
    """Build the pagination options for one side of the merge page."""
    refresh_category = [
        MergeState.refresh([category]),  # type: ignore[operator]
        MergeState.resolve_identifiers,
    ]
    return PaginationOptions(
        PaginationButtonOptions(
            MergeState.disable_previous_pages[category],
            [MergeState.go_to_previous_page(category), *refresh_category],  # type: ignore[operator]
        ),
        PaginationButtonOptions(
            MergeState.disable_next_pages[category],
            [MergeState.go_to_next_page(category), *refresh_category],  # type: ignore[operator]
        ),
        PaginationPageOptions(
            MergeState.current_pages[category],
            MergeState.page_selections[category],
            MergeState.disable_page_selections[category],
            [MergeState.set_current_page(category), *refresh_category],  # type: ignore[operator]
        ),
    )


def search_input(category: Literal["merged", "extracted"]) -> rx.Component:
    """Render a search input with an inlined button for the results to refresh."""
    return rx.form.root(
        rx.hstack(
            rx.input(
                autofocus=True,
                value=MergeState.query_strings[category],
                default_value=MergeState.query_strings[category],
                max_length=100,
                name=f"query_string_{category}",
                on_change=MergeState.handle_submit(category),  # type: ignore[operator]
                placeholder=MergeState.label_search_input_placeholder,
                width="100%",
                tab_index=1,
                type="text",
                custom_attrs={"data-testid": f"search-input-{category}"},
            ),
            rx.spacer(),
            rx.button(
                rx.icon("search"),
                type="submit",
                variant="surface",
                disabled=MergeState.is_loading,
                on_click=[
                    MergeState.go_to_first_page(category),  # type: ignore[operator]
                    MergeState.refresh([category]),  # type: ignore[operator]
                    MergeState.resolve_identifiers,
                ],
                custom_attrs={"data-testid": f"search-button-{category}"},
            ),
            align="center",
            width="100%",
        ),
        custom_attrs={"data-testid": f"search-{category}"},
    )


def submit_button() -> rx.Component:
    """Render a submit button to commit the merging."""
    return rx.button(
        MergeState.label_submit_button,
        color_scheme="jade",
        size="3",
        disabled=MergeState.disable_submit_button,
        on_click=MergeState.submit_merge_items,
        style=rx.Style(margin="var(--line-height-1) 0"),
        custom_attrs={"data-testid": "submit-button"},
    )


def search_panel(category: Literal["merged", "extracted"]) -> rx.Component:
    """Return the search interface."""

    def render_checkbox(_: SearchResult, index: int) -> rx.Component:
        return rx.checkbox(
            checked=MergeState.selected_items[category] == index,
            on_change=MergeState.select_item(category, index),  # type:ignore[operator]
        )

    list_options = SearchResultsListOptions(
        item_options=SearchResultsListItemOptions(render_prepend_fn=render_checkbox)
    )
    pagination_options = build_pagination_options(category)

    return rx.vstack(
        rx.heading(
            MergeState.label_search_title_merged
            if category == "merged"
            else MergeState.label_search_title_extracted,
            style=rx.Style(
                userSelect="none",
                fontWeight="normal",
                width="100%",
            ),
            as_="h2",
            custom_attrs={"data-testid": f"create-heading-{category}"},
        ),
        search_input(category),
        rx.box(
            rx.cond(
                category == "merged",
                search_results_component(
                    MergeState.results_merged,
                    SearchResultsComponentOptions(
                        summary_text=MergeState.label_result_summary_format_merged,
                        list_options=list_options,
                        pagination_options=pagination_options,
                    ),
                ),
                search_results_component(
                    MergeState.results_extracted,
                    SearchResultsComponentOptions(
                        summary_text=MergeState.label_result_summary_format_extracted,
                        list_options=list_options,
                        pagination_options=pagination_options,
                    ),
                ),
            ),
            custom_attrs={"data-testid": f"{category}-search-results-container"},
        ),
        align="stretch",
        # `minWidth` lets the panel shrink below the width of its widest result,
        # so the two panels always share the row instead of overflowing it
        style=rx.Style(flex="1", minWidth="0"),
    )


def index() -> rx.Component:
    """Return the index for the merge and extracted search component."""
    return page(
        rx.vstack(
            rx.hstack(
                merge_title(),
                rx.spacer(),
                submit_button(),
                align="center",
                width="100%",
            ),
            rx.hstack(
                search_panel(category="merged"),
                search_panel(category="extracted"),
                align="start",
                spacing="8",
                width="100%",
            ),
            align="stretch",
            spacing="4",
            style=rx.Style(flex="1", minWidth="0"),
        ),
    )

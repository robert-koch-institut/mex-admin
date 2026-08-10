from typing import Literal

import reflex as rx

from mex.admin.layout import page
from mex.admin.merge.state import MergeState
from mex.admin.models import SearchResult
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


def search_input(category: Literal["merged", "extracted"]) -> rx.Component:
    """Render a search input and buttons for the results to refresh."""
    return rx.vstack(
        rx.form.root(
            rx.card(
                rx.input(
                    autofocus=True,
                    value=MergeState.query_strings[category],
                    default_value=MergeState.query_strings[category],
                    max_length=100,
                    name=f"query_string_{category}",
                    on_change=MergeState.handle_submit(category),  # type: ignore[operator]
                    placeholder=MergeState.label_search_input_placeholder,
                    style=rx.Style(
                        {
                            "--text-field-selection-color": "",
                            "--text-field-focus-color": "transparent",
                            "--text-field-border-width": "calc(1px * var(--scaling))",
                            "boxShadow": (
                                "inset 0 0 0 var(--text-field-border-width) transparent"
                            ),
                        }
                    ),
                    tab_index=1,
                    type="text",
                    custom_attrs={"data-testid": f"search-input-{category}"},
                ),
            ),
            rx.spacer(height="var(--space-2)"),
            rx.hstack(
                rx.button(
                    rx.icon("Search"),
                    type="submit",
                    variant="surface",
                    disabled=MergeState.is_loading,
                    on_click=[
                        MergeState.refresh([category]),  # type: ignore[operator]
                        MergeState.resolve_identifiers,
                    ],
                    custom_attrs={"data-testid": f"search-button-{category}"},
                ),
                justify="center",
                align="center",
                spacing="2",
                margin="var(--space-4)",
            ),
        ),
        style=rx.Style(
            width="100%",
            marginBottom="var(--space-4)",
            align="center",
        ),
    )


def submit_button() -> rx.Component:
    """Render a submit button to commit the merging."""
    return rx.button(
        MergeState.label_submit_button,
        color_scheme="jade",
        size="3",
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
                    ),
                ),
                search_results_component(
                    MergeState.results_extracted,
                    SearchResultsComponentOptions(
                        summary_text=MergeState.label_result_summary_format_extracted,
                        list_options=list_options,
                    ),
                ),
            ),
            custom_attrs={"data-testid": f"{category}-search-results-container"},
        ),
        align="stretch",
        style=rx.Style(width="50%", margin="var(--space-4)"),
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
                style=rx.Style(width="100%"),
            ),
            rx.hstack(
                search_panel(category="merged"),
                search_panel(category="extracted"),
                style=rx.Style(
                    width="100%",
                    align="center",
                    justify="center",
                ),
            ),
            style=rx.Style(
                width="100%",
                align="center",
                justify="center",
                flexGrow="1",
            ),
        ),
    )

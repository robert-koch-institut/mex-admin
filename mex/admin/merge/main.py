import reflex as rx

from mex.admin.layout import page
from mex.admin.merge.state import DescriptionSegment, MergeSide, MergeState
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
from mex.admin.state import State
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
                MergeState.refresh(["goner", "keeper"]),  # type: ignore[operator]
                MergeState.resolve_identifiers,
            ],
            disabled=MergeState.is_loading,
            custom_attrs={"data-testid": "entity-type-select"},
        ),
        align="center",
        custom_attrs={"data-testid": "merge-heading"},
    )


def build_pagination_options(side: MergeSide) -> PaginationOptions:
    """Build the pagination options for one side of the merge page."""
    refresh_side = [
        MergeState.refresh([side]),  # type: ignore[operator]
        MergeState.resolve_identifiers,
    ]
    return PaginationOptions(
        PaginationButtonOptions(
            MergeState.disable_previous_pages[side],
            [MergeState.go_to_previous_page(side), *refresh_side],  # type: ignore[operator]
        ),
        PaginationButtonOptions(
            MergeState.disable_next_pages[side],
            [MergeState.go_to_next_page(side), *refresh_side],  # type: ignore[operator]
        ),
        PaginationPageOptions(
            MergeState.current_pages[side],
            MergeState.page_selections[side],
            MergeState.disable_page_selections[side],
            [MergeState.set_current_page(side), *refresh_side],  # type: ignore[operator]
        ),
    )


def search_input(side: MergeSide) -> rx.Component:
    """Render a search input with an inlined button for the results to refresh."""
    return rx.card(
        rx.form.root(
            rx.hstack(
                rx.input(
                    autofocus=True,
                    value=MergeState.query_strings[side],
                    default_value=MergeState.query_strings[side],
                    max_length=100,
                    name=f"query_string_{side}",
                    on_change=MergeState.handle_submit(side),  # type: ignore[operator]
                    placeholder=MergeState.label_search_input_placeholder,
                    width="100%",
                    tab_index=1,
                    type="text",
                    custom_attrs={"data-testid": f"search-input-{side}"},
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("search"),
                    type="submit",
                    variant="surface",
                    disabled=MergeState.is_loading,
                    on_click=[
                        MergeState.go_to_first_page(side),  # type: ignore[operator]
                        MergeState.refresh([side]),  # type: ignore[operator]
                        MergeState.resolve_identifiers,
                    ],
                    custom_attrs={"data-testid": f"search-button-{side}"},
                ),
                align="center",
                width="100%",
            ),
        ),
        style=rx.Style(
            marginBottom="var(--space-4)",
            width="100%",
        ),
        variant="ghost",
        custom_attrs={"data-testid": f"search-{side}"},
    )


def description_segment(segment: DescriptionSegment) -> rx.Component:
    """Render a dialog description chunk, linking identifiers to their edit page."""
    return rx.cond(
        segment.identifier,
        rx.link(
            segment.text,
            href="/item/" + segment.identifier,
            high_contrast=True,
            is_external=True,
            role="link",
            title=segment.text,
        ),
        rx.text.span(segment.text),
    )


def submit_button() -> rx.Component:
    """Render a submit button that asks for confirmation before merging."""
    return rx.cond(
        State.has_write_access,
        rx.alert_dialog.root(
            rx.alert_dialog.trigger(
                rx.button(
                    MergeState.label_submit_button,
                    color_scheme="jade",
                    size="3",
                    disabled=MergeState.disable_submit_button,
                    style=rx.Style(margin="var(--line-height-1) 0"),
                    custom_attrs={"data-testid": "submit-button"},
                ),
            ),
            rx.alert_dialog.content(
                rx.alert_dialog.title(MergeState.label_submit_dialog_title),
                rx.alert_dialog.description(
                    rx.foreach(
                        MergeState.submit_dialog_description_segments,
                        description_segment,
                    ),
                    size="2",
                    custom_attrs={"data-testid": "submit-merge-description"},
                ),
                rx.flex(
                    rx.alert_dialog.cancel(
                        # the inert flex is what receives radix's close behavior; a
                        # bare button child would render without it. the testid has
                        # to sit on the button, `cancel` drops its own attrs
                        rx.flex(
                            rx.button(
                                MergeState.label_submit_dialog_cancel_button,
                                variant="soft",
                                color_scheme="gray",
                                custom_attrs={
                                    "data-testid": "submit-merge-cancel-button"
                                },
                            ),
                        ),
                    ),
                    rx.alert_dialog.action(
                        rx.button(
                            MergeState.label_submit_dialog_confirm_button,
                            color_scheme="tomato",
                            variant="solid",
                            on_click=MergeState.submit_merge_items,
                            custom_attrs={"data-testid": "submit-merge-confirm-button"},
                        ),
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                ),
                style=rx.Style(max_width=450),
            ),
        ),
    )


def search_panel(side: MergeSide) -> rx.Component:
    """Return the search interface for one side of the merge page."""

    def render_checkbox(_: SearchResult, index: int) -> rx.Component:
        return rx.cond(
            State.has_write_access,
            rx.checkbox(
                checked=MergeState.selected_items[side] == index,
                on_change=MergeState.select_item(side, index),  # type:ignore[operator]
            ),
        )

    if side == "goner":
        heading = MergeState.label_search_title_goner
        results = MergeState.results_goner
        summary_text = MergeState.label_result_summary_format_goner
    else:
        heading = MergeState.label_search_title_keeper
        results = MergeState.results_keeper
        summary_text = MergeState.label_result_summary_format_keeper

    return rx.vstack(
        rx.heading(
            heading,
            style=rx.Style(
                userSelect="none",
                fontWeight="normal",
                width="100%",
            ),
            as_="h2",
            custom_attrs={"data-testid": f"search-heading-{side}"},
        ),
        search_input(side),
        rx.box(
            search_results_component(
                results,
                SearchResultsComponentOptions(
                    summary_text=summary_text,
                    list_options=SearchResultsListOptions(
                        item_options=SearchResultsListItemOptions(
                            render_prepend_fn=render_checkbox
                        )
                    ),
                    pagination_options=build_pagination_options(side),
                ),
            ),
            custom_attrs={"data-testid": f"{side}-search-results-container"},
        ),
        align="stretch",
        # `minWidth` lets the panel shrink below the width of its widest result,
        # so the two panels always share the row instead of overflowing it
        style=rx.Style(flex="1", minWidth="0"),
    )


def index() -> rx.Component:
    """Return the index for the merge component."""
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
                search_panel(side="goner"),
                search_panel(side="keeper"),
                align="start",
                spacing="4",
                width="100%",
            ),
            align="stretch",
            spacing="4",
            style=rx.Style(flex="1", minWidth="0"),
        ),
    )

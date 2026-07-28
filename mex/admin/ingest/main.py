from typing import Any

import reflex as rx

from mex.admin.component_option_helper import (
    build_pagination_for_state_options,
)
from mex.admin.ingest.models import IngestResult
from mex.admin.ingest.state import IngestState
from mex.admin.layout import page
from mex.admin.search_results_component import (
    SearchResultsComponentOptions,
    SearchResultsListItemOptions,
    SearchResultsListOptions,
    search_results_component,
)


def ingest_button(result: IngestResult, index: int) -> rx.Component:
    """Render a button to ingest the ingest result to the MEx backend."""
    return rx.cond(
        result.show_ingest_button,
        rx.button(
            IngestState.label_button_ingest,
            align="end",
            color_scheme="jade",
            variant="surface",
            on_click=IngestState.ingest_result(index),  # type: ignore[operator]
            width="calc(8em * var(--scaling))",
            custom_attrs={"data-testid": f"ingest-button-{index}"},
        ),
        rx.button(
            IngestState.label_button_ingested,
            align="end",
            color_scheme="gray",
            variant="surface",
            disabled=True,
            width="calc(8em * var(--scaling))",
            custom_attrs={"data-testid": f"ingest-button-{index}"},
        ),
    )


def search_input() -> rx.Component:
    """Render a search input element that will trigger the results to refresh."""
    return rx.center(
        rx.form(
            rx.hstack(
                rx.input(
                    autofocus=True,
                    max_length=100,
                    name="query_string",
                    placeholder=IngestState.label_search_placeholder,
                    style=rx.Style(
                        {
                            "--text-field-selection-color": "",
                            "--text-field-focus-color": "transparent",
                            "--text-field-border-width": "1px",
                            "backgroundClip": "content-box",
                            "backgroundColor": "transparent",
                            "boxShadow": (
                                "inset 0 0 0 var(--text-field-border-width) transparent"
                            ),
                            "color": "",
                        }
                    ),
                    disabled=IngestState.is_loading,
                    type="text",
                    custom_attrs={"data-testid": "search-input"},
                ),
                rx.button(
                    rx.icon("search"),
                    type="submit",
                    variant="surface",
                    disabled=IngestState.is_loading,
                    custom_attrs={"data-testid": "search-button"},
                ),
                width="100%",
            ),
            on_submit=[
                IngestState.handle_submit,
                IngestState.go_to_first_page,
                IngestState.refresh,
                IngestState.resolve_identifiers,
                IngestState.flag_ingested_items,
            ],
            style=rx.Style(margin="1em 0"),
            justify="center",
            align="center",
        )
    )


def search_results() -> rx.Component:
    """Render the search results with a heading, result list, and pagination."""
    return rx.cond(
        IngestState.is_loading,
        rx.center(
            rx.spinner(size="3"),
            style=rx.Style(
                marginTop="var(--space-6)",
                width="100%",
            ),
        ),
        search_results_component(
            IngestState.results_transformed,  # type: ignore[arg-type]
            SearchResultsComponentOptions(
                summary_text=IngestState.label_search_result_summary_format,
                pagination_options=build_pagination_for_state_options(
                    IngestState, IngestState.flag_ingested_items
                ),
                list_options=SearchResultsListOptions(
                    item_options=SearchResultsListItemOptions(
                        enable_show_all_properties=True,
                        on_toggle_show_all_properties=IngestState.toggle_show_all_properties,  # type: ignore[arg-type]
                        render_append_fn=ingest_button,  # type: ignore[arg-type]
                    )
                ),
            ),
        ),
    )


def search_infobox() -> rx.Component | rx.Var[Any]:
    """Render information about the specific search provider query format."""
    return rx.match(
        IngestState.current_aux_provider.key,
        (
            "ldap",
            rx.callout(
                IngestState.label_search_info_ldap,
                custom_attrs={"data-testid": "ingest-infobox-callout"},
            ),
        ),
        (
            "wikidata",
            rx.callout(
                IngestState.label_search_info_wikidata,
                custom_attrs={"data-testid": "ingest-infobox-callout"},
            ),
        ),
    )


def tab_list() -> rx.Component:
    """Render the list of aux providers as a tab navigation."""
    return rx.center(
        rx.tabs.list(
            rx.spacer(),
            rx.foreach(
                IngestState.aux_providers,
                lambda provider: rx.tabs.trigger(
                    provider.dynamic_name,
                    value=provider.key,
                    disabled=IngestState.is_loading,
                ),
            ),
            rx.spacer(),
            style=rx.Style(width="calc(45em * var(--scaling))"),
        )
    )


def tab_content() -> rx.Component:
    """Render the tab content with search components for each aux provider."""
    return rx.foreach(
        IngestState.aux_providers,
        lambda provider: rx.tabs.content(
            rx.vstack(
                search_input(),
                search_infobox(),
                search_results(),
                justify="center",
                align="center",
                spacing="5",
            ),
            value=provider.key,
        ),
    )


def index() -> rx.Component:
    """Return the index for the search component."""
    return page(
        rx.tabs.root(
            tab_list(),
            rx.spacer(),
            tab_content(),
            default_value=IngestState.current_aux_provider.key,
            on_change=[
                IngestState.set_current_aux_provider,
                IngestState.reset_query_string,
                IngestState.go_to_first_page,
                IngestState.refresh,
                IngestState.resolve_identifiers,
                IngestState.flag_ingested_items,
            ],
            custom_attrs={"data-testid": "aux-tab-section"},
            style=rx.Style(
                width="100%",
                padding="0 calc(var(--space-8) * var(--scaling))",
            ),
        )
    )

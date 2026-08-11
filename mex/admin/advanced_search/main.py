import reflex as rx

from mex.admin.advanced_search.state import AdvancedSearchState, RefFilter
from mex.admin.component_option_helper import build_pagination_options
from mex.admin.layout import page
from mex.admin.models import ValueLabelCheckboxItem
from mex.admin.search_reference_dialog import search_reference_dialog
from mex.admin.search_results_component import (
    SearchResultsComponentOptions,
    SearchResultsListItemOptions,
    SearchResultsListOptions,
    search_results_component,
)
from mex.admin.value_label_select import value_label_select


def filter_query() -> rx.Component:
    """Render filter query page."""
    return rx.card(
        rx.form(
            rx.hstack(
                rx.box(
                    rx.input(
                        default_value=AdvancedSearchState.query,
                        max_length=100,
                        name="query",
                        placeholder=AdvancedSearchState.label_search_input_placeholder,
                        type="text",
                        custom_attrs={"data-testid": "filter-query"},
                    ),
                    style=rx.Style(flex=1),
                ),
                rx.button(
                    rx.icon("search"),
                    type="submit",
                    variant="surface",
                    custom_attrs={"data-testid": "filter-query-submit"},
                ),
                align="stretch",
            ),
            on_submit=[
                AdvancedSearchState.on_query_form_submit,
                AdvancedSearchState.search,
                AdvancedSearchState.resolve_identifiers,
            ],
        )
    )


def entity_type_choice(choice: ValueLabelCheckboxItem) -> rx.Component:
    """Render a single checkbox for filtering by entity type."""
    return rx.checkbox(
        choice.label,
        checked=choice.checked,
        on_change=[
            AdvancedSearchState.toggle_entity_type(choice.value),  # type: ignore[operator]
            AdvancedSearchState.search,
            AdvancedSearchState.resolve_identifiers,
        ],
        custom_attrs={"data-testid": f"filter-entity-type-{choice.value}"},
    )


def filter_entity_type() -> rx.Component:
    """Render filter entity type page."""
    return rx.card(
        rx.text(
            AdvancedSearchState.label_entitytype_filter_title,
            style=rx.Style(
                marginBottom="var(--space-4)",
                userSelect="none",
            ),
        ),
        rx.vstack(
            rx.foreach(
                AdvancedSearchState.label_entity_types,
                entity_type_choice,
            ),
            custom_attrs={"data-testid": "filter-entity-types"},
            align="stretch",
        ),
        align="stretch",
    )


def ref_filter_value(
    ref: RefFilter, index: int, val: str, val_index: int
) -> rx.Component:
    """Render specified value of ref filter."""
    return rx.hstack(
        rx.input(
            value=val,
            placeholder=f"{AdvancedSearchState.label_reference_filter_value_placeholder} '{ref.field_label}'",  # noqa: E501
            on_change=[
                lambda value: AdvancedSearchState.set_ref_filter_value(
                    index, val_index, value
                ),  # type: ignore[operator]
                AdvancedSearchState.search,
                AdvancedSearchState.resolve_identifiers,
            ],
            custom_attrs={"data-testid": f"filter-ref-{index}-value-{val_index}-value"},
            style=rx.Style(flex="1"),
        ),
        search_reference_dialog(
            field_label=ref.field_label,
            reference_types=ref.field_value_types,
            on_identifier_selected=[
                lambda value: AdvancedSearchState.set_ref_filter_value(
                    index, val_index, value
                ),  # type: ignore[operator]
                AdvancedSearchState.search,
                AdvancedSearchState.resolve_identifiers,
            ],
        ),
        rx.icon_button(
            rx.icon(
                "minus",
                height="1rem",
                width="1rem",
            ),
            variant="soft",
            color_scheme="tomato",
            size="1",
            on_click=[
                AdvancedSearchState.remove_ref_filter_value(index, val_index),  # type: ignore[operator]
                AdvancedSearchState.search,
                AdvancedSearchState.resolve_identifiers,
            ],
            custom_attrs={
                "data-testid": f"filter-ref-{index}-value-{val_index}-remove"
            },
        ),
        align="center",
        style=rx.Style(padding_left="1em"),
    )


def ref_filter(ref: RefFilter, index: int) -> rx.Component:
    """Render specified ref filter."""
    return rx.vstack(
        rx.vstack(
            value_label_select(
                items=AdvancedSearchState.all_fields_for_entity_types,
                value=ref.field_descriptor_json,
                placeholder=AdvancedSearchState.label_reference_field_filter_placeholder,
                on_change=lambda value: AdvancedSearchState.set_ref_filter_field(
                    index, value
                ),  # type: ignore[operator]
                custom_attrs={"data-testid": f"ref-filter-{index}-field"},
                item_testid_prefix="ref-filter-",
            ),
            rx.button(
                f"{AdvancedSearchState.label_reference_filter_remove_value} "
                f"{ref.field_label}",
                color_scheme="gray",
                variant="soft",
                size="1",
                class_name="truncate",
                style=rx.Style(align_self="end", max_width="60%", display="block"),
                on_click=[
                    AdvancedSearchState.remove_ref_filter(index),  # type: ignore[operator]
                    AdvancedSearchState.search,
                    AdvancedSearchState.resolve_identifiers,
                ],
                custom_attrs={"data-testid": f"ref-filter-{index}-remove"},
            ),
            gap="var(--space-1)",
            align="stretch",
        ),
        rx.foreach(
            ref["values"],  # type: ignore[index]
            lambda val, val_index: ref_filter_value(ref, index, val, val_index),
        ),
        rx.button(
            f"{AdvancedSearchState.label_reference_filter_add_value} {ref.field_label}",
            variant="ghost",
            color_scheme="jade",
            size="1",
            on_click=lambda: AdvancedSearchState.add_ref_filter_value(index, ""),  # type: ignore[operator]
            class_name="truncate",
            style=rx.Style(
                align_self="end", margin_right="0", max_width="60%", display="block"
            ),
            custom_attrs={"data-testid": f"ref-filter-{index}-add-value"},
        ),
        align="stretch",
    )


def filter_references() -> rx.Component:
    """Render filter references page."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(
                    AdvancedSearchState.label_reference_filter_title,
                    style=rx.Style(userSelect="none"),
                ),
                rx.button(
                    rx.icon("plus"),
                    on_click=AdvancedSearchState.add_ref_filter(
                        AdvancedSearchState.all_fields_for_entity_types[0].value  # type: ignore[attr-defined]
                    ),  # type: ignore[operator]
                    variant="ghost",
                    color_scheme="jade",
                    style=rx.Style(margin_left="auto"),
                    custom_attrs={"data-testid": "add-reference-filter-button"},
                    size="1",
                ),
            ),
            rx.vstack(
                rx.foreach(
                    AdvancedSearchState.refs,
                    ref_filter,
                ),
                align="stretch",
                spacing="4",
            ),
            align="stretch",
        )
    )


def sidebar() -> rx.Component:
    """Render sidebar with filters for the search page."""
    return rx.vstack(
        filter_query(),
        filter_entity_type(),
        filter_references(),
        spacing="4",
        align="stretch",
        custom_attrs={"data-testid": "advanced-search-sidebar"},
        style=rx.Style(flex="0 0 300px"),
    )


def search_results() -> rx.Component:
    """Render search results page."""
    return rx.cond(
        AdvancedSearchState.is_searching,
        rx.center(
            rx.spinner(size="3"),
            style=rx.Style(
                marginTop="var(--space-6)",
                width="100%",
            ),
        ),
        search_results_component(
            AdvancedSearchState.search_results,
            options=SearchResultsComponentOptions(
                summary_text=AdvancedSearchState.label_result_summary_format,
                list_options=SearchResultsListOptions(
                    item_options=SearchResultsListItemOptions(enable_title_href=True)
                ),
                pagination_options=build_pagination_options(
                    AdvancedSearchState,
                    AdvancedSearchState.search,  # type: ignore[arg-type]
                    AdvancedSearchState.resolve_identifiers,
                ),
            ),
            style=rx.Style(
                flex=1,
                width="75%",
            ),
        ),
    )


def index() -> rx.Component:
    """Render index for the advanced search page."""
    return page(
        rx.hstack(
            sidebar(),
            search_results(),
            style=rx.Style(width="100%"),
            custom_attrs={"data-testid": "search-body"},
        )
    )

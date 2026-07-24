from collections.abc import Callable
from dataclasses import dataclass, field

import reflex as rx
from reflex.event import EventCallback

from mex.admin.components import (
    icon_by_stem_type,
    render_additional_titles,
    render_title,
    render_value,
)
from mex.admin.models import AdminValue, SearchResult
from mex.admin.pagination_component import PaginationOptions, pagination


@dataclass
class SearchResultsListItemOptions:
    """Options for rendering a search results list item."""

    enable_show_all_properties: bool = False
    on_toggle_show_all_properties: EventCallback[SearchResult, int] | None = None

    enable_title_href: bool = False

    render_title_fn: Callable[[SearchResult, int], rx.Component] | None = None
    render_prepend_fn: Callable[[SearchResult, int], rx.Component] | None = None
    render_append_fn: Callable[[SearchResult, int], rx.Component] | None = None


@dataclass
class SearchResultsListOptions:
    """Options for rendering a search results list."""

    item_options: SearchResultsListItemOptions = field(
        default_factory=SearchResultsListItemOptions
    )


def _render_properties(
    properties: list[AdminValue], property_type: str
) -> rx.Component:
    """Render a list of properties."""
    return rx.hstack(
        rx.foreach(
            properties,
            render_value,
        ),
        style=rx.Style(
            color="var(--gray-12)",
            fontWeight="var(--font-weight-light)",
        ),
        wrap="wrap",
        align="center",
        custom_attrs={"data-testid": f"display-properties-{property_type}"},
    )


def _search_results_item(
    item: SearchResult, index: int, options: SearchResultsListItemOptions
) -> rx.Component:
    """Render a search results item."""
    title = render_title(item.title[0])

    title_line_children = [
        icon_by_stem_type(
            item.stem_type,
            size=22,
            style=rx.Style(color=rx.color("accent", 11)),
        ),
        rx.link(
            title,
            href=f"/item/{item.identifier}",
        )
        if options.enable_title_href
        else title,
        render_additional_titles(item.title[1:]),
    ]

    if options.enable_show_all_properties ^ bool(options.on_toggle_show_all_properties):
        error_msg = "'enable_show_all_properties' is 'True' but "
        "'on_toggle_show_all_properties' is not set; or vice versa."
        raise ValueError(error_msg)

    if options.enable_show_all_properties and options.on_toggle_show_all_properties:
        title_line_children.append(
            rx.button(
                rx.icon(
                    rx.cond(
                        item.show_all_properties,
                        "minimize_2",
                        "maximize_2",
                    ),
                    style=rx.Style(width="1em", height="1em"),
                ),
                color_scheme="gray",
                variant="surface",
                size="1",
                on_click=options.on_toggle_show_all_properties(item, index),
                custom_attrs={"data-testid": "toggle-show-all-properties-button"},
            )
        )

    if options.render_title_fn:
        title_line_children.append(options.render_title_fn(item, index))

    vstack_children: list[rx.Component] = [
        rx.hstack(*title_line_children, align="center")
    ]
    if options.enable_show_all_properties:
        vstack_children.append(
            rx.cond(
                item.show_all_properties,
                _render_properties(item.all_properties, "all"),
                _render_properties(item.preview, "preview"),
            )
        )
    else:
        vstack_children.append(_render_properties(item.preview, "preview"))

    card_content = []
    if options.render_prepend_fn:
        card_content.append(options.render_prepend_fn(item, index))

    card_content.append(
        rx.vstack(
            *vstack_children,
            align="stretch",
            style=rx.Style(width="100%", flex="1", min_width="0"),
        )
    )

    if options.render_append_fn:
        card_content.append(options.render_append_fn(item, index))

    return rx.card(
        rx.hstack(
            *card_content,
            align="stretch",
        ),
        class_name="search-result-card",
        custom_attrs={"data-testid": f"search-result-{item.identifier}"},
        style=rx.Style(width="100%", flex="1 0 auto", min_height="0"),
    )


def search_results_list(
    items: list[SearchResult] | rx.Var[list[SearchResult]],
    options: SearchResultsListOptions | None = None,
    style: rx.Style | None = None,
) -> rx.Component:
    """Render a list of search results items."""
    options = options or SearchResultsListOptions()

    used_style = rx.Style(overflow="auto")
    used_style.update(style or {})

    return rx.cond(
        items,
        rx.vstack(
            rx.foreach(
                items, lambda x, i: _search_results_item(x, i, options.item_options)
            ),
            style=used_style,
            custom_attrs={"data-testid": "search-results-list"},
        ),
    )


def search_results_summary(summary_text: rx.Var[str]) -> rx.Component:
    """Render the search results summary text."""
    return rx.text(
        summary_text,
        style=rx.Style(
            color="var(--gray-12)",
            fontWeight="var(--font-weight-bold)",
            margin="var(--space-4)",
            userSelect="none",
        ),
        custom_attrs={"data-testid": "search-results-summary"},
    )


@dataclass
class SearchResultsComponentOptions:
    """Options for the search results component."""

    summary_text: rx.Var[str]
    list_options: SearchResultsListOptions
    pagination_options: PaginationOptions | None = None


def search_results_component(
    results: rx.Var[list[SearchResult]] | list[SearchResult],
    options: SearchResultsComponentOptions,
    style: rx.Style | None = None,
) -> rx.Component:
    """Render the search result component with summary, list, and pagination."""
    used_style = rx.Style(overflow="auto")
    used_style.update(style or {})

    content = [
        rx.center(search_results_summary(options.summary_text)),
        search_results_list(
            results,
            options.list_options,
        ),
    ]
    if options.pagination_options:
        content.append(rx.center(pagination(options.pagination_options)))

    return rx.vstack(
        *content,
        spacing="4",
        custom_attrs={"data-testid": "search-results-component"},
        align="stretch",
        style=used_style,
    )

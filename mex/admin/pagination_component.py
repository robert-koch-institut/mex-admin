import math
from dataclasses import dataclass
from typing import Any

import reflex as rx
from reflex.event import EventType
from reflex.vars import Var

from mex.admin.state import State

# the most pages we offer in the page select, before we start thinning them out
PAGE_SELECTION_LIMIT = 25
# the multiple that thinned out pages are rounded down to, for legible page numbers
PAGE_SELECTION_ROUNDING = 10


class PaginationStateMixin(rx.State, mixin=True):
    """State-Mixin for pagination behavior."""

    total: int = 0
    limit: int = 50
    current_page: int = 1

    @rx.var
    def max_page(self) -> int:
        """Return the maximum page, based on total and limit."""
        return math.ceil(self.total / self.limit)

    @rx.var
    def skip(self) -> int:
        """Return the skip/offset, based on limit and current_page."""
        return self.limit * (self.current_page - 1)

    @rx.var
    def page_selection(self) -> list[str]:
        """Return the selectable pages, thinned out when there are too many.

        Up to `PAGE_SELECTION_LIMIT` pages are offered one by one. Beyond that, the
        pages are spread evenly across that many steps and each step is rounded down
        to a multiple of `PAGE_SELECTION_ROUNDING` (e.g. 90, 190, 290 for 2490 pages).
        Rounding is skipped when the steps are shorter than the rounding itself,
        because it would collapse them all onto the same handful of pages.
        """
        if self.max_page <= PAGE_SELECTION_LIMIT:
            return [f"{i + 1}" for i in range(self.max_page)]
        pages = {
            i * self.max_page // PAGE_SELECTION_LIMIT
            for i in range(1, PAGE_SELECTION_LIMIT + 1)
        }
        if self.max_page >= PAGE_SELECTION_LIMIT * PAGE_SELECTION_ROUNDING:
            pages = {
                max(page // PAGE_SELECTION_ROUNDING * PAGE_SELECTION_ROUNDING, 1)
                for page in pages
            }
        # keep the current page selectable, so the select can display its own value
        pages.add(self.current_page)
        return [f"{page}" for page in sorted(pages)]

    @rx.var
    def disable_page_selection(self) -> bool:
        """Whether the page selection in the pagination should be disabled."""
        return self.current_page >= self.max_page

    @rx.var
    def disable_previous_page(self) -> bool:
        """Disable the 'Previous' button if on the first page."""
        return self.current_page <= 1

    @rx.var
    def disable_next_page(self) -> bool:
        """Disable the 'Next' button if on the last page."""
        return self.current_page >= self.max_page

    @rx.event
    def set_total(self, total: int) -> None:
        """Set the total of the pagination."""
        self.total = total
        self.set_current_page(self.current_page)  # type: ignore[operator]

    @rx.event
    def set_current_page(self, page_number: str | int) -> None:
        """Set the current page (coerced to be between 1 and max_page)."""
        page_number = int(page_number) if page_number else 1
        self.current_page = max(min(page_number, self.max_page), 1)

    @rx.event
    def go_to_first_page(self) -> None:
        """Navigate to the first page."""
        self.current_page = 1

    @rx.event
    def go_to_previous_page(self) -> None:
        """Navigate to the previous page."""
        self.set_current_page(self.current_page - 1)  # type: ignore[operator]

    @rx.event
    def go_to_next_page(self) -> None:
        """Navigate to the next page."""
        self.set_current_page(self.current_page + 1)  # type: ignore[operator]

    @rx.event
    def reset_pagination(self) -> None:
        """Reset the pagination to its default values."""
        self.total = 0
        self.current_page = 1
        self.limit = self.get_fields()["limit"].default  # type: ignore[assignment]


@dataclass
class PaginationPageOptions:
    """Options for the pagination component."""

    current_page: int | Var[int]
    pages: list[str] | Var[list[str]]
    disabled: bool | Var[bool]
    on_change: EventType[()] | None = None


@dataclass
class PaginationButtonOptions:
    """Options for a pagination button."""

    disabled: bool | Var[bool]
    on_click: EventType[()] | None = None


@dataclass
class PaginationOptions:
    """Options for the pagination component."""

    prev_options: PaginationButtonOptions
    next_options: PaginationButtonOptions
    page_options: PaginationPageOptions

    @staticmethod
    def create(
        state: PaginationStateMixin | type[PaginationStateMixin],
        on_page_change: EventType[()] | None = None,
    ) -> PaginationOptions:
        """Create pagination options for a given state.

        Args:
            state: The state to create the options for.
            on_page_change: EventHandler that gets executed when the current_page
                            changes. Defaults to None.
        """
        prev_click = (
            [state.go_to_previous_page, on_page_change]
            if on_page_change
            else [state.go_to_previous_page]
        )
        next_click = (
            [state.go_to_next_page, on_page_change]
            if on_page_change
            else [state.go_to_next_page]
        )
        change_page = (
            [state.set_current_page, on_page_change]
            if on_page_change
            else [state.set_current_page]
        )

        return PaginationOptions(
            PaginationButtonOptions(state.disable_previous_page, prev_click),
            PaginationButtonOptions(state.disable_next_page, next_click),
            PaginationPageOptions(
                state.current_page,
                state.page_selection,
                state.disable_page_selection,
                change_page,
            ),
        )


def pagination(
    options: PaginationOptions,
    style: rx.Style | dict[str, Any] | None = None,
) -> rx.Component:
    """Create pagination based on given options."""
    style = rx.Style().update(style)
    return rx.flex(
        rx.button(
            rx.text(State.label_pagination_previous_button),
            on_click=options.prev_options.on_click,
            disabled=options.prev_options.disabled,
            variant="surface",
            custom_attrs={"data-testid": "pagination-previous-button"},
            style=rx.Style(minWidth="10%"),
        ),
        rx.select(
            options.page_options.pages,
            value=options.page_options.current_page.to_string()
            if isinstance(options.page_options.current_page, Var)
            else f"{options.page_options.current_page}",
            on_change=options.page_options.on_change,
            disabled=options.page_options.disabled,
            custom_attrs={"data-testid": "pagination-page-select"},
        ),
        rx.button(
            rx.text(State.label_pagination_next_button, weight="bold"),
            on_click=options.next_options.on_click,
            disabled=options.next_options.disabled,
            variant="surface",
            custom_attrs={"data-testid": "pagination-next-button"},
            style=rx.Style(minWidth="10%"),
        ),
        spacing="4",
        style=style,
    )

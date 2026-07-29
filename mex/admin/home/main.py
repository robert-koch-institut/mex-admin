import reflex as rx

from mex.admin.home.state import HomeState
from mex.admin.layout import page


def start_search_input() -> rx.Component:
    """Render a wide search input that sends the user to the search page."""
    return rx.card(
        rx.form.root(
            rx.hstack(
                rx.input(
                    max_length=100,
                    name="query_string",
                    placeholder=HomeState.label_search_input_placeholder,
                    width="100%",
                    auto_focus=True,
                    tab_index=1,
                    type="text",
                    custom_attrs={"data-testid": "start-search-input"},
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("search"),
                    type="submit",
                    variant="surface",
                    custom_attrs={"data-testid": "start-search-button"},
                ),
                width="100%",
            ),
            on_submit=HomeState.handle_submit,
        ),
        style=rx.Style(
            maxWidth="100%",
            width="calc(720px * var(--scaling))",
        ),
    )


def index() -> rx.Component:
    """Return the index for the start page."""
    return page(
        rx.center(
            start_search_input(),
            style=rx.Style(
                marginTop="20vh",
                width="100%",
            ),
            custom_attrs={"data-testid": "start-page-body"},
        )
    )

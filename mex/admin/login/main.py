import reflex as rx
from reflex.event import EventType

from mex.admin.layout import app_logo
from mex.admin.login.state import LoginMExState, LoginState


def login_user() -> rx.Component:
    """Return a form field for the user name."""
    return rx.vstack(
        rx.text(LoginState.label_username),
        rx.input(
            name="username",
            auto_focus=True,
            on_change=LoginState.set_username,
            placeholder=LoginState.label_username,
            size="3",
            tab_index=1,
            style=rx.Style(width="100%"),
            custom_attrs={"data-testid": "input-username"},
        ),
        style=rx.Style(width="100%"),
    )


def login_password() -> rx.Component:
    """Return a form field for the password."""
    return rx.vstack(
        rx.text(LoginState.label_password),
        rx.input(
            on_change=LoginState.set_password,
            name="password",
            placeholder=LoginState.label_password,
            size="3",
            tab_index=2,
            type="password",
            style=rx.Style(width="100%"),
            custom_attrs={"data-testid": "input-password"},
        ),
        style=rx.Style(width="100%"),
    )


def login_button() -> rx.Component:
    """Return a submit button for the login form."""
    return rx.hstack(
        rx.spacer(),
        rx.button(
            LoginState.label_button_login,
            size="3",
            tab_index=3,
            style=rx.Style(
                padding="0 var(--space-6)",
                marginTop="var(--space-4)",
            ),
            custom_attrs={"data-testid": "login-button"},
            type="submit",
        ),
        style=rx.Style(width="100%"),
    )


def login_form(login_callback: EventType[()]) -> rx.Component:
    """Return a login form."""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.hstack(
                    app_logo(),
                    style=rx.Style(width="100%"),
                ),
                rx.divider(size="4"),
                rx.form(
                    rx.vstack(
                        login_user(),
                        login_password(),
                        login_button(),
                        style=rx.Style(width="100%"),
                    ),
                    on_submit=login_callback,
                    spacing="4",
                ),
            ),
            style=rx.Style(
                width="calc(340px * var(--scaling))",
                padding="var(--space-4)",
                top="20vh",
            ),
            custom_attrs={"data-testid": "login-card"},
        )
    )


def mex_login() -> rx.Component:
    """Return the index for the login component."""
    return login_form(LoginMExState.login)

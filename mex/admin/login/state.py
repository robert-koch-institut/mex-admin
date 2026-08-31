from collections.abc import Generator

import reflex as rx
from reflex.event import EventSpec

from mex.admin.label_var import label_var
from mex.admin.models import User
from mex.admin.security import has_read_access_mex, has_write_access_mex
from mex.admin.state import State


class LoginState(State):
    """State management for the login page."""

    username: str
    password: str

    @rx.event
    def set_username(self, username: str) -> None:
        """Set the username."""
        self.username = username

    @rx.event
    def set_password(self, password: str) -> None:
        """Set the password."""
        self.password = password

    @label_var(label_id="login.username")
    def label_username(self) -> None:
        """Label for username."""

    @label_var(label_id="login.password")
    def label_password(self) -> None:
        """Label for password."""

    @label_var(label_id="login.button_login")
    def label_button_login(self) -> None:
        """Label for button_login."""

    @label_var(label_id="login.invalid_credentials")
    def label_invalid_credentials(self) -> None:
        """Label for invalid_credentials."""


class LoginMExState(LoginState):
    """State management for the login page."""

    @rx.event
    def login(self) -> Generator[EventSpec]:
        """Login a user."""
        read_access = has_read_access_mex(self.username, self.password)
        write_access = has_write_access_mex(self.username, self.password)
        if read_access:
            self.user = User(
                name=self.username,
                write_access=write_access,
            )
            target_path_after_login = self.target_path_after_login or "/"
            # reset username/password
            self.reset()  # type: ignore[no-untyped-call]
            yield rx.redirect(target_path_after_login, replace=True)
        else:
            yield rx.toast.error(
                self.label_invalid_credentials, class_name="editor-toast"
            )

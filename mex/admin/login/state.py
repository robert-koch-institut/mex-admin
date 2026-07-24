from collections.abc import Generator

import reflex as rx
from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error
from mex.admin.label_var import label_var
from mex.admin.models import MergedLoginPerson, User
from mex.admin.security import has_read_access_mex, has_write_access_mex
from mex.admin.state import State
from mex.common.backend_api.connector import LDAPBackendApiConnector


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


class LoginLdapState(LoginState):
    """State management for the login page."""

    @rx.event
    def login(self) -> Generator[EventSpec]:
        """Login a user."""
        connector = LDAPBackendApiConnector.get()
        try:
            response = connector.merged_person_from_login(self.username, self.password)
        except RequestException as exc:
            yield from escalate_error(
                "backend", "Cannot reach backend. Please try again later.", exc
            )
            return
        if response:
            self.user_ldap = User(
                name=self.username,
                write_access=True,
            )
            self.merged_login_person = MergedLoginPerson(
                identifier=response.identifier,
                full_name=response.fullName,
                email=response.email,
                orcid_id=response.orcidId,
            )
            target_path_after_login = self.target_path_after_login or "/"
            # reset username/password
            self.reset()  # type: ignore[no-untyped-call]
            yield rx.redirect(target_path_after_login, replace=True)
        else:
            yield rx.toast.error(
                self.label_invalid_credentials, class_name="admin-toast"
            )


class LoginMExState(LoginState):
    """State management for the login page."""

    @rx.event
    def login(self) -> Generator[EventSpec]:
        """Login a user."""
        read_access = has_read_access_mex(self.username, self.password)
        write_access = has_write_access_mex(self.username, self.password)
        if read_access:
            self.user_mex = User(
                name=self.username,
                write_access=write_access,
            )
            target_path_after_login = self.target_path_after_login or "/"
            # reset username/password
            self.reset()  # type: ignore[no-untyped-call]
            yield rx.redirect(target_path_after_login, replace=True)
        else:
            yield rx.toast.error(
                self.label_invalid_credentials, class_name="admin-toast"
            )

from collections.abc import Generator, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

import reflex as rx
from reflex.event import EventSpec
from reflex.istate.data import ReflexURL

from mex.admin.label_var import label_var
from mex.admin.locale_service import LocaleService
from mex.admin.models import NavItem, User
from mex.admin.utils import replace_url_params
from mex.common.models import MEX_PRIMARY_SOURCE_STABLE_TARGET_ID


class State(rx.State):
    """The base state for the app."""

    _locale_service = LocaleService.get()
    _available_locales = _locale_service.get_available_locales()

    current_locale: str = next(
        (x for x in _available_locales if x.id.lower().startswith("de")),
        _available_locales[0],
    ).id
    navigate_target: str | None = None
    user: User | None = None
    target_path_after_login: str | None = None
    is_unsaved_changes_dialog_open: bool = False

    _nav_items: list[NavItem] = [
        NavItem(
            title="layout.nav_bar.search_navitem",
            route_ids=["/search"],
            raw_path="/search",
        ),
        NavItem(
            title="layout.nav_bar.advanced_search_navitem",
            route_ids=["/advanced-search"],
            raw_path="/advanced-search/?page=1",
        ),
        NavItem(
            title="layout.nav_bar.create_navitem",
            route_ids=["/create", "/create/[draft_id]"],
            raw_path="/create",
            requires_write=True,
        ),
        NavItem(
            title="layout.nav_bar.edit_navitem",
            route_ids=["/item/[item_id]"],
            raw_path=f"/item/{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
        ),
        NavItem(
            title="layout.nav_bar.merge_navitem",
            route_ids=["/merge"],
            raw_path="/merge",
            requires_write=True,
        ),
        NavItem(
            title="layout.nav_bar.ingest_navitem",
            route_ids=["/ingest"],
            raw_path="/ingest",
            requires_write=True,
        ),
    ]

    @rx.var
    def has_write_access(self) -> bool:
        """Whether the logged-in MEx user may trigger backend writes."""
        return bool(self.user and self.user.write_access)

    def _translate_nav_item(self, item: NavItem) -> NavItem:
        return NavItem(
            title=self._locale_service.get_ui_label(self.current_locale, item.title),
            **item.model_dump(exclude={"title"}),
        )

    @rx.var(deps=["current_locale", "user"])
    def nav_items_translated(self) -> list[NavItem]:
        """The Navbar items with locale sensitive label, filtered by access rights."""
        return [
            self._translate_nav_item(item)
            for item in self._nav_items
            if self.has_write_access or not item.requires_write
        ]

    @rx.event
    def set_is_unsaved_changes_dialog_open(self, is_open: bool) -> None:  # noqa: FBT001
        """Set the state of the unsaved changes dialog.

        Args:
            is_open: Whether the dialog should be open or not.
        """
        self.is_unsaved_changes_dialog_open = is_open

    @rx.event
    def change_locale(self, locale: str) -> None:
        """Change the current locale to the given one and reload the page.

        Args:
            locale: The locale to change to.
        """
        self.current_locale = locale

    @rx.event
    def logout(self) -> Generator[EventSpec]:
        """Log out a user."""
        self.reset()  # type: ignore[no-untyped-call]
        yield rx.redirect("/")

    @staticmethod
    def _strip_frontend_path(url: ReflexURL) -> str:
        config = rx.config.get_config()
        parsed = urlparse(url)
        path = parsed.path
        if path.startswith(config.frontend_path):
            path = path[len(config.frontend_path) :] or "/"
        return str(urlunparse(parsed._replace(path=path)))

    @rx.event
    def check_mex_login(self) -> Generator[EventSpec]:
        """Check if a user is logged in."""
        if self.user is None:
            self.target_path_after_login = self._strip_frontend_path(self.router.url)
            yield rx.redirect("/login", replace=True)

    def push_url_params(
        self,
        params: Mapping[str, int | str | Sequence[int | str]],
    ) -> EventSpec | None:
        """Event handler to push updated url parameter to the browser history."""
        for nav_item in self._nav_items:
            if self.router.route_id in nav_item.route_ids:
                url = replace_url_params(self.router.url, params)
                return rx.call_script(f"window.history.pushState(null, '', '{url}');")
        return None

    @rx.event
    def load_nav(self) -> None:
        """Event hook for updating the navigation on page loads."""
        for nav_item in self._nav_items:
            nav_item.active = self.router.route_id in nav_item.route_ids

    @label_var(label_id="components.titles.additional_titles")
    def label_additional_titles(self) -> None:
        """Label for titles.additional_titles."""

    @label_var(label_id="components.pagination.next_button")
    def label_pagination_next_button(self) -> None:
        """Label for pagination.next_button."""

    @label_var(label_id="components.pagination.previous_button")
    def label_pagination_previous_button(self) -> None:
        """Label for pagination.previous_button."""

    @label_var(label_id="layout.nav_bar.logout_button")
    def label_nav_bar_logout_button(self) -> None:
        """Label for nav_bar.logout_button."""

    @label_var(label_id="layout.unsaved_changes_dialog.title")
    def label_unsaved_changes_dialog_title(self) -> None:
        """Label for unsaved_changes_dialog.title."""

    @label_var(label_id="layout.unsaved_changes_dialog.description")
    def label_unsaved_changes_dialog_description(self) -> None:
        """Label for unsaved_changes_dialog.description."""

    @label_var(label_id="layout.unsaved_changes_dialog.description_draft")
    def label_unsaved_changes_dialog_description_draft(self) -> None:
        """Label for unsaved_changes_dialog.description_draft."""

    @label_var(label_id="layout.unsaved_changes_dialog.description_edit")
    def label_unsaved_changes_dialog_description_edit(self) -> None:
        """Label for unsaved_changes_dialog.description_edit."""

    @label_var(label_id="layout.unsaved_changes_dialog.cancel_button")
    def label_unsaved_changes_dialog_cancel_button(self) -> None:
        """Label for unsaved_changes_dialog.cancel_button."""

    @label_var(label_id="layout.unsaved_changes_dialog.logout_button")
    def label_unsaved_changes_dialog_logout_button(self) -> None:
        """Label for unsaved_changes_dialog.logout_button."""

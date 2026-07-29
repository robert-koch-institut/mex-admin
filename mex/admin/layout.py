from collections.abc import Callable
from typing import Literal, cast

import reflex as rx

from mex.admin.components import icon_by_stem_type, render_title
from mex.admin.create.state import CreateState
from mex.admin.edit.state import EditState
from mex.admin.locale_service import LocaleService
from mex.admin.models import NavItem, User
from mex.admin.rules.models import UserDraft
from mex.admin.rules.state import RuleState
from mex.admin.state import State

locale_service = LocaleService.get()


def user_button(
    user_type: Literal["user_mex", "user_ldap"] = "user_mex",
) -> rx.Component:
    """Return a user button with an icon that indicates their access rights."""
    user = getattr(State, user_type)
    return rx.button(
        rx.cond(
            cast("User", user).write_access,
            rx.icon("user_round_cog"),
            rx.icon("user_round"),
        ),
        variant="ghost",
        style=rx.Style(marginTop="0"),
    )


def unsaved_changes_dialog() -> rx.Component:
    """Return a dialog that informs the user about unsaved changes."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(State.label_unsaved_changes_dialog_title),
            rx.alert_dialog.description(
                State.label_unsaved_changes_dialog_description,
                size="2",
            ),
            rx.unordered_list(
                rx.list_item(
                    f"{CreateState.draft_count} {State.label_unsaved_changes_dialog_description_draft}",  # noqa: E501
                ),
                rx.list_item(
                    f"{EditState.edit_count} {State.label_unsaved_changes_dialog_description_edit}",  # noqa: E501
                ),
            ),
            rx.flex(
                rx.alert_dialog.action(
                    rx.button(
                        State.label_unsaved_changes_dialog_logout_button,
                        on_click=State.logout,
                        color_scheme="tomato",
                        variant="solid",
                        custom_attrs={
                            "data-testid": "unsaved-changes-dialog-logout-button"
                        },
                    ),
                ),
                rx.alert_dialog.cancel(
                    rx.button(
                        State.label_unsaved_changes_dialog_cancel_button,
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.set_is_unsaved_changes_dialog_open(False),  # type: ignore[operator]
                        custom_attrs={
                            "data-testid": "unsaved-changes-dialog-cancel-button"
                        },
                    ),
                ),
                spacing="3",
                margin_top="16px",
                justify="end",
            ),
            custom_attrs={"data-testid": "unsaved-changes-dialog"},
        ),
        open=State.is_unsaved_changes_dialog_open,
    )


def user_menu(user_type: Literal["user_mex", "user_ldap"] = "user_mex") -> rx.Component:
    """Return a user menu with a trigger, the user's name and a logout button."""
    user = getattr(State, user_type)
    return rx.menu.root(
        rx.menu.trigger(
            user_button(user_type),
            custom_attrs={"data-testid": "user-menu"},
        ),
        rx.menu.content(
            rx.menu.item(cast("User", user).name, disabled=True),
            rx.menu.separator(),
            rx.menu.item(
                State.label_nav_bar_logout_button,
                on_select=rx.cond(
                    CreateState.draft_count + EditState.edit_count,
                    State.set_is_unsaved_changes_dialog_open(True),  # type: ignore[operator]
                    State.logout,
                ),
                custom_attrs={"data-testid": "logout-button"},
            ),
            align="end",
        ),
    )


def language_switcher() -> rx.Component:
    """Render a language switcher."""
    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                State.current_locale,
                style=rx.Style(fontWeight="var(--font-weight-medium)"),
                variant="ghost",
            ),
            custom_attrs={"data-testid": "language-switcher"},
        ),
        rx.menu.content(
            rx.foreach(
                locale_service.get_available_locales(),
                lambda locale: rx.menu.item(
                    rx.text(locale.label),
                    on_click=State.change_locale(locale.id),  # type: ignore[operator]
                    custom_attrs={
                        "data-testid": f"language-switcher-menu-item-{locale.id}"
                    },
                ),
            )
        ),
    )


def render_draft_menu_item(dict_entry: tuple[str, UserDraft]) -> rx.Component:
    """Render a navigable menu item for the given draft."""
    draft = dict_entry[1]
    return rx.menu.item(
        rx.link(
            rx.hstack(
                icon_by_stem_type(
                    draft.stem_type,
                    size=22,
                    style=rx.Style(color=rx.color("accent", 11), flexShrink="0"),
                ),
                render_title(draft.title),
            ),
            href=f"/create/{draft.identifier}",
            style=rx.Style({"flex": "1", "minWidth": "0", "overflow": "hidden"}),
        ),
        custom_attrs={"data-testid": f"draft-{draft.identifier}-menu-item"},
    )


def nav_link(item: NavItem) -> rx.Component:
    """Return a link component for the given navigation item."""
    link = rx.link(
        rx.text(item.title, size="4", weight="medium"),
        href=item.raw_path,
        underline=rx.cond(item.active, "always", "none"),
        class_name=rx.cond(item.active, "nav-item nav-item-active", "nav-item"),
        custom_attrs={
            "data-testid": f"nav-item-{item.route_ids[0]}",
        },
    )

    return rx.cond(
        item.route_ids.contains("/create"),  # type: ignore[attr-defined]
        rx.cond(
            RuleState.draft_count,
            rx.fragment(
                link,
                rx.menu.root(
                    rx.menu.trigger(
                        rx.badge(
                            RuleState.draft_count,
                            style=rx.Style(
                                align_self="center",
                                margin_left="-1em",
                                cursor="pointer",
                                border="1px solid transparent",
                            ),
                            _hover={"border-color": f"{rx.color('accent', 8)}"},
                            custom_attrs={"data-testid": "draft-menu-trigger"},
                        ),
                    ),
                    rx.menu.content(
                        rx.foreach(RuleState.drafts, render_draft_menu_item)
                    ),
                ),
            ),
            link,
        ),
        link,
    )


def app_logo() -> rx.Component:
    """Return the app logo with icon and label, linking to the start page."""
    return rx.link(
        rx.hstack(
            rx.icon("circuit-board", size=28),
            rx.heading(
                "MEx Admin",
                weight="medium",
                style=rx.Style(userSelect="none"),
            ),
            custom_attrs={"data-testid": "app-logo"},
        ),
        href="/",
        underline="none",
        # keep the ambient colors, so linking does not change the logo's looks
        style=rx.Style(color="inherit"),
    )


def nav_bar(
    nav_items_source: list[NavItem] | None = None,
    user_type: Literal["user_mex", "user_ldap"] = "user_mex",
    logo_factory: Callable[[], rx.Component] = app_logo,
) -> rx.Component:
    """Return a navigation bar component."""
    nav_items_to_use = (
        nav_items_source if nav_items_source is not None else State.nav_items_translated
    )
    nav_items_section: rx.Component = (
        rx.fragment()
        if isinstance(nav_items_to_use, list) and not nav_items_to_use
        else rx.cond(
            nav_items_to_use,
            rx.fragment(
                rx.divider(orientation="vertical", size="2"),
                rx.hstack(
                    rx.foreach(nav_items_to_use, nav_link),
                    justify="start",
                    spacing="4",
                ),
            ),
        )
    )
    return rx.vstack(
        rx.box(
            style=rx.Style(
                height="var(--space-6)",
                width="100%",
                backdropFilter="var(--backdrop-filter-panel)",
            ),
        ),
        rx.card(
            rx.hstack(
                logo_factory(),
                nav_items_section,
                rx.spacer(),
                rx.hstack(
                    language_switcher(),
                    user_menu(user_type),
                    rx.button(
                        rx.icon("sun_moon"),
                        variant="ghost",
                        style=rx.Style(marginTop="0"),
                        on_click=rx.toggle_color_mode,
                    ),
                    style=rx.Style(alignItems="center"),
                    spacing="4",
                ),
                justify="between",
                align_items="center",
            ),
            size="2",
            custom_attrs={"data-testid": "nav-bar"},
            style=rx.Style(
                width="100%",
                marginTop="calc(-1 * var(--base-card-border-width))",
            ),
        ),
        spacing="0",
        style=rx.Style(
            maxWidth="var(--app-max-width)",
            minWidth="var(--app-min-width)",
            position="fixed",
            top="0",
            width="100%",
            zIndex="1000",
        ),
    )


def page(
    *children: rx.Component,
    user_type: Literal["user_mex", "user_ldap"] = "user_mex",
    nav_items_source: list[NavItem] | None = None,
    logo_factory: Callable[[], rx.Component] = app_logo,
) -> rx.Component:
    """Return a page fragment with navigation bar and given children.

    Args:
        *children: Components to render in the page body
        user_type: State attribute to check for user login
        nav_items_source: Custom navigation items, if None uses default
        logo_factory: Function that returns a logo component
    """
    user_check = getattr(State, user_type)
    navbar_component = nav_bar(nav_items_source, user_type, logo_factory)

    page_content = [
        navbar_component,
        rx.hstack(
            *children,
            style=rx.Style(
                maxWidth="var(--app-max-width)",
                minWidth="var(--app-min-width)",
                padding="calc(var(--space-6) * 4) var(--space-6) var(--space-6)",
                width="100%",
            ),
            custom_attrs={"data-testid": "page-body"},
        ),
        unsaved_changes_dialog(),
    ]

    return rx.cond(
        user_check,
        rx.center(
            *page_content,
            style=rx.Style(
                {
                    "--app-max-width": "calc(1480px * var(--scaling))",
                    "--app-min-width": "calc(800px * var(--scaling))",
                    "width": "100%",
                }
            ),
        ),
        rx.center(
            rx.spinner(size="3"),
            style=rx.Style(marginTop="40vh"),
        ),
    )

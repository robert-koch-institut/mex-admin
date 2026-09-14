from typing import cast

import reflex as rx

from mex.admin.components import icon_by_stem_type, render_title
from mex.admin.create.state import CreateState
from mex.admin.edit.state import EditState
from mex.admin.locale_service import LocaleService, MExLocale
from mex.admin.models import NavItem, User
from mex.admin.rules.models import UserDraft
from mex.admin.rules.state import RuleState
from mex.admin.state import State

locale_service = LocaleService.get()

# The nav bar is a solid accent surface, so its children cannot rely on the
# theme's default foreground colors. These vars are declared on the nav bar and
# inherited by everything inside it.
NAV_BAR_PALETTE = {
    "--nav-bar-bg": "var(--accent-11)",
    "--nav-bar-fg": "var(--accent-contrast)",
    "--nav-bar-button-bg": "var(--accent-12)",
    "--nav-bar-button-bg-hover": (
        "color-mix(in srgb, var(--accent-12) 70%, var(--accent-11))"
    ),
}


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


def logout_button() -> rx.Component:
    """Return a logout button with a trailing arrow icon."""
    return rx.button(
        State.label_nav_bar_logout_button,
        rx.icon("arrow-right", size=18),
        on_click=rx.cond(
            CreateState.draft_count + EditState.edit_count,
            State.set_is_unsaved_changes_dialog_open(True),  # type: ignore[operator]
            State.logout,
        ),
        variant="solid",
        style=rx.Style(
            margin="0",
            # fixed width, so translating the label does not shift the nav bar
            width="calc(140px * var(--scaling))",
            backgroundColor="var(--nav-bar-button-bg)",
            color="var(--nav-bar-fg)",
        ),
        _hover={"backgroundColor": "var(--nav-bar-button-bg-hover)"},
        custom_attrs={"data-testid": "logout-button"},
    )


def user_menu() -> rx.Component:
    """Return a flat user menu with the current user's name and a logout button."""
    return rx.hstack(
        rx.text(
            cast("User", State.user).name,
            style=rx.Style(userSelect="none", whiteSpace="nowrap"),
        ),
        logout_button(),
        spacing="3",
        style=rx.Style(alignItems="center"),
        custom_attrs={"data-testid": "user-menu"},
    )


def language_switcher_segment(locale: MExLocale) -> rx.Component:
    """Render one segment of the language switcher for the given locale."""
    is_current = State.current_locale == locale.id
    return rx.button(
        locale.code,
        on_click=State.change_locale(locale.id),  # type: ignore[operator]
        title=locale.label,
        variant="ghost",
        radius="none",
        style=rx.Style(
            margin="0",
            paddingLeft="var(--space-3)",
            paddingRight="var(--space-3)",
            fontWeight="var(--font-weight-bold)",
            backgroundColor=rx.cond(
                is_current, "var(--nav-bar-button-bg)", "transparent"
            ),
            color="var(--nav-bar-fg)",
        ),
        _hover={"backgroundColor": "var(--nav-bar-button-bg-hover)"},
        custom_attrs={
            "data-testid": f"language-switcher-{locale.id}",
            "aria-pressed": is_current,
        },
    )


def language_switcher() -> rx.Component:
    """Render a language switcher with one button segment per available locale."""
    return rx.hstack(
        rx.foreach(
            locale_service.get_available_locales(),
            language_switcher_segment,
        ),
        spacing="0",
        style=rx.Style(
            alignItems="stretch",
            border="1px solid var(--nav-bar-button-bg)",
            borderRadius="var(--radius-3)",
            overflow="hidden",
        ),
        custom_attrs={"data-testid": "language-switcher"},
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
        # radix links are accent colored, which is unreadable on the accent fill
        style=rx.Style(
            color="var(--nav-bar-fg)",
            # `underline` only sets the line, leaving radix's near transparent
            # accent-a5 decoration color, which vanishes on the accent fill
            textDecorationColor="var(--nav-bar-fg)",
            # 1px matches the nav bar divider, so the two lines agree
            textDecorationThickness="1px",
            textUnderlineOffset="6px",
        ),
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
                                # the soft accent badge disappears on the accent fill
                                backgroundColor="var(--nav-bar-button-bg)",
                                color="var(--nav-bar-fg)",
                            ),
                            _hover={"border-color": "var(--nav-bar-fg)"},
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


def mex_wordmark() -> rx.Component:
    """Return the MEx wordmark, tinted with the surrounding text color.

    The svg is used as a mask rather than an image, so that the same asset works
    on the light login card and on the solid accent nav bar.
    """
    return rx.box(
        style=rx.Style(
            {
                # the intrinsic size of assets/mex-logo.svg is 66x25
                "height": "calc(25px * var(--scaling))",
                "width": "calc(66px * var(--scaling))",
                "flexShrink": "0",
                "backgroundColor": "currentColor",
                "maskImage": "url(/mex-logo.svg)",
                "maskRepeat": "no-repeat",
                "maskSize": "contain",
                "maskPosition": "center",
                "WebkitMaskImage": "url(/mex-logo.svg)",
                "WebkitMaskRepeat": "no-repeat",
                "WebkitMaskSize": "contain",
                "WebkitMaskPosition": "center",
            }
        ),
        role="img",
        aria_label="MEx",
    )


def app_logo() -> rx.Component:
    """Return the app logo with the MEx wordmark and the app name."""
    return rx.hstack(
        mex_wordmark(),
        rx.heading(
            "Admin",
            weight="medium",
            style=rx.Style(userSelect="none"),
        ),
        spacing="3",
        align="center",
        custom_attrs={"data-testid": "app-logo"},
    )


def app_logo_link() -> rx.Component:
    """Return the app logo, linking to the start page."""
    return rx.link(
        app_logo(),
        href="/",
        underline="none",
        # keep the ambient colors, so linking does not change the logo's looks
        style=rx.Style(color="inherit"),
    )


def nav_bar() -> rx.Component:
    """Return a navigation bar component."""
    nav_items_section = rx.cond(
        State.nav_items_translated,
        rx.hstack(
            rx.foreach(State.nav_items_translated, nav_link),
            justify="start",
            spacing="4",
        ),
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
                app_logo_link(),
                nav_items_section,
                rx.spacer(),
                rx.hstack(
                    language_switcher(),
                    user_menu(),
                    style=rx.Style(alignItems="center"),
                    spacing="7",
                ),
                justify="between",
                align_items="center",
                # the gaps next to the spacer collapse into it, so this only
                # separates the logo from the nav items, matching the spacing
                # between the language switcher and the user menu
                spacing="7",
            ),
            size="2",
            custom_attrs={"data-testid": "nav-bar"},
            style=rx.Style(
                {
                    **NAV_BAR_PALETTE,
                    # radix paints the card surface on a ::before pseudo element
                    "--card-background-color": "var(--nav-bar-bg)",
                    "color": "var(--nav-bar-fg)",
                    "width": "100%",
                    "marginTop": "calc(-1 * var(--base-card-border-width))",
                }
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


def page(*children: rx.Component) -> rx.Component:
    """Return a page fragment with navigation bar and given children.

    Args:
        *children: Components to render in the page body
    """
    page_content = [
        nav_bar(),
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
        State.user,
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

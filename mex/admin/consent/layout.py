import reflex as rx

from mex.admin.layout import page as shared_page


def consent_logo() -> rx.Component:
    """Return the consent logo with icon and label."""
    return rx.hstack(
        rx.icon("shield-check", size=28),
        rx.heading(
            "MEx Consent",
            weight="medium",
            style=rx.Style(userSelect="none"),
        ),
        custom_attrs={"data-testid": "app-logo"},
    )


def page(*children: rx.Component) -> rx.Component:
    """Return a page fragment with the consent navigation bar and given children."""
    return shared_page(
        *children,
        user_type="user_ldap",
        nav_items_source=[],
        logo_factory=consent_logo,
    )

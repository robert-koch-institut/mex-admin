import reflex as rx

from mex.admin.consent.consent_category_list import ConsentCategoryList
from mex.admin.consent.layout import page
from mex.admin.consent.state import ConsentState
from mex.admin.state import State


def user_data() -> rx.Component:
    """Render the user data section with name and email."""
    return rx.cond(
        ConsentState.merged_login_person,
        rx.hstack(
            rx.icon(
                "circle-user",
                size=64,
                style=rx.Style(color="var(--accent-10)"),
            ),
            rx.vstack(
                rx.text(
                    ConsentState.merged_login_person.full_name,  # type: ignore  [union-attr]
                    style=rx.Style(
                        fontWeight="var(--font-weight-bold)",
                        fontSize="var(--font-size-6)",
                    ),
                ),
                rx.text(
                    ConsentState.merged_login_person.email,  # type: ignore [union-attr]
                    style=rx.Style(
                        color="var(--gray-12)",
                    ),
                ),
                rx.text(
                    ConsentState.merged_login_person.orcid_id,  # type: ignore [union-attr]
                    style=rx.Style(
                        color="var(--gray-12)",
                    ),
                ),
                spacing="0",
            ),
            align="center",
            spacing="4",
            style=rx.Style(
                marginBottom="var(--space-4)",
            ),
            custom_attrs={"data-testid": "user-data"},
        ),
        rx.text(
            ConsentState.label_user_data_loading,
            custom_attrs={"data-testid": "user-data"},
        ),
    )


def consent_box() -> rx.Component:
    """Render the consent box with text and buttons."""
    return rx.card(
        rx.vstack(
            rx.markdown(ConsentState.consent_md),
            consent_status(),
            rx.hstack(
                rx.button(
                    ConsentState.label_consent_box_consent_button,
                    on_click=ConsentState.submit_rule_set("consent"),  # type: ignore[operator]
                    disabled=ConsentState.is_consent_valid_for_processing,
                    custom_attrs={"data-testid": "accept-consent-button"},
                ),
                rx.spacer(),
                rx.button(
                    ConsentState.label_consent_box_no_consent_button,
                    on_click=ConsentState.submit_rule_set("denial"),  # type: ignore[operator]
                    disabled=ConsentState.consent_status.bool(),  # type: ignore[union-attr]
                    custom_attrs={"data-testid": "denial-consent-button"},
                ),
                style=rx.Style(padding="var(--space-4) 0"),
            ),
            rx.cond(
                ConsentState.is_consent_valid_for_processing,
                rx.text(
                    ConsentState.label_consent_retraction_denial,
                    style=rx.Style(
                        color="var(--gray-11)",
                    ),
                    custom_attrs={"data-testid": "consent-change-blocked-info"},
                ),
            ),
            style=rx.Style(
                display="flex",
                width="100%",
            ),
        ),
        style=rx.Style(
            backgroundColor="var(--accent-3)",
            padding="var(--space-4)",
        ),
        custom_attrs={"data-testid": "consent-box"},
    )


def consent_status() -> rx.Component:
    """Render the current consent status for the user."""
    return rx.hstack(
        rx.text(f"{ConsentState.merged_login_person.full_name}:"),  # type: ignore[union-attr]
        rx.cond(
            ConsentState.consent_status,
            rx.cond(
                ConsentState.is_consent_valid_for_processing,
                rx.text(
                    ConsentState.label_consent_status_consented_format,
                    color_scheme="jade",
                ),
                rx.text(
                    ConsentState.label_consent_status_declined_format,
                    color_scheme="tomato",
                ),
            ),
            rx.text(
                ConsentState.label_consent_status_no_consent,
                color_scheme="gray",
            ),
        ),
        custom_attrs={"data-testid": "consent-status"},
    )


def index() -> rx.Component:
    """Return the index for the merge and extracted search component."""
    return page(
        rx.vstack(
            user_data(),
            ConsentCategoryList.create("projects", State.merged_login_person),
            ConsentCategoryList.create("resources", State.merged_login_person),
            ConsentCategoryList.create("publications", State.merged_login_person),
            rx.spacer(direction="column"),
            rx.box(
                consent_box(),
                style=rx.Style(
                    justifyContent="center",
                    display="flex",
                    width="100%",
                ),
            ),
            style=rx.Style(
                width="100%",
                align="center",
                justify="center",
                flexGrow="1",
            ),
            custom_attrs={"data-testid": "consent-index"},
        ),
    )

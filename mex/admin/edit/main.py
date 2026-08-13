import reflex as rx

from mex.admin.components import render_value
from mex.admin.edit.state import EditState
from mex.admin.layout import page
from mex.admin.rules.main import (
    editor_field,
    rule_page_header,
    submit_button,
    validation_errors,
)
from mex.admin.rules.models import PublishTarget
from mex.admin.rules.state import RuleState
from mex.admin.search_results_component import (
    SearchResultsListItemOptions,
    SearchResultsListOptions,
    search_results_list,
)
from mex.admin.state import State
from mex.admin.style_helper import flex1_col_style, flex3_style


def edit_title() -> rx.Component:
    """Return the title for the edit page."""
    return rx.heading(
        rx.hstack(
            rx.foreach(
                EditState.item_title,
                render_value,
            ),
            style=rx.Style(
                flexWrap="nowrap",
                whiteSpace="nowrap",
                width="max-content",
            ),
        ),
        custom_attrs={"data-testid": "edit-heading"},
        style=rx.Style(userSelect="none"),
    )


def render_publish_target_switch(item: PublishTarget) -> rx.Component:
    """Render a publish target as switch and label."""
    return rx.center(
        rx.text(item.label.title(), style={"margin-right": ".5em"}),
        rx.switch(
            checked=item.enabled,
            on_change=EditState.toggle_publish_target(item.identifier),  # type: ignore[operator]
        ),
        custom_attrs={"data-testid": f"publish-target-{item.identifier}"},
    )


def render_publish_target() -> rx.Component:
    """Render switches to turn on/off publish targets, for users with write access."""
    return rx.cond(
        State.has_write_access,
        rx.card(
            rx.hstack(
                rx.text.strong(EditState.label_publish_targets),
                rx.foreach(EditState.publish_targets, render_publish_target_switch),
                align="center",
                height="100%",
                custom_attrs={"data-testid": "publish-targets"},
            ),
            style=rx.Style(
                padding="var(--space-1) var(--space-4)",
                margin="var(--line-height-1) 0",
            ),
        ),
    )


def delete_reset_button() -> rx.Component:
    """Render a button to show the delete or reset rules dialog."""
    return rx.cond(
        State.has_write_access & (EditState.delete_reset_mode != None),  # noqa: E711
        rx.alert_dialog.root(
            rx.alert_dialog.trigger(
                rx.button(
                    rx.cond(EditState.is_deleting, rx.spinner()),
                    rx.match(
                        EditState.delete_reset_mode,
                        ("reset", EditState.label_reset_rules_button),
                        ("delete", EditState.label_delete_rules_button),
                        "",
                    ),
                    disabled=EditState.is_deleting,
                    size="3",
                    color_scheme="tomato",
                    variant="outline",
                    style=rx.Style(margin="var(--line-height-1) 0"),
                ),
                custom_attrs={"data-testid": "delete-reset-dialog-button"},
            ),
            rx.alert_dialog.content(
                rx.alert_dialog.title(
                    rx.match(
                        EditState.delete_reset_mode,
                        ("reset", EditState.label_reset_rules_dialog_title),
                        ("delete", EditState.label_delete_rules_dialog_title),
                        "",
                    ),
                ),
                rx.alert_dialog.description(
                    rx.match(
                        EditState.delete_reset_mode,
                        ("reset", EditState.label_reset_rules_dialog_description),
                        ("delete", EditState.label_delete_rules_dialog_description),
                        "",
                    ),
                    size="2",
                ),
                rx.flex(
                    rx.alert_dialog.cancel(
                        rx.flex(
                            rx.button(
                                EditState.label_delete_reset_dialog_cancel_button,
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        custom_attrs={"data-testid": "delete-reset-cancel-button"},
                    ),
                    rx.alert_dialog.action(
                        rx.button(
                            rx.match(
                                EditState.delete_reset_mode,
                                (
                                    "reset",
                                    EditState.label_reset_rules_dialog_confirm_button,
                                ),
                                (
                                    "delete",
                                    EditState.label_delete_rules_dialog_confirm_button,
                                ),
                                "",
                            ),
                            color_scheme="tomato",
                            variant="solid",
                            on_click=EditState.delete_reset,
                            custom_attrs={"data-testid": "delete-reset-button"},
                        ),
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                ),
                style=rx.Style(max_width=450),
            ),
        ),
    )


def discard_changes_button() -> rx.Component:
    """Render a button to show discard changes dialog."""
    return rx.cond(
        State.has_write_access & EditState.has_changes,
        rx.alert_dialog.root(
            rx.alert_dialog.trigger(
                rx.button(
                    EditState.label_discard_changes_button,
                    size="3",
                    color_scheme="tomato",
                    variant="surface",
                    style=rx.Style(margin="var(--line-height-1) 0"),
                ),
                custom_attrs={"data-testid": "discard-changes-dialog-button"},
            ),
            rx.alert_dialog.content(
                rx.alert_dialog.title(EditState.label_discard_changes_dialog_title),
                rx.alert_dialog.description(
                    EditState.label_discard_changes_dialog_description,
                    size="2",
                ),
                rx.flex(
                    rx.alert_dialog.cancel(
                        rx.flex(
                            rx.button(
                                EditState.label_discard_changes_dialog_cancel_button,
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        custom_attrs={"data-testid": "discard-changes-cancel-button"},
                    ),
                    rx.alert_dialog.action(
                        rx.button(
                            EditState.label_discard_changes_dialog_discard_button,
                            color_scheme="tomato",
                            variant="solid",
                            on_click=[
                                RuleState.delete_local_state,
                                RuleState.refresh,
                                RuleState.resolve_identifiers,
                            ],
                            custom_attrs={"data-testid": "discard-changes-button"},
                        ),
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                ),
                style=rx.Style(max_width=450),
            ),
        ),
    )


def superseding_by_backward_card() -> rx.Component:
    """Render a card to show superseding items."""
    return rx.hstack(
        rx.card(
            rx.text(EditState.label_field_superseded_by_label),
            style=flex1_col_style,
            custom_attrs={"data-testid": "field-supersededBy-backward-name"},
            title=EditState.label_field_superseded_by_description,
        ),
        rx.card(
            rx.cond(
                EditState.is_loading_superseded_by_backward,
                rx.spinner(),
                rx.cond(
                    EditState.superseded_by_backward,
                    search_results_list(
                        EditState.superseded_by_backward,
                        SearchResultsListOptions(
                            item_options=SearchResultsListItemOptions(
                                enable_title_href=True
                            )
                        ),
                    ),
                    rx.text(EditState.label_field_superseded_by_empty),
                ),
            ),
            style=flex3_style,
        ),
        custom_attrs={"data-testid": "field-supersededBy-backward"},
    )


def loading_spinner() -> rx.Component:
    """Render a spinner while the item is being loaded."""
    return rx.center(
        rx.spinner(size="3"),
        custom_attrs={"data-testid": "edit-loading"},
        style=rx.Style(
            flex="1",
            marginTop="var(--space-6)",
            width="100%",
        ),
    )


def load_error_message() -> rx.Component:
    """Render why the item could not be loaded, instead of an unusable editor."""
    return rx.center(
        rx.heading(
            rx.match(
                RuleState.load_error,
                ("not_found", EditState.label_load_error_not_found),
                ("backend", EditState.label_load_error_backend),
                EditState.label_load_error_backend,
            ),
            size="6",
            align="center",
        ),
        custom_attrs={"data-testid": "edit-load-error"},
        style=rx.Style(
            flex="1",
            minHeight="60vh",
            width="100%",
        ),
    )


def editor() -> rx.Component:
    """Render the editor for a successfully loaded item."""
    return rx.vstack(
        rule_page_header(
            edit_title(),
        ),
        rx.hstack(
            rx.spacer(),
            render_publish_target(),
            delete_reset_button(),
            discard_changes_button(),
            submit_button(),
            align="stretch",
            justify="start",
        ),
        rx.foreach(
            RuleState.translated_fields,
            editor_field,
        ),
        superseding_by_backward_card(),
        validation_errors(),
        align="stretch",
        style=rx.Style(
            flex="1",
            marginTop="calc(2 * var(--space-6))",
            overflow="auto",
        ),
    )


def index() -> rx.Component:
    """Return the index for the edit component."""
    return page(
        rx.cond(
            RuleState.is_loading,
            loading_spinner(),
            rx.cond(
                RuleState.load_error != None,  # noqa: E711
                load_error_message(),
                editor(),
            ),
        ),
    )

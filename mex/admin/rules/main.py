from typing import cast

import reflex as rx

from mex.admin.components import icon_by_stem_type, render_span, render_value
from mex.admin.locale_service import LocaleService
from mex.admin.models import EditorValue
from mex.admin.rules.models import (
    EditorPrimarySource,
    FieldTranslation,
    InputConfig,
    ValidationMessage,
)
from mex.admin.rules.state import RuleState
from mex.admin.search_reference_dialog import search_reference_dialog
from mex.admin.style_helper import (
    add_component_style,
    add_flex1,
    flex1_col_style,
    flex1_style,
    flex3_style,
)

locale_service = LocaleService.get()


def editor_value_switch(
    field_name: str,
    primary_source: EditorPrimarySource,
    value: EditorValue,
    index: int,
) -> rx.Component:
    """Return a switch for toggling subtractive rules."""
    return rx.switch(
        checked=value.enabled,
        on_change=RuleState.toggle_field_value(field_name, value),  # type: ignore[operator]
        custom_attrs={
            "data-testid": f"switch-{field_name}-{primary_source.identifier}-{index}"
        },
        color_scheme=rx.cond(primary_source.enabled, "blue", "gray"),
    )


def editor_edit_button(
    field_name: str,
    primary_source: EditorPrimarySource,
    value: EditorValue,
    index: int,
) -> rx.Component:
    """Return a button for toggling editing."""
    return rx.icon_button(
        rx.cond(
            value.being_edited,
            rx.icon(
                "pencil-off",
                height="1rem",
                width="1rem",
            ),
            rx.icon(
                "pencil",
                height="1rem",
                width="1rem",
            ),
        ),
        variant="soft",
        size="1",
        on_click=[
            RuleState.toggle_field_value_editing(field_name, index),  # type: ignore[operator]
            RuleState.resolve_identifiers,
        ],
        custom_attrs={
            "data-testid": (
                f"edit-toggle-{field_name}-{primary_source.identifier}-{index}"
            )
        },
    )


def editor_static_value(
    field_name: str,
    primary_source: EditorPrimarySource,
    index: int,
    value: EditorValue,
) -> rx.Component:
    """Render a static value with an optional subtractive rule switch."""
    return rx.hstack(
        render_value(
            value,
            rx.cond(primary_source.input_config.render_textarea, False, True),  # noqa: FBT003
        ),
        rx.cond(
            primary_source.input_config.allow_subtractive,
            editor_value_switch(
                field_name,
                primary_source,
                value,
                index,
            ),
        ),
        style=flex1_style,
    )


def editor_additive_value(
    field_translation: FieldTranslation,
    primary_source: EditorPrimarySource,
    index: int,
    value: EditorValue,
) -> rx.Component:
    """Render an additive value with buttons for editing and removal."""
    field_name = field_translation.field.name
    return rx.hstack(
        rx.hstack(
            rx.cond(
                value.being_edited,
                add_flex1(
                    additive_rule_input(
                        field_translation,
                        primary_source.input_config,
                        index,
                        value,
                    )
                ),
                add_flex1(
                    render_value(
                        value,
                        rx.cond(
                            primary_source.input_config.render_textarea,
                            False,  # noqa: FBT003
                            True,  # noqa: FBT003
                        ),
                    )
                ),
            ),
            editor_edit_button(field_name, primary_source, value, index),
            style=flex1_style,
        ),
        remove_additive_button(
            field_translation,
            index,
        ),
        custom_attrs={"data-testid": f"additive-rule-{field_name}-{index}"},
        spacing="8",
        style=flex1_style,
    )


def remove_additive_button(
    field_translation: FieldTranslation,
    index: int,
) -> rx.Component:
    """Render a button to remove an additive value."""
    field_name = field_translation.field.name
    return rx.button(
        rx.icon(
            "circle-minus",
            height="1rem",
            width="1rem",
        ),
        f"{RuleState.label_additive_rule_remove_button_prefix} "
        f"{field_translation.label}",
        color_scheme="tomato",
        variant="soft",
        size="1",
        on_click=RuleState.remove_additive_value(field_name, index),  # type: ignore[operator]
        custom_attrs={
            "data-testid": f"additive-rule-{field_name}-{index}-remove-button"
        },
    )


def href_input(
    field_name: str,
    index: int,
    href: str | None,
) -> rx.Component:
    """Render an input component for editing a href attribute."""
    return rx.input(
        placeholder="URL",
        value=rx.cond(href, href, ""),
        on_change=RuleState.set_href_value(field_name, index),  # type: ignore[operator]
        style=rx.Style(
            margin="calc(-1 * var(--space-1))",
            width="100%",
        ),
        custom_attrs={"data-testid": f"additive-rule-{field_name}-{index}-href"},
    )


def text_input(
    field_name: str,
    index: int,
    text: str | None,
) -> rx.Component:
    """Render an input component for editing a text attribute."""
    return rx.input(
        placeholder="Text",
        value=rx.cond(text, text, ""),
        on_change=RuleState.set_text_value(field_name, index),  # type: ignore[operator]
        style=rx.Style(
            margin="calc(-1 * var(--space-1))",
            width="100%",
        ),
        custom_attrs={"data-testid": f"additive-rule-{field_name}-{index}-text"},
    )


def textarea_input(
    field_name: str,
    index: int,
    text: str | None,
) -> rx.Component:
    """Render a textarea component for editing a textarea attribute."""
    return rx.text_area(
        placeholder="Text",
        value=rx.cond(text, text, ""),
        on_change=RuleState.set_text_value(field_name, index),  # type: ignore[operator]
        style=rx.Style(
            margin="calc(-1 * var(--space-1))",
            width="100%",
        ),
        custom_attrs={"data-testid": f"additive-rule-{field_name}-{index}-text"},
        rows="5",
        resize="vertical",
    )


def identifier_input(
    field_translation: FieldTranslation,
    index: int,
    identifier: str | None,
) -> rx.Component:
    """Render an input component for editing identifiers."""
    field = field_translation.field
    return rx.hstack(
        rx.input(
            placeholder="Identifier",
            value=rx.cond(identifier, identifier, ""),
            on_change=RuleState.set_identifier_value(field.name, index),  # type: ignore[operator]
            style=rx.Style(
                margin="calc(-1 * var(--space-1))",
                width="100%",
            ),
            custom_attrs={
                "data-testid": f"additive-rule-{field.name}-{index}-identifier"
            },
        ),
        search_reference_dialog(
            on_identifier_selected=lambda x: RuleState.set_identifier_value(
                field_translation.field.name, index, x
            ),  # type: ignore[operator]
            reference_types=field_translation.field.value_type,
            field_label=field_translation.label,
        ),
    )


def badge_input(
    field_name: str,
    index: int,
    input_config: InputConfig,
    badge: str | None,
) -> rx.Component:
    """Render an input component for editing a badge attribute."""
    return rx.fragment(
        rx.foreach(
            input_config.badge_titles,
            render_span,
        ),
        rx.box(
            rx.select(
                input_config.badge_options,
                value=rx.cond(
                    badge,
                    badge,
                    rx.cond(input_config.badge_default, input_config.badge_default, ""),
                ),
                size="1",
                variant="soft",
                radius="medium",
                color_scheme="gray",
                on_change=RuleState.set_badge_value(field_name, index),  # type: ignore[operator]
                custom_attrs={
                    "data-testid": f"additive-rule-{field_name}-{index}-badge"
                },
            ),
        ),
    )


def additive_rule_input(
    field_translation: FieldTranslation,
    input_config: InputConfig,
    index: int,
    value: EditorValue,
) -> rx.Component:
    """Return an input mask for additive rules."""
    field = field_translation.field
    return rx.hstack(
        rx.cond(
            input_config.editable_href,
            add_flex1(href_input(field.name, index, value.href)),
        ),
        rx.cond(
            input_config.editable_text,
            rx.cond(
                input_config.render_textarea,
                add_flex1(textarea_input(field.name, index, value.text)),
                add_flex1(text_input(field.name, index, value.text)),
            ),
        ),
        rx.cond(
            input_config.editable_identifier,
            add_flex1(identifier_input(field_translation, index, value.identifier)),
        ),
        rx.cond(
            input_config.editable_badge,
            add_flex1(badge_input(field.name, index, input_config, value.badge)),
        ),
    )


def editor_value_card(
    field_translation: FieldTranslation,
    primary_source: EditorPrimarySource,
    index: int,
    value: EditorValue,
) -> rx.Component:
    """Return a card containing a single editor value."""
    field_name = field_translation.field.name
    return rx.card(
        rx.cond(
            primary_source.input_config.allow_additive,
            editor_additive_value(
                field_translation,
                primary_source,
                index,
                value,
            ),
            editor_static_value(
                field_name,
                primary_source,
                index,
                value,
            ),
        ),
        background=rx.cond(
            primary_source.enabled & value.enabled, "inherit", "var(--gray-a4)"
        ),
        custom_attrs={
            "data-testid": f"value-{field_name}-{primary_source.identifier}-{index}"
        },
    )


def primary_source_switch(
    field_name: str,
    primary_source: EditorPrimarySource,
) -> rx.Component:
    """Return a switch for toggling preventive rules."""
    return rx.switch(
        checked=primary_source.enabled,
        on_change=RuleState.toggle_primary_source(
            field_name,
            primary_source.name.href,
        ),  # type: ignore[operator]
        custom_attrs={
            "data-testid": f"switch-{field_name}-{primary_source.identifier}"
        },
        color_scheme="blue",
    )


def primary_source_name(
    field_name: str,
    primary_source: EditorPrimarySource,
) -> rx.Component:
    """Return the name of a primary source as a card with a preventive rule toggle."""
    return rx.card(
        rx.hstack(
            add_flex1(render_value(primary_source.name)),
            rx.spacer(),
            rx.cond(
                ~cast("rx.vars.BooleanVar", primary_source.input_config.allow_additive)
                & (primary_source.input_config.allow_preventive),
                primary_source_switch(
                    field_name,
                    primary_source,
                ),
            ),
        ),
        background=rx.cond(primary_source.enabled, "inherit", "var(--gray-a4)"),
        custom_attrs={
            "data-testid": (
                f"primary-source-{field_name}-{primary_source.identifier}-name"
            )
        },
    )


def new_additive_button(
    field_translation: FieldTranslation,
    primary_source_identifier: str,
) -> rx.Component:
    """Render a button for adding new additive rules to a given field."""
    field_name = field_translation.field.name
    return rx.card(
        rx.button(
            rx.icon(
                "circle-plus",
                height="1rem",
                width="1rem",
            ),
            f"{RuleState.label_additive_rule_add_button_prefix} "
            f"{field_translation.label}",
            color_scheme="jade",
            variant="soft",
            size="1",
            on_click=RuleState.add_additive_value(field_name),  # type: ignore[operator]
            custom_attrs={
                "data-testid": f"new-additive-{field_name}-{primary_source_identifier}"
            },
        ),
    )


def editor_primary_source_stack(
    field_translation: FieldTranslation,
    primary_source: EditorPrimarySource,
) -> rx.Component:
    """Render a stack of editor value cards and input elements for a primary source."""
    return rx.vstack(
        rx.foreach(
            primary_source.editor_values,
            lambda value, index: editor_value_card(
                field_translation,
                primary_source,
                index,
                value,
            ),
        ),
        rx.cond(
            primary_source.input_config.allow_additive,
            new_additive_button(
                field_translation,
                primary_source.identifier,
            ),
        ),
        align="stretch",
    )


def editor_primary_source(
    field_translation: FieldTranslation,
    primary_source: EditorPrimarySource,
) -> rx.Component:
    """Return a horizontal grid of cards for editing one primary source."""
    field_name = field_translation.field.name
    return rx.hstack(
        add_component_style(
            primary_source_name(
                field_name,
                primary_source,
            ),
            flex1_col_style,
        ),
        add_component_style(
            editor_primary_source_stack(field_translation, primary_source),
            flex3_style,
        ),
        custom_attrs={
            "data-testid": f"primary-source-{field_name}-{primary_source.identifier}",
        },
    )


def field_name_card(
    field_translation: FieldTranslation,
) -> rx.Component:
    """Return a card with a field name."""
    field = field_translation.field
    return rx.card(
        rx.hstack(
            rx.text(field_translation.label),
            rx.cond(
                field.is_required,
                rx.text("*", style=rx.Style(color="tomato")),
            ),
            spacing="1",
        ),
        title=field_translation.description,
        custom_attrs={"data-testid": f"field-{field.name}-name"},
    )


def editor_field(field_translation: FieldTranslation) -> rx.Component:
    """Return a horizontal grid of cards for editing one field."""
    field = field_translation.field
    return rx.hstack(
        add_component_style(field_name_card(field_translation), flex1_col_style),
        rx.vstack(
            rx.foreach(
                field.primary_sources,
                lambda primary_source: editor_primary_source(
                    field_translation, primary_source
                ),
            ),
            align="stretch",
            style=flex3_style,
        ),
        style=rx.Style(margin="var(--space-3) 0"),
        custom_attrs={"data-testid": f"field-{field.name}"},
        role="row",
    )


def validation_message(error: ValidationMessage) -> rx.Component:
    """Render a single validation error message."""
    return rx.data_list.item(
        rx.data_list.label(error.field_name),
        rx.data_list.value(
            render_span(error.message),
            render_span(" (Input: "),
            rx.code(error.input),
            render_span(")"),
            style=rx.Style(display="inline"),
        ),
    )


def validation_errors() -> rx.Component:
    """Return an overlay showing validation errors."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(RuleState.label_validation_result_dialog_title),
            rx.alert_dialog.description(
                rx.card(
                    rx.data_list.root(
                        rx.foreach(RuleState.validation_messages, validation_message),
                        orientation="vertical",
                    ),
                ),
            ),
            rx.alert_dialog.action(
                rx.button(
                    RuleState.label_validation_result_dialog_close_button,
                    on_click=RuleState.clear_validation_messages,
                    style=rx.Style(margin="var(--line-height-1) 0"),
                    custom_attrs={"data-testid": "close-validation-errors-button"},
                ),
                style=rx.Style(justifyContent="flex-end"),
            ),
        ),
        open=cast(
            "rx.vars.ArrayVar[list[ValidationMessage]]", RuleState.validation_messages
        ).bool(),
    )


def submit_button() -> rx.Component:
    """Render a submit button to save the rule set."""
    return rx.button(
        rx.cond(
            RuleState.is_submitting,
            rx.spinner(RuleState.label_save_button_saving_format),
            rx.text(RuleState.label_save_button_format),
        ),
        size="3",
        color_scheme="jade",
        on_click=[
            RuleState.set_is_submitting(value=True),  # type: ignore[operator]
            RuleState.submit_rule_set,
            RuleState.resolve_identifiers,
            RuleState.set_is_submitting(value=False),  # type: ignore[operator]
        ],
        disabled=RuleState.is_submitting,
        style=rx.Style(margin="var(--line-height-1) 0"),
        custom_attrs={"data-testid": "submit-button"},
    )


def rule_page_header(title: rx.Component) -> rx.Component:
    """Wrap the given title in a header component with a save button."""
    return rx.hstack(
        icon_by_stem_type(
            RuleState.stem_type,
            size=32,
            style=rx.Style(margin="auto 0"),
        ),
        title,
        style=rx.Style(
            alignItems="baseline",
            backdropFilter="var(--backdrop-filter-panel)",
            marginTop="calc(-1 * var(--space-1))",
            maxHeight="6rem",
            maxWidth="calc(var(--app-max-width) - var(--space-6) * 2)",
            overflow="hidden",
            padding="var(--space-4) 0",
            position="fixed",
            top="calc(var(--space-6) * 3)",
            width="100%",
            zIndex="999",
        ),
    )

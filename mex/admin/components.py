from typing import Any

import reflex as rx

from mex.admin.models import EditorValue
from mex.admin.state import State


def render_value(
    value: EditorValue,
    truncate_text: bool | rx.Var[bool] = True,  # noqa: FBT001, FBT002
) -> rx.Component:
    """Render a single editor value."""
    return rx.hstack(
        rx.cond(
            value.href,
            render_link(value),
            render_text(value, truncate_text),
        ),
        rx.cond(
            value.badge,
            render_badge(value.badge),
        ),
        spacing="1",
        style=rx.Style(max_width="100%"),
    )


def render_title(title: EditorValue) -> rx.Component:
    """Render one title in a container with hidden overflow."""
    return rx.box(
        render_value(title),
        style=rx.Style(
            fontWeight="var(--font-weight-bold)",
            overflow="hidden",
            whiteSpace="nowrap",
        ),
    )


def render_additional_titles(titles: list[EditorValue]) -> rx.Component:
    """Render one title and if necessary a badge with tooltip and additional titles."""
    return rx.cond(
        titles,
        rx.hover_card.root(
            rx.hover_card.trigger(
                rx.badge(
                    State.label_additional_titles,
                    style=rx.Style(margin="auto 0", cursor="default"),
                    custom_attrs={"data-testid": "additional-titles-badge"},
                ),
                custom_attrs={"data-testid": "tooltip-additional-titles-trigger"},
            ),
            rx.hover_card.content(
                rx.foreach(titles, render_value),
                custom_attrs={"data-testid": "tooltip-additional-titles"},
            ),
        ),
    )


def render_search_preview(values: list[EditorValue]) -> rx.Component:
    """Render a horizontal stack of editor values for a search preview."""
    return rx.hstack(
        rx.foreach(
            values,
            render_value,
        ),
        style=rx.Style(
            color="var(--gray-12)",
            fontWeight="var(--font-weight-light)",
            whiteSpace="nowrap",
            overflow="hidden",
            textOverflow="ellipsis",
            maxWidth="100%",
        ),
    )


def render_identifier(value: EditorValue) -> rx.Component:
    """Render an editor value as a clickable internal link that loads the edit page."""
    return rx.skeleton(
        rx.link(
            rx.cond(value.text, value.text, ""),
            href=rx.cond(value.href, value.href, ""),
            high_contrast=True,
            role="link",
            class_name="truncate",
            title=rx.cond(value.text, value.text, ""),
        ),
        min_width="16ch",
        min_height="1lh",
        loading=rx.cond(value.text, False, True),  # noqa: FBT003
    )


def render_external_link(value: EditorValue) -> rx.Component:
    """Render an editor value as a clickable external link that opens in a new tab."""
    return rx.link(
        rx.cond(
            value.text,
            value.text,
            rx.cond(value.href, value.href, ""),
        ),
        href=rx.cond(value.href, value.href, ""),
        high_contrast=True,
        is_external=True,
        title=rx.cond(value.text, value.text, ""),
        class_name="truncate",
        role="link",
    )


def render_link(value: EditorValue) -> rx.Component:
    """Render an editor value as an internal or external link."""
    return rx.cond(
        value.identifier,
        render_identifier(value),
        render_external_link(value),
    )


def render_span(
    text: str | None,
    truncate_text: bool | rx.Var[bool] = True,  # noqa: FBT001, FBT002
) -> rx.Component:
    """Render a generic span with the given text."""
    return rx.text(
        rx.cond(text, text, ""),
        as_="span",
        class_name=rx.cond(truncate_text, "truncate", ""),
        title=rx.cond(text, text, ""),
    )


def render_text(
    value: EditorValue,
    truncate_text: bool | rx.Var[bool] = True,  # noqa: FBT001, FBT002
) -> rx.Component:
    """Render an editor value as a text span."""
    return rx.skeleton(
        render_span(value.text, truncate_text),
        min_width="16ch",
        min_height="1lh",
        loading=rx.cond(value.text, False, True),  # noqa: FBT003
    )


def render_badge(text: str | None) -> rx.Component:
    """Render a generic badge with the given text."""
    return rx.badge(
        text,
        radius="medium",
        variant="soft",
        color_scheme="gray",
        style=rx.Style(margin="auto 0"),
    )


def icon_by_stem_type(
    stem_type: str | None = None,
    size: int | None = None,
    style: rx.Style | None = None,
) -> rx.Component | rx.Var[Any]:
    """Render an icon for the given stem type."""
    # Sigh, https://reflex.dev/docs/library/data-display/icon#using-dynamic-icon-tags
    return rx.match(
        stem_type,
        (
            "AccessPlatform",
            rx.icon("app_window", size=size, style=style, title=stem_type),
        ),
        (
            "Activity",
            rx.icon("circle_gauge", size=size, style=style, title=stem_type),
        ),
        (
            "BibliographicResource",
            rx.icon("book_marked", size=size, style=style, title=stem_type),
        ),
        (
            "Consent",
            rx.icon("badge_check", size=size, style=style, title=stem_type),
        ),
        (
            "ContactPoint",
            rx.icon("inbox", size=size, style=style, title=stem_type),
        ),
        (
            "Distribution",
            rx.icon("container", size=size, style=style, title=stem_type),
        ),
        (
            "Organization",
            rx.icon("building", size=size, style=style, title=stem_type),
        ),
        (
            "OrganizationalUnit",
            rx.icon("door_open", size=size, style=style, title=stem_type),
        ),
        (
            "Person",
            rx.icon("circle_user_round", size=size, style=style, title=stem_type),
        ),
        (
            "PrimarySource",
            rx.icon("hard_drive", size=size, style=style, title=stem_type),
        ),
        (
            "Resource",
            rx.icon("archive", size=size, style=style, title=stem_type),
        ),
        (
            "Variable",
            rx.icon("box", size=size, style=style, title=stem_type),
        ),
        (
            "VariableGroup",
            rx.icon("boxes", size=size, style=style, title=stem_type),
        ),
        rx.icon("file_question", size=size, style=style),
    )

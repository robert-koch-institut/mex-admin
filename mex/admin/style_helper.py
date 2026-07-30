from typing import Any

import reflex as rx

flex1_style = rx.Style(flex="1", min_height="0", min_width="0")
flex3_style = rx.Style(flex="3", min_height="0", min_width="0")


flex1_col_style = flex1_style | {"max_width": "25%"}


def add_component_style(
    component: rx.Component, style: rx.Style | dict[str, Any]
) -> rx.Component:
    """Add specified style to given component and returns the styled component.

    If the component already has a style the styles are merged, where the given `style`
    arg will override existing keys.
    """
    component.style = rx.Style(component.style | style)
    return component


def add_flex1(component: rx.Component) -> rx.Component:
    """Add flex1 style to the given component and returns it."""
    return add_component_style(component, flex1_style)

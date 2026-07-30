from collections.abc import Sequence
from typing import Any

import reflex as rx
from pydantic import BaseModel
from reflex.components import Component
from reflex.components.radix.themes.components.select import (
    HighLevelSelect,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectRoot,
    SelectTrigger,
)
from reflex.vars.base import Var


class ValueLabelSelectItem(BaseModel):
    """Items for ValueLabelHighLevelSelect that contain value and label."""

    value: str
    label: str


class ValueLabelHighLevelSelect(HighLevelSelect):
    """High level wrapper for the Select component."""

    @classmethod
    def create_value_label_select(
        cls,
        items: Sequence[ValueLabelSelectItem] | Var[Sequence[ValueLabelSelectItem]],
        **props: Any,  # noqa: ANN401
    ) -> Component:
        """Create a select component. THIS IS COPY PASTE FROM HighLevelSelect!

        Args:
            items: The items (with "label" and "value") of the select.
            **props: Additional properties to apply to the select component.

        Returns:
            The select component.
        """
        trigger_prop_list = [
            "id",
            "placeholder",
            "variant",
            "radius",
            "width",
            "flex_shrink",
            "custom_attrs",
        ]

        content_props = {
            prop: props.pop(prop)
            for prop in ["high_contrast", "position"]
            if prop in props
        }

        trigger_props = {
            prop: props.pop(prop) for prop in trigger_prop_list if prop in props
        }

        color_scheme = props.pop("color_scheme", None)

        if color_scheme is not None:
            content_props["color_scheme"] = color_scheme
            trigger_props["color_scheme"] = color_scheme

        item_testid_prefix = props.pop("item_testid_prefix", "")
        label = props.pop("label", None)

        def _render_item(item: ValueLabelSelectItem, item_index: int) -> rx.Component:
            return SelectItem.create(
                item.label,
                value=item.value,
                custom_attrs={
                    "data-testid": f"{item_testid_prefix}value-label-select-item-{item_index}-{item.value}"  # noqa: E501
                },
            )

        child: list[Any] = []
        if isinstance(items, Var):
            child = [
                rx.foreach(
                    items,
                    _render_item,
                )
            ]
        else:
            child = [
                _render_item(item, item_index) for item_index, item in enumerate(items)
            ]

        return SelectRoot.create(
            SelectTrigger.create(
                **trigger_props,
            ),
            SelectContent.create(
                SelectGroup.create(
                    SelectLabel.create(label) if label is not None else "",
                    *child,
                ),
                **content_props,
            ),
            **props,
        )


value_label_select = ValueLabelHighLevelSelect.create_value_label_select

import json
import time
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Any

import reflex as rx
from pydantic import BaseModel
from reflex.event import EventSpec
from requests import HTTPError

from mex.admin.exceptions import escalate_error
from mex.admin.fields import STRINGIFIED_TYPES_BY_FIELD_BY_CLASS_NAME
from mex.admin.label_var import label_var
from mex.admin.models import SearchResult, ValueLabelCheckboxItem
from mex.admin.pagination_component import PaginationStateMixin
from mex.admin.state import State
from mex.admin.transform import transform_models_to_search_results
from mex.admin.utils import resolve_editor_value
from mex.admin.value_label_select import ValueLabelSelectItem
from mex.common.backend_api.connector import BackendApiConnector, ReferenceFilter
from mex.common.fields import REFERENCE_FIELDS_BY_CLASS_NAME
from mex.common.models import MERGED_MODEL_CLASSES
from mex.common.transform import ensure_prefix


@dataclass
class FieldDescriptor:
    """Model to describe a field with its name, label value types it can reference."""

    field: str
    labels: set[str]
    value_types: set[str]

    def to_json(self) -> str:
        """Serialize the FieldDescriptor to a JSON string."""
        return json.dumps(
            {
                "field": self.field,
                "labels": list(self.labels),
                "value_types": list(self.value_types),
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> FieldDescriptor:
        """Deserialize a JSON string to a FieldDescriptor."""
        data = json.loads(json_str)
        return FieldDescriptor(
            field=data["field"],
            labels=set(data["labels"]),
            value_types=set(data["value_types"]),
        )


class RefFilter(BaseModel):
    """Model to filter reference fields by values."""

    field_descriptor_json: str = ""
    field_label: str = ""
    field_value_types: list[str] = []
    values: list[str] = []


def _build_reference_filters(refs: Sequence[RefFilter]) -> list[ReferenceFilter]:
    """Build the backend reference filters for the given reference filter rows.

    Blank values are dropped, because a freshly added value row is empty and
    would otherwise be sent to the backend as an identifier to filter for.

    Args:
        refs: The reference filter rows as shown in the sidebar.

    Returns:
        Reference filters for all rows that have at least one identifier.
    """
    reference_filters = []
    for ref in refs:
        identifiers = [value for value in ref.values if value.strip()]
        if identifiers:
            reference_filters.append(
                ReferenceFilter(
                    field=FieldDescriptor.from_json(ref.field_descriptor_json).field,
                    identifiers=identifiers,
                )
            )
    return reference_filters


class AdvancedSearchState(State, PaginationStateMixin):
    """State for the advanced search page."""

    query: str = ""
    entity_types: list[str] = []
    refs: list[RefFilter] = []

    all_entity_types = [k.stemType for k in MERGED_MODEL_CLASSES]

    is_searching: bool = False
    search_duration_seconds: float = 0.0
    search_results: list[SearchResult] = []

    @rx.var
    def label_entity_types(self) -> list[ValueLabelCheckboxItem]:
        """Get entity types with value, label and checked."""
        return sorted(
            [
                ValueLabelCheckboxItem(
                    label=self._locale_service.get_ui_label(self.current_locale, key),
                    value=key,
                    checked=key in self.entity_types,
                )
                for key in self.all_entity_types
            ],
            key=lambda x: x.label,
        )

    @rx.var
    def all_fields_for_entity_types(self) -> list[ValueLabelSelectItem]:
        """Get all fields for the currently selected entity types filter.

        Returns:
            The fields for the selected entity types.
        """
        selected_entity_types = (
            self.all_entity_types if len(self.entity_types) == 0 else self.entity_types
        )

        items: dict[str, FieldDescriptor] = {}
        for entity_type in selected_entity_types:
            for field in REFERENCE_FIELDS_BY_CLASS_NAME[
                ensure_prefix(entity_type, "Extracted")
            ]:
                if field not in items:
                    items[field] = FieldDescriptor(field, set(), set())
                entry = items[field]
                entry.labels.add(
                    self._locale_service.get_field_label(
                        self.current_locale, entity_type, field
                    )
                )
                entry.value_types.update(
                    STRINGIFIED_TYPES_BY_FIELD_BY_CLASS_NAME[
                        ensure_prefix(entity_type, "Extracted")
                    ][field]
                )

        return sorted(
            [
                ValueLabelSelectItem(
                    label=" / ".join(item.labels), value=item.to_json()
                )
                for key, item in items.items()
            ],
            key=lambda x: x.label,
        )

    @rx.var
    def search_results_length(self) -> int:
        """Return the number of current search results."""
        return len(self.search_results)

    @rx.event
    def search(self) -> Generator[EventSpec | None]:
        """Perform the search with the current filters."""
        entity_type = [ensure_prefix(x, "Merged") for x in self.entity_types]
        skip = self.limit * (self.current_page - 1)
        reference_filters = _build_reference_filters(self.refs)

        self.is_searching = True
        yield None

        connector = BackendApiConnector.get()
        start_time = time.monotonic()
        try:
            fetch_result = connector.fetch_preview_items(
                query_string=self.query or None,
                entity_type=entity_type,
                reference_filters=reference_filters or None,
                skip=skip,
                limit=self.limit,
            )
        except HTTPError as exc:
            self.search_duration_seconds = time.monotonic() - start_time
            self.search_results = []
            self.total = 0
            self.current_page = 1
            yield from escalate_error(
                "backend",
                "advanced search :: error fetching preview items",
                exc.response.text,
            )
        else:
            self.search_duration_seconds = time.monotonic() - start_time
            self.search_results = transform_models_to_search_results(fetch_result.items)
            self.total = fetch_result.total

        self.is_searching = False

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for result in self.search_results:
            for preview in result.preview:
                if preview.identifier and not preview.text:
                    async with self:
                        await resolve_editor_value(preview)

    @rx.event
    def on_query_form_submit(self, form_data: dict[str, Any]) -> None:
        """Handle the submission of the query form."""
        self.query = form_data.get("query", self.query)

    @rx.event
    def toggle_entity_type(self, entity_type: str) -> None:
        """Toggle the selection of an entity type."""
        if entity_type in self.entity_types:
            self.entity_types.remove(entity_type)
        else:
            self.entity_types.append(entity_type)

    @rx.event
    def add_ref_filter(self, field_descriptor_json: str) -> None:
        """Add a reference filter.

        Args:
            field_descriptor_json:  The field (FieldDescriptor, as json serialized str)
            to filter on.
        """
        field_data = FieldDescriptor.from_json(field_descriptor_json)

        self.refs.append(
            RefFilter(
                field_descriptor_json=field_descriptor_json,
                field_label=" / ".join(field_data.labels),
                field_value_types=sorted(field_data.value_types),
                values=[],
            )
        )

    @rx.event
    def remove_ref_filter(self, index: int) -> None:
        """Remove a reference filter.

        Args:
            index: The index of ref filter to remove.
        """
        if index < len(self.refs):
            self.refs.pop(index)

    @rx.event
    def set_ref_filter_field(self, index: int, field_descriptor_json: str) -> None:
        """Set the field for a reference filter.

        Args:
            index: The index of the reference filter to update.
            field_descriptor_json: The field (FieldDescriptor, as json serialized str).
        """
        ref = self.refs[index]
        field_desc = FieldDescriptor.from_json(field_descriptor_json)

        ref.field_descriptor_json = field_descriptor_json
        ref.field_label = " / ".join(field_desc.labels)
        ref.field_value_types = sorted(field_desc.value_types)
        ref.values = []

    @rx.event
    def add_ref_filter_value(self, index: int, value: str) -> None:
        """Add a value to a reference filter.

        Args:
            index: The index of the reference filter to update.
            value: The value to add.
        """
        if index < len(self.refs):
            self.refs[index].values.append(value)

    @rx.event
    def set_ref_filter_value(self, index: int, val_index: int, value: str) -> None:
        """Set a value for a reference filter.

        Args:
            index: The index of the reference filter to update.
            val_index: The index of the value to update.
            value: The new value.
        """
        if index < len(self.refs):
            values = self.refs[index].values
            if val_index < len(values):
                values[val_index] = value

    @rx.event
    def remove_ref_filter_value(self, index: int, val_index: int) -> None:
        """Remove a value from a reference filter.

        Args:
            index: The index of the reference filter to update.
            val_index: The index of the value to remove.
        """
        self.refs[index].values.pop(val_index)

    @label_var(label_id="search.search_input.placeholder")
    def label_search_input_placeholder(self) -> None:
        """Label for search_input.placeholder."""

    @label_var(label_id="search.reference_field_filter.placeholder")
    def label_reference_field_filter_placeholder(self) -> None:
        """Label for reference_field_filter.placeholder."""

    @label_var(
        label_id="search.result_summary.format",
        deps=[
            "search_results_length",
            "total",
            "current_page",
            "limit",
            "search_duration_seconds",
        ],
    )
    def label_result_summary_format(self) -> list[float]:
        """Label for result_summary.format."""
        # the range is 1-based and inclusive, but collapses to 0-0 without results
        first_item = self.skip + 1 if self.search_results_length else 0
        return [
            first_item,
            self.skip + self.search_results_length,
            self.total,
            self.search_duration_seconds,
        ]

    @label_var(label_id="advanced_search.reference_filter.add_value")
    def label_reference_filter_add_value(self) -> None:
        """Label for reference_filter.add_value."""

    @label_var(label_id="advanced_search.reference_filter.remove_value")
    def label_reference_filter_remove_value(self) -> None:
        """Label for reference_filter.remove_value."""

    @label_var(label_id="advanced_search.reference_filter.value_placeholder")
    def label_reference_filter_value_placeholder(self) -> None:
        """Label for reference_filter.value_placeholder."""

    @label_var(label_id="advanced_search.reference_filter.title")
    def label_reference_filter_title(self) -> None:
        """Label for reference_filter.title."""

    @label_var(label_id="advanced_search.entitytype_filter.title")
    def label_entitytype_filter_title(self) -> None:
        """Label for entitytype_filter.title."""

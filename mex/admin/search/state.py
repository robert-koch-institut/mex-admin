import time
from collections.abc import Generator
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import reflex as rx
from pydantic import TypeAdapter, ValidationError
from reflex.event import EventSpec
from reflex.istate.data import RouterData
from requests import HTTPError

from mex.admin.exceptions import escalate_error
from mex.admin.label_var import label_var
from mex.admin.locale_service import LocaleService
from mex.admin.models import SearchResult, ValueLabelCheckboxItem
from mex.admin.pagination_component import PaginationStateMixin
from mex.admin.search.models import (
    ReferenceFieldFilter,
    ReferenceFieldIdentifierFilter,
    ReferenceFieldParameters,
    SearchPrimarySource,
)
from mex.admin.state import State
from mex.admin.transform import transform_models_to_search_results
from mex.admin.utils import resolve_editor_value
from mex.admin.value_label_select import ValueLabelSelectItem
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.exceptions import MExError
from mex.common.fields import REFERENCE_FIELDS_BY_CLASS_NAME
from mex.common.models import MERGED_MODEL_CLASSES, MergedPrimarySource
from mex.common.transform import ensure_prefix
from mex.common.types import Identifier


def _build_dynamic_refresh_params(
    reference_field_filter: ReferenceFieldFilter,
) -> ReferenceFieldParameters:
    identifiers = [
        x for x in reference_field_filter.identifiers if not x.validation_msg
    ]
    if not reference_field_filter.field or not identifiers:
        return {"reference_field": None, "referenced_identifier": None}
    return {
        "reference_field": reference_field_filter.field,
        "referenced_identifier": [x.value for x in identifiers],
    }


def _build_had_primary_source_refresh_params(
    had_primary_sources: dict[str, SearchPrimarySource],
) -> ReferenceFieldParameters:
    had_primary_source = [
        identifier
        for identifier, primary_source in had_primary_sources.items()
        if primary_source.checked
    ]
    return {
        "reference_field": "hadPrimarySource" if had_primary_source else None,
        "referenced_identifier": had_primary_source,
    }


class SearchState(State, PaginationStateMixin):
    """State management for the search page."""

    results: list[SearchResult] = []
    query_string: str = ""
    entity_types: dict[str, bool] = {k.stemType: False for k in MERGED_MODEL_CLASSES}

    reference_filter_strategy: Literal["had_primary_source", "dynamic"] = "dynamic"
    had_primary_sources: dict[str, SearchPrimarySource] = {}
    reference_field_filter: ReferenceFieldFilter = ReferenceFieldFilter(
        field="", identifiers=[]
    )
    is_loading: bool = True
    search_duration_seconds: float = 0.0
    _locale_service = LocaleService.get()

    @rx.var
    def label_entity_types(self) -> list[ValueLabelCheckboxItem]:
        """Get entity types with value, label and checked."""
        return sorted(
            [
                ValueLabelCheckboxItem(
                    label=self._locale_service.get_ui_label(self.current_locale, key),
                    value=key,
                    checked=self.entity_types[key],
                )
                for key in self.entity_types
            ],
            key=lambda x: x.label,
        )

    @rx.event
    def set_reference_filter_field(self, value: str) -> None:
        """Set the reference filter field used to filter references.

        Args:
            value (str): The field to use for reference filtering.
        """
        self.reference_field_filter.field = value

    @rx.event
    def set_reference_filter_strategy(
        self, value: Literal["had_primary_source", "dynamic"]
    ) -> None:
        """Set the reference filter strategy to define the filter mechanism.

        Args:
            value: The strategy used for filtering.
        """
        self.reference_filter_strategy = value

    @rx.event
    def set_reference_field_filter_identifier(self, index: int, value: str) -> None:
        """Set the reference value to filter for at a specific index.

        Args:
            index (int): Index of the identifier
            value (str): Value of the identifier
        """
        self.reference_field_filter.identifiers[index].validation_msg = None
        self.reference_field_filter.identifiers[index].value = value
        try:
            TypeAdapter(Identifier).validate_python(value)
        except ValidationError as ve:
            self.reference_field_filter.identifiers[index].validation_msg = "\n".join(
                [error["msg"] for error in ve.errors()]
            )

    @rx.event
    def remove_reference_field_filter_identifier(self, index: int) -> None:
        """Remove the reference value to filter for at a specific index.

        Args:
            index: Index of the identifier to remove.
        """
        self.reference_field_filter.identifiers.pop(index)

    @rx.event
    def add_reference_field_filter_identifier(self) -> None:
        """Add a new empty identifier."""
        self.reference_field_filter.identifiers.append(
            ReferenceFieldIdentifierFilter(value="", validation_msg=None)
        )
        self.set_reference_field_filter_identifier(
            len(self.reference_field_filter.identifiers) - 1, ""
        )  # type: ignore[operator]

    @rx.var(cache=False)
    def all_fields_for_entity_types(self) -> list[ValueLabelSelectItem]:
        """Get all fields for the currently selected entity types filter.

        Returns:
            The fields for the selected entity types.
        """
        selected_entity_types = [
            item[0]
            for item in list(filter(lambda item: item[1], self.entity_types.items()))
        ]

        if len(selected_entity_types) == 0:
            selected_entity_types = [item[0] for item in self.entity_types.items()]

        fields_with_type = [
            [
                ValueLabelSelectItem(
                    value=field,
                    label=self._locale_service.get_field_label(
                        self.current_locale, entity_type, field
                    ),
                )
                for field in REFERENCE_FIELDS_BY_CLASS_NAME[
                    ensure_prefix(entity_type, "Extracted")
                ]
            ]
            for entity_type in selected_entity_types
        ]

        return sorted(
            {
                item.value: item
                for item in [f for fields in fields_with_type for f in fields]
            }.values(),
            key=lambda x: x.label,
        )

    @rx.var(cache=False)
    def current_results_length(self) -> int:
        """Return the number of current search results."""
        return len(self.results)

    @rx.event
    def load_search_params(self) -> Generator[EventSpec | None]:
        """Load url params into the state."""
        router: RouterData = self.get_value("router")
        parsed_url = urlparse(router.url)
        params = parse_qs(parsed_url.query)
        current_page = params["page"][0] if "page" in params else 1
        self.set_current_page(current_page)  # type: ignore[operator]
        yield None
        self.query_string = " ".join(params.get("q", ""))
        type_params = params.get("entityType", [])
        type_params = type_params if isinstance(type_params, list) else [type_params]
        self.entity_types = {
            k.stemType: k.stemType in type_params for k in MERGED_MODEL_CLASSES
        }
        had_primary_source_params = params.get("hadPrimarySource", [])
        had_primary_source_params = (
            had_primary_source_params
            if isinstance(had_primary_source_params, list)
            else [had_primary_source_params]
        )
        for primary_source_identifier in had_primary_source_params:
            self.had_primary_sources[primary_source_identifier].checked = True

        self.reference_filter_strategy = (
            "had_primary_source"
            if params.get("referenceFilterStrategy") == ["had_primary_source"]
            else "dynamic"
        )
        ref_field_identifiers = params.get("referenceIdentifier", [])
        ref_field_identifiers = (
            ref_field_identifiers
            if isinstance(ref_field_identifiers, list)
            else [ref_field_identifiers]
        )
        reference_field = (
            params["referenceField"][0] if "referenceField" in params else ""
        )
        self.reference_field_filter = ReferenceFieldFilter(
            field=reference_field,
            identifiers=[
                ReferenceFieldIdentifierFilter(value=x, validation_msg=None)
                for x in ref_field_identifiers
            ],
        )

    @rx.event
    def push_search_params(self) -> Generator[EventSpec | None]:
        """Push a new browser history item with updated search parameters."""
        yield self.push_url_params(
            {
                "q": self.query_string,
                "page": self.current_page,
                "entityType": [k for k, v in self.entity_types.items() if v],
                "referenceFilterStrategy": self.reference_filter_strategy,
                "hadPrimarySource": [
                    k for k, v in self.had_primary_sources.items() if v.checked
                ],
                "referenceField": self.reference_field_filter.field,
                "referenceIdentifier": [
                    x.value for x in self.reference_field_filter.identifiers
                ],
            }
        )

    @rx.event
    def set_entity_type(
        self,
        index: str,
        value: bool,  # noqa: FBT001
    ) -> None:
        """Set the entity type for filtering and refresh the results."""
        self.entity_types[index] = value

    @rx.event
    def set_had_primary_source(
        self,
        index: str,
        value: bool,  # noqa: FBT001
    ) -> None:
        """Set the entity type for filtering and refresh the results."""
        self.had_primary_sources[index].checked = value

    @rx.event
    def handle_submit(self, form_data: dict[str, Any]) -> None:
        """Handle the form submit."""
        self.query_string = form_data["query_string"]

    @rx.event
    def scroll_to_top(self) -> Generator[EventSpec]:
        """Scroll the page to the top."""
        yield rx.call_script("window.scrollTo({top: 0, behavior: 'smooth'});")

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for result in self.results:
            for preview in result.preview:
                if preview.identifier and not preview.text:
                    async with self:
                        await resolve_editor_value(preview)

    @rx.event
    def refresh(self) -> Generator[EventSpec | None]:
        """Refresh the search results."""
        # TODO(ND): use proper connector method when available (stop-gap MX-1984)
        connector = BackendApiConnector.get()
        entity_type = [
            ensure_prefix(k, "Merged") for k, v in self.entity_types.items() if v
        ]
        filter_strategy_params = (
            _build_dynamic_refresh_params(self.reference_field_filter)
            if self.reference_filter_strategy == "dynamic"
            else _build_had_primary_source_refresh_params(self.had_primary_sources)
        )

        skip = self.limit * (self.current_page - 1)
        self.is_loading = True
        yield None
        start_time = time.monotonic()
        try:
            response = connector.fetch_preview_items(
                query_string=self.query_string,
                entity_type=entity_type,
                skip=skip,
                limit=self.limit,
                **filter_strategy_params,
            )
        except HTTPError as exc:
            self.search_duration_seconds = time.monotonic() - start_time
            self.is_loading = False
            self.results = []
            yield SearchState.set_total(0)  # type: ignore[operator]
            yield SearchState.set_current_page(1)  # type: ignore[operator]
            yield from escalate_error(
                "backend", "error fetching merged items", exc.response.text
            )
        else:
            self.search_duration_seconds = time.monotonic() - start_time
            self.is_loading = False
            self.results = transform_models_to_search_results(response.items)
            yield SearchState.set_total(response.total)  # type: ignore[operator]

    @rx.event
    def get_available_primary_sources(self) -> Generator[EventSpec]:
        """Get all available primary sources."""
        # TODO(ND): use proper connector method when available (stop-gap MX-1984)
        connector = BackendApiConnector.get()
        maximum_number_of_primary_sources = 100
        try:
            primary_sources_response = connector.fetch_preview_items(
                entity_type=[ensure_prefix(MergedPrimarySource.stemType, "Merged")],
                skip=0,
                limit=maximum_number_of_primary_sources,
            )
        except HTTPError as exc:
            yield from escalate_error(
                "backend", "error fetching primary sources", exc.response.text
            )
        else:
            available_primary_sources = transform_models_to_search_results(
                primary_sources_response.items
            )
            if len(available_primary_sources) == maximum_number_of_primary_sources:
                msg = (
                    f"Cannot handle more than {maximum_number_of_primary_sources} "
                    "primary sources."
                )
                raise MExError(msg)
            search_primary_sources = [
                SearchPrimarySource(
                    identifier=source.identifier,
                    title=source.title[0].text or "",
                    checked=False,
                )
                for source in available_primary_sources
            ]
            self.had_primary_sources = {
                str(source.identifier): source
                for source in sorted(
                    search_primary_sources, key=lambda source: source.title.lower()
                )
            }

    @label_var(label_id="search.search_input.placeholder")
    def label_search_input_placeholder(self) -> None:
        """Label for search_input.placeholder."""

    @label_var(label_id="search.entitytype_filter.title")
    def label_entitytype_filter_title(self) -> None:
        """Label for entitytype_filter.title."""

    @label_var(label_id="search.reference_filter.dynamic_tab")
    def label_reference_filter_dynamic_tab(self) -> None:
        """Label for reference_filter.dynamic_tab."""

    @label_var(label_id="search.reference_filter.primarysource_tab")
    def label_reference_filter_primarysource_tab(self) -> None:
        """Label for reference_filter.primarysource_tab."""

    @label_var(
        label_id="search.result_summary.detailed_format",
        deps=[
            "current_results_length",
            "total",
            "current_page",
            "limit",
            "search_duration_seconds",
        ],
    )
    def label_result_summary_detailed_format(self) -> list[float]:
        """Label for result_summary.detailed_format."""
        # the range is 1-based and inclusive, but collapses to 0-0 without results
        first_item = self.skip + 1 if self.current_results_length else 0
        return [
            first_item,
            self.skip + self.current_results_length,
            self.total,
            self.search_duration_seconds,
        ]

    @label_var(label_id="search.reference_field_filter.placeholder")
    def label_reference_field_filter_placeholder(self) -> None:
        """Label for reference_field_filter.placeholder."""

    @label_var(label_id="search.reference_field_filter.add")
    def label_reference_field_filter_add(self) -> None:
        """Label for reference_field_filter.add."""


full_refresh = [
    SearchState.go_to_first_page,
    SearchState.push_search_params,
    SearchState.refresh,
    SearchState.resolve_identifiers,
]

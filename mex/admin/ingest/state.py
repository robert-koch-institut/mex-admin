from collections.abc import Generator
from typing import Any

import reflex as rx
from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error, response_payload
from mex.admin.ingest.models import ALL_AUX_PROVIDERS, AuxProvider, IngestResult
from mex.admin.ingest.transform import transform_models_to_results
from mex.admin.label_var import label_var
from mex.admin.pagination_component import PaginationStateMixin
from mex.admin.state import State
from mex.admin.utils import resolve_editor_value
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.models import AnyExtractedModel, PaginatedItemsContainer


class IngestState(State, PaginationStateMixin):
    """State management for the ingest page."""

    results_transformed: list[IngestResult] = []
    results_extracted: list[AnyExtractedModel] = []
    query_string: str = ""
    aux_providers: list[AuxProvider] = ALL_AUX_PROVIDERS
    current_aux_provider: AuxProvider = aux_providers[0]
    is_loading: bool = True

    @rx.var(cache=False)
    def current_results_length(self) -> int:
        """Return the number of current search results."""
        return len(self.results_transformed)

    @rx.event
    def toggle_show_all_properties(self, item: IngestResult, index: int) -> None:
        """Toggle if all properties are visible for given item at index."""
        self.results_transformed[
            index
        ].show_all_properties = not item.show_all_properties

    @rx.event
    def set_current_aux_provider(self, value: str) -> None:
        """Change the current aux provider."""
        for provider in self.aux_providers:
            if provider.key.value == value:
                self.current_aux_provider = provider
                break

    @rx.event
    def handle_submit(self, form_data: dict[str, Any]) -> None:
        """Handle the form submit."""
        self.query_string = form_data["query_string"]

    @rx.event
    def reset_query_string(self) -> None:
        """Reset the query string."""
        self.query_string = ""

    @rx.event
    def ingest_result(self, index: int) -> Generator[EventSpec]:
        """Ingest the selected result to MEx backend."""
        connector = BackendApiConnector.get()
        model = self.get_value(self.results_extracted[index])  # type: ignore[arg-type]
        try:
            # TODO(ND): use the user auth for backend requests (stop-gap MX-1616)
            connector.ingest([model])
        except RequestException as exc:
            yield from escalate_error(
                "backend", f"error ingesting {model.stemType}", response_payload(exc)
            )
        else:
            self.results_transformed[index].show_ingest_button = False
            yield rx.toast.success(
                title=self.label_toast_success_title,
                description=self.label_toast_success_message_format.format(
                    model.stemType
                ),
                class_name="editor-toast",
                close_button=True,
                dismissible=True,
                duration=5000,
            )

    @rx.event
    def scroll_to_top(self) -> Generator[EventSpec]:
        """Scroll the page to the top."""
        yield rx.call_script("window.scrollTo({top: 0, behavior: 'smooth'});")

    @rx.event
    def resolve_primary_source_titles(self) -> Generator[EventSpec]:
        """Resolve the dynamic names of the aux providers."""
        for provider in self.aux_providers:
            yield from provider.resolve_dynamic_name()

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for result in self.results_transformed:
            for value in [*result.title, *result.preview, *result.all_properties]:
                if value.identifier and not value.text:
                    async with self:
                        await resolve_editor_value(value)

    @rx.event(background=True)
    async def flag_ingested_items(self) -> None:
        """Check and flag, if any result is already ingested into backend."""
        connector = BackendApiConnector.get()
        for index, result in enumerate(self.results_transformed):
            response = connector.fetch_identities(
                identifier_in_primary_source=self.results_extracted[
                    index
                ].identifierInPrimarySource,
                had_primary_source=self.results_extracted[index].hadPrimarySource,
            )
            if len(response.items) > 0:
                async with self:
                    result.show_ingest_button = False

    @rx.event
    def refresh(self) -> Generator[EventSpec | None]:
        """Refresh the search results."""
        connector = BackendApiConnector.get()
        self.is_loading = True
        yield None
        try:
            response = connector.request(
                method="GET",
                endpoint=self.current_aux_provider.key.value,
                params={
                    "q": self.query_string or None,
                    "offset": str(self.skip),
                    "limit": str(self.limit),
                },
            )
        except RequestException as exc:
            self.is_loading = False
            self.results_transformed = []
            self.results_extracted = []
            yield IngestState.set_total(0)  # type: ignore[operator]
            yield IngestState.set_current_page(1)  # type: ignore[operator]
            yield None
            yield from escalate_error(
                "backend",
                f"error fetching {self.current_aux_provider.static_name} items",
                response_payload(exc),
            )
        else:
            self.is_loading = False
            container = PaginatedItemsContainer[AnyExtractedModel].model_validate(
                response
            )
            self.results_extracted = container.items
            self.results_transformed = transform_models_to_results(container.items)
            self.set_total(container.total)  # type: ignore[operator]

    @label_var(label_id="ingest.button_ingest")
    def label_button_ingest(self) -> None:
        """Label for button_ingest."""

    @label_var(label_id="ingest.button_ingested")
    def label_button_ingested(self) -> None:
        """Label for button_ingested."""

    @label_var(label_id="ingest.search.placeholder")
    def label_search_placeholder(self) -> None:
        """Label for search.placeholder."""

    @label_var(
        label_id="ingest.search.result_summary_format",
        deps=["current_results_length", "total"],
    )
    def label_search_result_summary_format(self) -> list[int]:
        """Label for search.result_summary_format."""
        return [self.current_results_length, self.total]

    @label_var(label_id="ingest.search_info.ldap")
    def label_search_info_ldap(self) -> None:
        """Label for search_info.ldap."""

    @label_var(label_id="ingest.search_info.wikidata")
    def label_search_info_wikidata(self) -> None:
        """Label for search_info.wikidata."""

    @label_var(label_id="ingest.toast_success.title")
    def label_toast_success_title(self) -> None:
        """Label for toast_success.title."""

    @label_var(label_id="ingest.toast_success.message_format")
    def label_toast_success_message_format(self) -> None:
        """Label for toast_success.message_format."""

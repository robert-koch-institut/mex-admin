from collections.abc import Generator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error, response_payload
from mex.admin.models import SearchResult
from mex.common.backend_api.connector import BackendApiConnector


class AuxProviderKey(StrEnum):
    """Keys for auxiliary providers."""

    LDAP = "ldap"
    ORCID = "orcid"
    WIKIDATA = "wikidata"


@dataclass
class AuxProvider:
    """Auxiliary provider with static and dynamic display names."""

    key: AuxProviderKey
    static_name: str
    dynamic_name: str

    def __str__(self) -> str:
        """Return the display name (dynamic if available, otherwise static)."""
        return self.dynamic_name or self.static_name

    def resolve_dynamic_name(self) -> Generator[EventSpec, Any, Any]:
        """Resolve the dynamic name from the backend connector."""
        connector = BackendApiConnector.get()
        try:
            response = connector.fetch_preview_items(
                query_string=self.key.value,
                entity_type=["MergedPrimarySource"],
                skip=0,
                limit=1,
            )
            if response.items:
                self.dynamic_name = str(response.items[0].title[-1].value)  # type: ignore[union-attr]
        except RequestException as exc:
            yield from escalate_error(
                "backend",
                f"error fetching title for {self.key.value}",
                response_payload(exc),
            )


ALL_AUX_PROVIDERS: list[AuxProvider] = [
    AuxProvider(AuxProviderKey.LDAP, "LDAP", "Active Directory"),
    AuxProvider(
        AuxProviderKey.ORCID,
        "ORCID",
        "Open Researcher Contributor Identification Initiative",
    ),
    AuxProvider(AuxProviderKey.WIKIDATA, "Wikidata", "Wikidata"),
]


class IngestResult(SearchResult):
    """Ingest search result."""

    show_ingest_button: bool

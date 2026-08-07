import logging
import re
from collections.abc import Generator
from re import Pattern
from typing import Any, cast
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import Page, expect
from pydantic import SecretStr
from pytest import LogCaptureFixture

from mex.admin.api.main import api
from mex.admin.locale_service import LocaleService
from mex.admin.settings import AdminSettings
from mex.admin.types import AdminUserDatabase, AdminUserPassword
from mex.common.backend_api.connector import (
    BackendApiConnector,
    LDAPBackendApiConnector,
)
from mex.common.logging import logger
from mex.common.models import (
    MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
    AnyExtractedModel,
    ExtractedActivity,
    ExtractedContactPoint,
    ExtractedOrganizationalUnit,
    ExtractedPrimarySource,
    ExtractedResource,
)
from mex.common.types import (
    AccessRestriction,
    Identifier,
    IdentityProvider,
    Link,
    MergedContactPointIdentifier,
    MergedOrganizationalUnitIdentifier,
    MergedPersonIdentifier,
    MergedPrimarySourceIdentifier,
    Text,
    TextLanguage,
    Theme,
    YearMonthDay,
)

pytest_plugins = ("mex.common.testing.plugin",)


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict[str, Any],
) -> dict[str, Any]:
    """Run the playwright test browser in a larger resolution than its default."""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1600,
            "height": 900,
        },
    }


@pytest.fixture
def client() -> TestClient:
    """Return a fastAPI test client initialized with our app."""
    with TestClient(api, raise_server_exceptions=False) as test_client:
        return test_client


@pytest.fixture(autouse=True)
def settings(
    caplog: LogCaptureFixture,
    request: pytest.FixtureRequest,
    is_integration_test: bool,  # noqa: FBT001
    isolate_settings: None,  # noqa: ARG001
) -> AdminSettings:
    """Load and return the correct admin settings."""
    verbosity = request.config.option.verbose
    cutoff_level = logging.INFO if verbosity >= 2 else logging.WARNING
    with caplog.at_level(cutoff_level, logger=logger.name):
        settings = AdminSettings.get()
        if is_integration_test:
            settings.identity_provider = IdentityProvider.BACKEND
        else:
            settings.identity_provider = IdentityProvider.MEMORY
            settings.admin_user_database = AdminUserDatabase(
                read={"reader": AdminUserPassword("read_pw")},
                write={"writer": AdminUserPassword("write_pw")},
            )
    return settings


@pytest.fixture
def reader_user_credentials(settings: AdminSettings) -> tuple[str, SecretStr]:
    for username, password in settings.admin_user_database["read"].items():
        return username, password
    msg = "No reader configured"  # pragma: no cover
    raise RuntimeError(msg)  # pragma: no cover


@pytest.fixture
def writer_user_credentials(settings: AdminSettings) -> tuple[str, SecretStr]:
    for username, password in settings.admin_user_database["write"].items():
        return username, password
    msg = "No writer configured"  # pragma: no cover
    raise RuntimeError(msg)  # pragma: no cover


def set_generous_timeouts(page: Page) -> None:
    """Raise playwright's default timeouts to survive slow reflex page loads."""
    page.set_default_navigation_timeout(50_000)
    page.set_default_timeout(30_000)
    expect.set_options(timeout=30_000)


def prepare_page(
    page: Page,
    base_url: str,
    credentials: tuple[str, SecretStr],
) -> Page:
    """Prepare a for an integration test by performing a login and setting timeouts."""
    page.goto(base_url)
    page.get_by_test_id("input-username").fill(credentials[0])
    page.get_by_test_id("input-password").fill(credentials[1].get_secret_value())
    page.get_by_test_id("login-button").click()
    expect(page.get_by_test_id("page-body")).to_be_visible()
    set_generous_timeouts(page)
    return page


@pytest.fixture
def writer_user_page(
    page: Page, writer_user_credentials: tuple[str, SecretStr], base_url: str
) -> Generator[Page]:
    """Return a page with a logged in writer user context."""
    page = prepare_page(page, base_url, writer_user_credentials)
    yield page
    page.close()


@pytest.fixture
def reader_user_page(
    page: Page, reader_user_credentials: tuple[str, SecretStr], base_url: str
) -> Generator[Page]:
    """Return a page with a logged in reader user context."""
    page = prepare_page(page, base_url, reader_user_credentials)
    yield page
    page.close()


@pytest.fixture(autouse=True)
def flush_graph_database(is_integration_test: bool) -> None:  # noqa: FBT001
    """Flush the graph database before every integration test."""
    if is_integration_test:
        connector = BackendApiConnector.get()
        connector.flush_graph()


@pytest.fixture
def dummy_data(
    request: pytest.FixtureRequest,
) -> list[AnyExtractedModel]:
    """Create a set of interlinked dummy data."""
    primary_source_1 = ExtractedPrimarySource(
        hadPrimarySource=MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
        identifierInPrimarySource="ps-1",
        title=[Text(value="Primary Source One", language=TextLanguage.EN)],
    )
    primary_source_2 = ExtractedPrimarySource(
        hadPrimarySource=MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
        identifierInPrimarySource="ps-2",
        version="Cool Version v2.13",
        title=[Text(value="Primary Source Two", language=TextLanguage.EN)],
    )
    contact_point_1 = ExtractedContactPoint(
        email=["info@contact-point.one"],
        hadPrimarySource=primary_source_1.stableTargetId,
        identifierInPrimarySource="cp-1",
    )
    contact_point_2 = ExtractedContactPoint(
        email=["help@contact-point.two"],
        hadPrimarySource=primary_source_1.stableTargetId,
        identifierInPrimarySource="cp-2",
    )
    organizational_unit_1 = ExtractedOrganizationalUnit(
        hadPrimarySource=primary_source_2.stableTargetId,
        identifierInPrimarySource="ou-1",
        name=[Text(value="Unit 1", language=TextLanguage.EN)],
        shortName=["OU1"],
    )
    test_module = request.module.__name__

    if "consent" in test_module:
        user_id = get_logged_in_user_id()
    else:
        user_id = contact_point_1.stableTargetId  # type: ignore[assignment]
    activity_1 = ExtractedActivity(
        abstract=[
            Text(value="An active activity.", language=TextLanguage.EN),
            Text(value="Une activité active.", language=None),
        ],
        contact=[
            user_id,
            organizational_unit_1.stableTargetId,
        ],
        hadPrimarySource=primary_source_1.stableTargetId,
        identifierInPrimarySource="a-1",
        responsibleUnit=[organizational_unit_1.stableTargetId],
        shortName=["A1"],
        start=[YearMonthDay(1999, 12, 24)],
        end=[YearMonthDay(2023, 1, 1)],
        theme=[Theme["INFECTIOUS_DISEASES_AND_EPIDEMIOLOGY"]],
        title=[Text(value="Aktivität 1", language=TextLanguage.DE)],
        website=[
            Link(title="Activity Homepage", url="https://activity-1"),
            Link(url="https://activity-homepage-1"),
        ],
    )
    resource_1 = ExtractedResource(
        hadPrimarySource=primary_source_1.stableTargetId,
        identifierInPrimarySource="r-1",
        accessRestriction=AccessRestriction["OPEN"],
        contact=[user_id],
        theme=[Theme["BIOINFORMATICS_AND_SYSTEMS_BIOLOGY"]],
        title=[Text(value="Bioinformatics Resource 1", language=None)],
        unitInCharge=[organizational_unit_1.stableTargetId],
    )
    resource_2 = ExtractedResource(
        hadPrimarySource=primary_source_2.stableTargetId,
        identifierInPrimarySource="r-2",
        accessRestriction=AccessRestriction["OPEN"],
        contact=[user_id, contact_point_2.stableTargetId],
        theme=[Theme["PUBLIC_HEALTH"]],
        title=[
            Text(value="Some Resource with many titles 1", language=None),
            Text(value="Some Resource with many titles 2", language=TextLanguage.EN),
            Text(value="Eine Resource mit vielen Titeln 3", language=TextLanguage.DE),
            Text(value="Some Resource with many titles 4", language=None),
        ],
        unitInCharge=[organizational_unit_1.stableTargetId],
    )
    return [
        primary_source_1,
        primary_source_2,
        contact_point_1,
        contact_point_2,
        organizational_unit_1,
        activity_1,
        resource_1,
        resource_2,
    ]


@pytest.fixture
def dummy_data_by_identifier_in_primary_source(
    dummy_data: list[AnyExtractedModel],
) -> dict[str, AnyExtractedModel]:
    return {model.identifierInPrimarySource: model for model in dummy_data}


@pytest.fixture
def dummy_data_by_stable_target_id(
    dummy_data: list[AnyExtractedModel],
) -> dict[Identifier, AnyExtractedModel]:
    return {model.stableTargetId: model for model in dummy_data}


@pytest.fixture
def load_dummy_data(
    dummy_data: list[AnyExtractedModel],
    flush_graph_database: None,  # noqa: ARG001
) -> None:
    """Ingest dummy data into the backend."""
    connector = BackendApiConnector.get()
    connector.ingest(dummy_data)


@pytest.fixture
def load_pagination_dummy_data(
    dummy_data: list[AnyExtractedModel],
    flush_graph_database: None,  # noqa: ARG001
    request: pytest.FixtureRequest,
) -> None:
    """Ingest dummy data into the backend with dynamic model types based on test context."""
    connector = BackendApiConnector.get()
    primary_source_1 = next(
        x for x in dummy_data if x.identifierInPrimarySource == "ps-1"
    )

    pagination_dummy_data = []
    pagination_dummy_data.extend(dummy_data)

    # Determine which type of models to create based on test module
    test_module = request.module.__name__

    if "consent" in test_module:
        user_id = get_logged_in_user_id()
        organizational_unit_1 = next(
            x for x in dummy_data if x.identifierInPrimarySource == "ou-1"
        )
        pagination_dummy_data.extend(
            [
                ExtractedResource(
                    hadPrimarySource=cast(
                        "MergedPrimarySourceIdentifier", primary_source_1.stableTargetId
                    ),
                    identifierInPrimarySource=f"r-pagination-test-{i}",
                    accessRestriction=AccessRestriction["OPEN"],
                    contact=[
                        cast(
                            "MergedContactPointIdentifier",
                            user_id,
                        )
                    ],
                    theme=[Theme["BIOINFORMATICS_AND_SYSTEMS_BIOLOGY"]],
                    title=[Text(value=f"Pagination Test Resource {i}", language=None)],
                    unitInCharge=[
                        cast(
                            "MergedOrganizationalUnitIdentifier",
                            organizational_unit_1.stableTargetId,
                        )
                    ],
                )
                for i in range(100)
            ]
        )
    else:
        pagination_dummy_data.extend(
            [
                ExtractedContactPoint(
                    email=[f"help-{i}@pagination.abc"],
                    hadPrimarySource=cast(
                        "MergedPrimarySourceIdentifier", primary_source_1.stableTargetId
                    ),
                    identifierInPrimarySource=f"cp-pagination-test-{i}",
                )
                for i in range(100)
            ]
        )

    connector.ingest(pagination_dummy_data)


@pytest.fixture
def extracted_activity(
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> ExtractedActivity:
    extracted_activity = dummy_data_by_identifier_in_primary_source["a-1"]
    assert type(extracted_activity) is ExtractedActivity
    return extracted_activity


def build_pagination_regex(current: int, total: int) -> Pattern[str]:
    return re.compile(rf"\w+\s{current}\s\w+\s{total}\s\w+")


def build_search_summary_regex(first: int, last: int, total: int) -> Pattern[str]:
    """Match the search page summary in any locale, ignoring the measured duration."""
    service = LocaleService.get()
    summaries = (
        re.escape(
            service.get_ui_label(locale.id, "search.result_summary.format").format(
                first, last, total, 0.0
            )
        ).replace(r"0\.0", r"\d+\.\d+")
        for locale in service.get_available_locales()
    )
    return re.compile(f"({'|'.join(summaries)})")


def build_ui_label_regex(label_id: str) -> Pattern[str]:
    service = LocaleService.get()
    ui_labels = (
        re.escape(service.get_ui_label(locale.id, label_id))
        for locale in service.get_available_locales()
    )
    return re.compile(f"({'|'.join(ui_labels)})")


def get_logged_in_user_id() -> MergedPersonIdentifier:
    """Return the merged person identifier of the currently logged in user."""
    settings = AdminSettings.get()
    url = urlsplit(settings.ldap_url.get_secret_value())
    connector = LDAPBackendApiConnector.get()
    persons = connector.merged_person_from_login(
        username=str(url.username), password=str(url.password)
    )
    if not persons:
        msg = "No merged login person found for the logged in user."
        raise RuntimeError(msg)
    return persons.identifier

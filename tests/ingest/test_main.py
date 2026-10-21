import pytest
from playwright.sync_api import Locator, Page, expect

from mex.admin.ingest.models import ALL_AUX_PROVIDERS, AuxProviderKey
from mex.common.backend_api.connector import BackendApiConnector
from tests.conftest import build_ui_label_regex


@pytest.fixture
def ingest_page(base_url: str, writer_user_page: Page) -> Page:
    page = writer_user_page
    page.goto(f"{base_url}/ingest")
    section = page.get_by_test_id("aux-tab-section")
    expect(section).to_be_visible()
    return page


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_aux_tab_section(ingest_page: Page) -> None:
    page = ingest_page
    nav_bar = page.get_by_test_id("aux-tab-section")
    page.screenshot(path="tests_ingest_test_main-test_aux_tab_section.png")
    expect(nav_bar).to_be_visible()


def expand_show_all_properties(page: Page, expand_button: Locator) -> None:
    """Expand the first result card, retrying until the full property list renders.

    The toggle is a controlled component whose state lives on the server, so a click
    that lands before the result list is hydrated is silently dropped. Re-clicking is
    safe in that case, because a dropped click leaves the state untouched.
    """
    all_properties = page.get_by_test_id("display-properties-all")
    for _ in range(2):
        expand_button.click()
        try:
            expect(all_properties).to_be_visible(timeout=15_000)
        except AssertionError:
            continue
        else:
            return
    expand_button.click()
    expect(all_properties).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_and_ingest_roundtrip(ingest_page: Page) -> None:
    page = ingest_page
    ldap = next(p for p in ALL_AUX_PROVIDERS if p.key == AuxProviderKey.LDAP)

    # count the items before
    connector = BackendApiConnector.get()
    result = connector.fetch_extracted_items(entity_type=["ExtractedPerson"])
    assert result.total == 0
    items_before = result.total

    # go to the correct tab
    aux_provider_tab = page.get_by_role("tab", name=str(ldap))
    expect(aux_provider_tab).to_be_enabled(timeout=50_000)
    aux_provider_tab.click()
    search_input = page.get_by_test_id("search-input")
    expect(search_input).to_be_visible()
    expect(search_input).to_be_enabled()

    # trigger a search
    # note: the ldap mock of the testing backend answers every query with the same
    # three persons, so there is no query we could use to assert an empty result here
    search_input.fill("L*")
    search_input.press("Enter")
    expect(search_input).to_be_enabled(timeout=30_000)
    page.screenshot(path="tests_ingest_test_main-roundtrip_ldap-search.png")

    # test pagination is showing
    prev_button = page.get_by_test_id("pagination-previous-button")
    expect(prev_button).to_be_disabled(timeout=30_000)
    expect(page.get_by_test_id("pagination-next-button")).to_be_visible()
    expect(page.get_by_test_id("pagination-page-select")).to_be_visible()

    # test expand button works
    expand_button = page.get_by_test_id("toggle-show-all-properties-button").first
    expect(expand_button).to_be_visible()

    page.screenshot(path="tests_ingest_test_main-roundtrip_ldap.png")
    expect(page.get_by_test_id("display-properties-all")).not_to_be_visible()
    expand_show_all_properties(page, expand_button)
    page.screenshot(path="tests_ingest_test_main-roundtrip_ldap-expanded.png")

    # test ingest button works
    ingest_button = page.get_by_test_id("ingest-button-0")
    ingest_button.click()
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    expect(ingest_button).to_be_disabled()
    page.screenshot(path="tests_ingest_test_main-roundtrip_ldap-ingested.png")
    page.reload()
    expect(ingest_button).to_be_disabled()
    page.screenshot(path="tests_ingest_test_main-roundtrip_ldap-ingested-reload.png")

    # count the items afterwards
    result = connector.fetch_extracted_items(entity_type=["ExtractedPerson"])
    assert result.total > items_before


@pytest.mark.integration
def test_infobox_visibility_and_content(ingest_page: Page) -> None:
    page = ingest_page
    expected_callout_content = {
        AuxProviderKey.LDAP: build_ui_label_regex("ingest.search_info.ldap"),
        AuxProviderKey.WIKIDATA: build_ui_label_regex("ingest.search_info.wikidata"),
        AuxProviderKey.ORCID: None,
    }

    for provider in ALL_AUX_PROVIDERS:
        tab = page.get_by_role("tab", name=provider.dynamic_name)
        tab.click()
        callout = page.get_by_test_id("ingest-infobox-callout")

        expected_content = expected_callout_content[provider.key]
        if expected_content:
            expect(callout).to_have_count(1)
            expect(callout).to_have_text(expected_content)
        else:
            expect(callout).to_have_count(0)

        page.screenshot(path=f"tests_ingest_test_main-test_infobox_{provider}.png")

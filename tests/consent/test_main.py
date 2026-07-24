from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import Page, expect

from mex.admin.settings import AdminSettings


@pytest.fixture
def login_ldap_user(
    page: Page,
    base_url: str,
) -> Page:
    settings = AdminSettings.get()
    url = urlsplit(settings.ldap_url.get_secret_value())
    page.goto(f"{base_url}/consent")
    page.get_by_test_id("input-username").fill(str(url.username))
    page.get_by_test_id("input-password").fill(str(url.password))
    page.get_by_test_id("login-button").click()
    page.wait_for_timeout(3000)
    page.screenshot(path="tests_ldap_login.png")
    expect(page.get_by_test_id("nav-bar")).to_be_visible()
    return page


@pytest.fixture
def consent_page(
    base_url: str,
    login_ldap_user: Page,
) -> Page:
    page = login_ldap_user
    page.goto(f"{base_url}/consent")
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    page.wait_for_timeout(5000)
    page.screenshot(path="tests_consent_test_main-test_index-on-load.png")
    return page


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_projects_and_resources(consent_page: Page) -> None:
    page = consent_page
    resources_section = page.get_by_test_id("user-resources")
    expect(resources_section).to_be_visible()
    expect(resources_section).to_contain_text("Bioinformatics Resource 1")
    projects_section = page.get_by_test_id("user-projects")
    expect(projects_section).to_be_visible()
    expect(projects_section).to_contain_text("Aktivität 1")


@pytest.mark.integration
@pytest.mark.usefixtures("load_pagination_dummy_data")
def test_pagination(consent_page: Page) -> None:
    page = consent_page

    res_list = page.get_by_test_id("user-resources")
    pagination_previous = res_list.get_by_test_id("pagination-previous-button")
    pagination_next = res_list.get_by_test_id("pagination-next-button")
    pagination_page_select = res_list.get_by_test_id("pagination-page-select")

    pagination_page_select.scroll_into_view_if_needed()
    page.screenshot(path="tests_consent_test_main_test_pagination.png")

    # check if:
    # - previous is disabled
    # - select shows all expected page numbers
    # - next is enabled
    expect(pagination_previous).to_be_disabled()
    expect(pagination_page_select).to_have_text("1")
    pagination_page_select.click()
    opt1 = page.get_by_role("option", name="1", exact=True)
    expect(opt1).to_be_visible()
    expect(opt1).to_have_attribute("data-state", "checked")
    expect(page.get_by_role("option", name="2", exact=True)).to_be_visible()
    expect(page.get_by_role("option", name="3", exact=True)).to_be_visible()
    expect(pagination_next).to_be_enabled()

    # Navigate to the last page (page 21)
    page.get_by_role("option", name="21", exact=True).click()
    expect(pagination_previous).to_be_enabled()
    expect(pagination_page_select).to_have_text("21")
    expect(pagination_next).to_be_disabled()

    # Test going back one page
    pagination_previous.click()
    expect(pagination_previous).to_be_enabled()
    expect(pagination_page_select).to_have_text("20")
    expect(pagination_next).to_be_enabled()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_index(consent_page: Page) -> None:
    settings = AdminSettings.get()
    url = urlsplit(settings.ldap_url.get_secret_value())
    page = consent_page

    # load page and check user information is visible
    user_data = page.get_by_test_id("user-data")
    expect(user_data).to_be_visible()
    expect(user_data).to_contain_text(str(url.username))
    expect(user_data).to_contain_text(f"{url.username}@rki.com")

    # check consent box and buttons are visible
    consent_box = page.get_by_test_id("consent-box")
    expect(consent_box).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_submit_consent(consent_page: Page) -> None:
    page = consent_page
    today = datetime.now(tz=ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y")

    consent_status = page.get_by_test_id("consent-status")
    consent_status.scroll_into_view_if_needed()

    # submit the denial first: once positive consent is valid, retraction is
    # prohibited and the denial button becomes disabled, so it has to be tested
    # before consent is given
    denial_button = page.get_by_test_id("denial-consent-button")
    denial_button.click()
    page.screenshot(path="tests_consent_test_main-test_submit_consent_invalid.png")
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    expect(consent_status).to_contain_text(f"Sie haben Ihre Ablehnung am {today}")

    # check if given consent is submitted
    page.get_by_test_id("accept-consent-button").click()
    page.screenshot(path="tests_consent_test_main-test_submit_consent_valid.png")
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    expect(page.get_by_test_id("consent-status")).to_contain_text(
        f"Sie haben Ihre Einwilligung am {today}"
    )

    # check if denial button is disabled after positive consent
    expect(denial_button).to_be_disabled()

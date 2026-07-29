import pytest
from playwright.sync_api import Page, expect

from tests.conftest import build_search_summary_regex


@pytest.fixture
def home_page(
    base_url: str,
    reader_user_page: Page,
) -> Page:
    page = reader_user_page
    page.goto(base_url)
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


@pytest.mark.integration
def test_index(home_page: Page) -> None:
    page = home_page

    # load page and establish the start page search box is visible
    expect(page.get_by_test_id("start-page-body")).to_be_visible()
    expect(page.get_by_test_id("start-search-input")).to_be_visible()
    expect(page.get_by_test_id("start-search-button")).to_be_visible()
    page.screenshot(path="tests_home_test_main-test_index-on-load.png")


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_start_search(base_url: str, home_page: Page) -> None:
    page = home_page

    # submitting the start page search leads to the search page
    search_input = page.get_by_test_id("start-search-input")
    expect(search_input).to_be_visible()
    search_input.fill("Bioinformatics")
    search_input.press("Enter")

    page.wait_for_url(f"{base_url}/search?q=Bioinformatics&page=1")
    search_results_summary = page.get_by_test_id("search-results-summary")
    expect(search_results_summary).to_be_visible()
    page.screenshot(path="tests_home_test_main-test_start_search-on-search.png")
    expect(search_results_summary).to_have_text(build_search_summary_regex(1, 1, 1))


@pytest.mark.integration
def test_app_logo_links_to_start_page(base_url: str, home_page: Page) -> None:
    page = home_page
    page.goto(f"{base_url}/search")
    expect(page.get_by_test_id("search-sidebar")).to_be_visible()

    page.get_by_test_id("app-logo").click()

    page.wait_for_url(f"{base_url}/")
    expect(page.get_by_test_id("start-search-input")).to_be_visible()

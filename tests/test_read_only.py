"""Integration tests for the softly enforced read-only mode.

Users without write access must not be shown any control that would trigger a
backend write, nor be led to the pages that exist only to perform one. The routes
themselves stay reachable by direct URL on purpose - this is a UI affordance, not
a security boundary (proper enforcement follows with OIDC/JWT, MX-1616).
"""

import re

import pytest
from playwright.sync_api import Page, expect

from mex.common.models import ExtractedActivity

# write controls a writer always gets on a loaded item
WRITE_CONTROL_TEST_IDS = [
    "submit-button",
    "publish-targets",
]
# write controls that additionally depend on item state: delete/reset needs the
# item to already carry rules (rules/state.py), discard needs unsaved changes
CONDITIONAL_WRITE_CONTROL_TEST_IDS = [
    "delete-reset-dialog-button",
    "discard-changes-dialog-button",
]
EMPTY_VALUE_PATTERN = re.compile(r"^empty-value-")
# subtractive and preventive rule toggles, see rules/main.py; radix renders these
# without a queryable "switch" aria role, so match on the test id instead
SWITCH_PATTERN = re.compile(r"^switch-")


def _open_edit_page(page: Page, base_url: str, identifier: str) -> Page:
    """Open the edit page and wait for the editor to finish loading."""
    page.goto(f"{base_url}/item/{identifier}")
    # the heading only appears once the item is loaded - without this wait the
    # `to_have_count(0)` assertions below would pass on a still-empty page
    expect(page.get_by_test_id("edit-heading")).to_be_visible()
    return page


@pytest.fixture
def reader_edit_page(
    base_url: str,
    reader_user_page: Page,
    extracted_activity: ExtractedActivity,
    load_dummy_data: None,  # noqa: ARG001
) -> Page:
    return _open_edit_page(
        reader_user_page, base_url, str(extracted_activity.stableTargetId)
    )


@pytest.fixture
def writer_edit_page(
    base_url: str,
    writer_user_page: Page,
    extracted_activity: ExtractedActivity,
    load_dummy_data: None,  # noqa: ARG001
) -> Page:
    return _open_edit_page(
        writer_user_page, base_url, str(extracted_activity.stableTargetId)
    )


@pytest.mark.integration
def test_nav_bar_hides_write_only_pages(reader_user_page: Page) -> None:
    page = reader_user_page
    nav_bar = page.get_by_test_id("nav-bar")
    expect(nav_bar).to_be_visible()
    page.screenshot(path="tests_test_read_only-test_nav_bar_hides_write_only_pages.png")

    expect(page.get_by_test_id("nav-item-/search")).to_be_visible()
    expect(page.get_by_test_id("nav-item-/advanced-search")).to_be_visible()
    expect(page.get_by_test_id("nav-item-/item/[item_id]")).to_be_visible()

    expect(page.get_by_test_id("nav-item-/create")).to_have_count(0)
    expect(page.get_by_test_id("nav-item-/merge")).to_have_count(0)
    expect(page.get_by_test_id("nav-item-/ingest")).to_have_count(0)


@pytest.mark.integration
def test_nav_bar_shows_write_only_pages_for_writer(writer_user_page: Page) -> None:
    page = writer_user_page
    expect(page.get_by_test_id("nav-bar")).to_be_visible()

    expect(page.get_by_test_id("nav-item-/create")).to_be_visible()
    expect(page.get_by_test_id("nav-item-/merge")).to_be_visible()
    expect(page.get_by_test_id("nav-item-/ingest")).to_be_visible()


@pytest.mark.integration
def test_edit_page_shows_write_controls_for_writer(writer_edit_page: Page) -> None:
    """Guard the read-only test below against vacuously passing on stale test ids."""
    page = writer_edit_page
    page.screenshot(
        path="tests_test_read_only-test_edit_page_shows_write_controls_for_writer.png"
    )

    for test_id in WRITE_CONTROL_TEST_IDS:
        expect(page.get_by_test_id(test_id)).to_be_visible()
    assert page.get_by_test_id(SWITCH_PATTERN).count() > 0


@pytest.mark.integration
def test_edit_page_is_read_only(reader_edit_page: Page) -> None:
    page = reader_edit_page
    page.screenshot(path="tests_test_read_only-test_edit_page_is_read_only.png")

    # the item itself stays fully readable
    expect(page.get_by_test_id("edit-heading")).to_be_visible()

    # but nothing that writes, or prepares a write, is offered
    for test_id in WRITE_CONTROL_TEST_IDS + CONDITIONAL_WRITE_CONTROL_TEST_IDS:
        expect(page.get_by_test_id(test_id)).to_have_count(0)
    expect(page.get_by_test_id(SWITCH_PATTERN)).to_have_count(0)


@pytest.mark.integration
def test_edit_page_fills_empty_columns_for_reader(reader_edit_page: Page) -> None:
    """A primary source with no values must not collapse its column.

    For writers that column is filled by the add-additive button. Hiding that
    button left read-only users with an empty flex child, which knocked the
    three column grid out of alignment.
    """
    page = reader_edit_page

    assert page.get_by_test_id(EMPTY_VALUE_PATTERN).count() > 0


@pytest.mark.integration
def test_edit_page_has_no_empty_columns_for_writer(writer_edit_page: Page) -> None:
    """Writers keep the add-additive button, so the placeholder must not appear."""
    page = writer_edit_page

    expect(page.get_by_test_id(EMPTY_VALUE_PATTERN)).to_have_count(0)


def _open_merge_page_with_results(page: Page, base_url: str) -> Page:
    """Open the merge page and list some results on the goner side.

    The page loads on an entity type without dummy data, so without an actual
    search there would be no result rows - and no selection checkboxes to make
    an assertion about either way.
    """
    page.goto(f"{base_url}/merge")
    expect(page.get_by_test_id("merge-heading")).to_be_visible()

    page.get_by_test_id("entity-type-select").click()
    page.get_by_test_id(
        re.compile(r"^value-label-select-item-\d+-ContactPoint$")
    ).click()
    page.get_by_test_id("search-button-goner").click()

    results = page.get_by_test_id("goner-search-results-container")
    expect(results.get_by_test_id(re.compile(r"^search-result-"))).not_to_have_count(0)
    return page


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_merge_page_shows_write_controls_for_writer(
    base_url: str, writer_user_page: Page
) -> None:
    """Guard the read-only test below against vacuously passing on stale test ids."""
    page = _open_merge_page_with_results(writer_user_page, base_url)

    expect(page.get_by_test_id("submit-button")).to_be_visible()
    assert (
        page.get_by_test_id("goner-search-results-container")
        .get_by_role("checkbox")
        .count()
        > 0
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_merge_page_is_read_only(base_url: str, reader_user_page: Page) -> None:
    page = _open_merge_page_with_results(reader_user_page, base_url)
    page.screenshot(path="tests_test_read_only-test_merge_page_is_read_only.png")

    # the search panels still work, they just cannot feed a merge
    expect(page.get_by_test_id("search-input-goner")).to_be_visible()
    expect(page.get_by_test_id("search-input-keeper")).to_be_visible()

    expect(page.get_by_test_id("submit-button")).to_have_count(0)
    expect(
        page.get_by_test_id("goner-search-results-container").get_by_role("checkbox")
    ).to_have_count(0)


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_ingest_page_is_read_only(base_url: str, reader_user_page: Page) -> None:
    # the writer-side presence of `ingest-button-*` is covered by
    # tests/ingest/test_main.py, which drives a real aux provider search
    page = reader_user_page
    page.goto(f"{base_url}/ingest")
    expect(page.get_by_test_id("aux-tab-section")).to_be_visible()
    page.screenshot(path="tests_test_read_only-test_ingest_page_is_read_only.png")

    expect(page.get_by_test_id("ingest-button-0")).to_have_count(0)


@pytest.mark.integration
def test_create_page_offers_no_editor(base_url: str, reader_user_page: Page) -> None:
    page = reader_user_page
    page.goto(f"{base_url}/create")
    expect(page.get_by_test_id("create-heading")).to_be_visible()
    page.screenshot(path="tests_test_read_only-test_create_page_offers_no_editor.png")

    expect(page.get_by_test_id("entity-type-select")).to_have_count(0)
    expect(page.get_by_test_id("submit-button")).to_have_count(0)

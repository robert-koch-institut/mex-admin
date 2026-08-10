import re

import pytest
from playwright.sync_api import Locator, Page, expect

from mex.common.models import (
    AnyExtractedModel,
    ExtractedContactPoint,
    ExtractedResource,
)
from tests.conftest import build_search_summary_regex, build_ui_label_regex


@pytest.fixture
def merge_page(
    base_url: str,
    writer_user_page: Page,
) -> Page:
    page = writer_user_page
    page.goto(f"{base_url}/merge")
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


def select_entity_type(page: Page, stem_type: str) -> None:
    """Pick the given stem type in the shared entity type select."""
    page.get_by_test_id("entity-type-select").click()
    page.get_by_test_id(
        re.compile(rf"^value-label-select-item-\d+-{stem_type}$")
    ).click()


def expect_summary(container: Locator, first: int, last: int, total: int) -> None:
    """Expect the detailed result summary of the container to show these counts."""
    expect(
        container.get_by_test_id("search-results-summary").get_by_text(
            build_search_summary_regex(
                first, last, total, "merge.result_summary.format"
            )
        )
    ).to_be_visible()


@pytest.mark.integration
def test_index(merge_page: Page) -> None:
    page = merge_page

    # load page and establish the heading with the entity type select is visible
    expect(page.get_by_test_id("merge-heading")).to_be_visible()
    expect(page.get_by_test_id("entity-type-select")).to_be_visible()

    # establish both section headings are visible
    section = page.get_by_test_id("create-heading-merged")
    expect(section).to_be_visible()
    section = page.get_by_test_id("create-heading-extracted")
    expect(section).to_be_visible()

    # check submit button is showing
    expect(page.get_by_test_id("submit-button")).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_entity_type_select_filters_both_sides(merge_page: Page) -> None:
    page = merge_page
    merged_results = page.get_by_test_id("merged-search-results-container")
    extracted_results = page.get_by_test_id("extracted-search-results-container")

    # selecting an entity type filters the merged and the extracted side
    select_entity_type(page, "ContactPoint")
    expect_summary(merged_results, 1, 2, 2)
    expect_summary(extracted_results, 1, 2, 2)

    # switching the entity type filters both sides again
    select_entity_type(page, "OrganizationalUnit")
    expect_summary(merged_results, 1, 1, 1)
    expect_summary(extracted_results, 1, 1, 1)


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_input_merged(merge_page: Page) -> None:
    page = merge_page
    merged_results = page.get_by_test_id("merged-search-results-container")

    # check merged search input is showing and working
    search_input_merged = page.get_by_test_id("search-input-merged")
    expect(search_input_merged).to_be_visible()
    search_input_merged.fill("Unit 1")
    select_entity_type(page, "OrganizationalUnit")
    page.get_by_test_id("search-button-merged").click()
    expect_summary(merged_results, 1, 1, 1)
    page.screenshot(
        path="tests_merge_items_test_main-test_merged_search_input-on-search-input-1-found.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_input_extracted(merge_page: Page) -> None:
    page = merge_page
    extracted_results = page.get_by_test_id("extracted-search-results-container")

    # check extracted search input is showing and working
    search_input_extracted = page.get_by_test_id("search-input-extracted")
    expect(search_input_extracted).to_be_visible()
    search_input_extracted.fill("Unit 1")
    select_entity_type(page, "OrganizationalUnit")
    page.get_by_test_id("search-button-extracted").click()
    expect_summary(extracted_results, 1, 1, 1)
    page.screenshot(
        path="tests_merge_items_test_main-test_extracted_search_input-on-search-input-1-found.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_select_result_extracted(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    extracted_results = page.get_by_test_id("extracted-search-results-container")

    # check extracted search result selection is working
    search_input_extracted = page.get_by_test_id("search-input-extracted")
    expect(search_input_extracted).to_be_visible()
    search_input_extracted.fill("contact")
    select_entity_type(page, "ContactPoint")
    page.get_by_test_id("search-button-extracted").click()
    expect_summary(extracted_results, 1, 2, 2)
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    result = extracted_results.get_by_test_id(
        f"search-result-{contact_point_1.identifier}"
    )
    result.get_by_role("checkbox").click()
    checked = extracted_results.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(1)
    page.screenshot(
        path="tests_merge_items_test_main-test_select_result_extracted-select.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_select_result_merged(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    merged_results = page.get_by_test_id("merged-search-results-container")

    # check merged search result selection is working
    search_input_merged = page.get_by_test_id("search-input-merged")
    expect(search_input_merged).to_be_visible()
    search_input_merged.fill("contact")
    select_entity_type(page, "ContactPoint")
    page.get_by_test_id("search-button-merged").click()
    expect_summary(merged_results, 1, 2, 2)
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    result = merged_results.get_by_test_id(
        f"search-result-{contact_point_1.stableTargetId}"
    )
    result.get_by_role("checkbox").click()
    checked = merged_results.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(1)
    page.screenshot(
        path="tests_merge_items_test_main-test_select_result_merged-select.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_resolves_identifier(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    assert isinstance(contact_point_1, ExtractedContactPoint)
    activity_1 = dummy_data_by_identifier_in_primary_source["a-1"]

    select_entity_type(page, "Activity")

    page.get_by_test_id("search-button-extracted").click()
    extracted_results = page.get_by_test_id("extracted-search-results-container")
    expect_summary(extracted_results, 1, 1, 1)
    page.screenshot(path="tests_merge_test_main-test_resolves_identifier.png")
    result = extracted_results.get_by_test_id(f"search-result-{activity_1.identifier}")
    email = result.get_by_text(f"{contact_point_1.email[0]}")
    expect(email).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_additional_titles_badge(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    # search for resources
    page = merge_page
    select_entity_type(page, "Resource")

    resource_r2 = dummy_data_by_identifier_in_primary_source["r-2"]
    assert isinstance(resource_r2, ExtractedResource)
    extracted_results = page.get_by_test_id("extracted-search-results-container")
    resource_r2_result = extracted_results.get_by_test_id(
        f"search-result-{resource_r2.identifier}"
    )
    expect(resource_r2_result).to_be_visible()
    page.screenshot(path="tests_merge_test_additional_titles_badge_on_load.png")
    first_title = resource_r2.title[0]

    # expect title is visible and there are additional titles for 'r2'
    expect(resource_r2_result).to_contain_text(first_title.value)
    additional_title_badge = page.get_by_test_id("additional-titles-badge").first
    expect(additional_title_badge).to_be_visible()
    # wait for the (re-rendering) result card to settle before scrolling, so the
    # non-retrying scroll action does not act on a detached element
    expect(additional_title_badge).to_have_text(
        build_ui_label_regex("components.titles.additional_titles")
    )
    additional_title_badge.scroll_into_view_if_needed()
    page.screenshot(path="tests_search_test_additional_titles_badge_on_visible.png")

    # hover additional titles
    box = additional_title_badge.bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=5)
    additional_title_badge.hover()
    page.screenshot(path="tests_merge_test_additional_titles_badge_on_hover.png")

    # check tooltip content
    tooltip = page.get_by_test_id("tooltip-additional-titles")
    expect(tooltip).to_be_visible()
    expect(tooltip).not_to_contain_text(first_title.value)
    for title in resource_r2.title[1:]:
        expect(tooltip).to_contain_text(title.value)

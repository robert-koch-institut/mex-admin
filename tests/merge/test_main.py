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


def select_result(page: Page, side: str, identifier: str) -> None:
    """Tick the checkbox of the given result on the given side."""
    page.get_by_test_id(f"{side}-search-results-container").get_by_test_id(
        f"search-result-{identifier}"
    ).get_by_role("checkbox").click()


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

    # establish both section headings are visible and name the two roles
    expect(page.get_by_test_id("search-heading-goner")).to_have_text(
        build_ui_label_regex("merge.search.title_goner")
    )
    expect(page.get_by_test_id("search-heading-keeper")).to_have_text(
        build_ui_label_regex("merge.search.title_keeper")
    )

    # check submit button is showing
    expect(page.get_by_test_id("submit-button")).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_entity_type_select_filters_both_sides(merge_page: Page) -> None:
    page = merge_page
    goner_results = page.get_by_test_id("goner-search-results-container")
    keeper_results = page.get_by_test_id("keeper-search-results-container")

    # selecting an entity type filters both sides
    select_entity_type(page, "ContactPoint")
    expect_summary(goner_results, 1, 2, 2)
    expect_summary(keeper_results, 1, 2, 2)

    # switching the entity type filters both sides again
    select_entity_type(page, "OrganizationalUnit")
    expect_summary(goner_results, 1, 1, 1)
    expect_summary(keeper_results, 1, 1, 1)


@pytest.mark.integration
@pytest.mark.usefixtures("load_pagination_dummy_data")
def test_entity_type_select_resets_pagination(merge_page: Page) -> None:
    page = merge_page
    goner_results = page.get_by_test_id("goner-search-results-container")
    page_select = goner_results.get_by_test_id("pagination-page-select")

    select_entity_type(page, "ContactPoint")
    goner_results.get_by_test_id("pagination-next-button").click()
    expect(page_select).to_have_text("2")
    expect_summary(goner_results, 51, 100, 102)

    # switching the entity type has to go back to page 1, otherwise the skip of
    # the old page would leap clean over the whole new result set
    select_entity_type(page, "Resource")
    expect(page_select).to_have_text("1")
    expect_summary(goner_results, 1, 2, 2)


@pytest.mark.integration
@pytest.mark.usefixtures("load_pagination_dummy_data")
def test_pagination(merge_page: Page) -> None:
    page = merge_page
    select_entity_type(page, "ContactPoint")

    # both sides paginate on their own, so each starts on page 1 of 102 items
    for side in ("goner", "keeper"):
        container = page.get_by_test_id(f"{side}-search-results-container")
        previous_button = container.get_by_test_id("pagination-previous-button")
        next_button = container.get_by_test_id("pagination-next-button")
        page_select = container.get_by_test_id("pagination-page-select")
        page_select.scroll_into_view_if_needed()

        expect(page_select).to_have_text("1")
        expect(previous_button).to_be_disabled()
        expect(next_button).to_be_enabled()
        expect_summary(container, 1, 50, 102)

        next_button.click()
        expect(page_select).to_have_text("2")
        expect(previous_button).to_be_enabled()
        expect_summary(container, 51, 100, 102)

        next_button.click()
        expect(page_select).to_have_text("3")
        expect(next_button).to_be_disabled()
        expect_summary(container, 101, 102, 102)

        previous_button.click()
        expect(page_select).to_have_text("2")
        expect_summary(container, 51, 100, 102)

    page.screenshot(path="tests_merge_test_main-test_pagination.png")


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_input_goner(merge_page: Page) -> None:
    page = merge_page
    goner_results = page.get_by_test_id("goner-search-results-container")

    # check goner search input is showing and working
    search_input_goner = page.get_by_test_id("search-input-goner")
    expect(search_input_goner).to_be_visible()
    search_input_goner.fill("Unit 1")
    select_entity_type(page, "OrganizationalUnit")
    page.get_by_test_id("search-button-goner").click()
    expect_summary(goner_results, 1, 1, 1)
    page.screenshot(
        path="tests_merge_items_test_main-test_goner_search_input-on-search-input-1-found.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_input_keeper(merge_page: Page) -> None:
    page = merge_page
    keeper_results = page.get_by_test_id("keeper-search-results-container")

    # check keeper search input is showing and working
    search_input_keeper = page.get_by_test_id("search-input-keeper")
    expect(search_input_keeper).to_be_visible()
    search_input_keeper.fill("Unit 1")
    select_entity_type(page, "OrganizationalUnit")
    page.get_by_test_id("search-button-keeper").click()
    expect_summary(keeper_results, 1, 1, 1)
    page.screenshot(
        path="tests_merge_items_test_main-test_keeper_search_input-on-search-input-1-found.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_select_result_keeper(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    keeper_results = page.get_by_test_id("keeper-search-results-container")

    # check keeper search result selection is working
    search_input_keeper = page.get_by_test_id("search-input-keeper")
    expect(search_input_keeper).to_be_visible()
    search_input_keeper.fill("contact")
    select_entity_type(page, "ContactPoint")
    page.get_by_test_id("search-button-keeper").click()
    expect_summary(keeper_results, 1, 2, 2)
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    select_result(page, "keeper", str(contact_point_1.stableTargetId))
    expect(keeper_results.get_by_role("checkbox", checked=True)).to_have_count(1)
    page.screenshot(
        path="tests_merge_items_test_main-test_select_result_keeper-select.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_select_result_goner(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    goner_results = page.get_by_test_id("goner-search-results-container")

    # check goner search result selection is working
    search_input_goner = page.get_by_test_id("search-input-goner")
    expect(search_input_goner).to_be_visible()
    search_input_goner.fill("contact")
    select_entity_type(page, "ContactPoint")
    page.get_by_test_id("search-button-goner").click()
    expect_summary(goner_results, 1, 2, 2)
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    select_result(page, "goner", str(contact_point_1.stableTargetId))
    expect(goner_results.get_by_role("checkbox", checked=True)).to_have_count(1)
    page.screenshot(
        path="tests_merge_items_test_main-test_select_result_goner-select.png"
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_submit_button_needs_both_selections(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    submit_button = page.get_by_test_id("submit-button")
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    contact_point_2 = dummy_data_by_identifier_in_primary_source["cp-2"]

    # without any selection there is nothing to merge
    expect(submit_button).to_be_disabled()
    select_entity_type(page, "ContactPoint")
    expect(submit_button).to_be_disabled()

    # selecting only the goner side is still not enough
    select_result(page, "goner", str(contact_point_1.stableTargetId))
    expect(submit_button).to_be_disabled()

    # only with a selection on both sides the merge can be submitted
    select_result(page, "keeper", str(contact_point_2.stableTargetId))
    expect(submit_button).to_be_enabled()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_submit_dialog_can_be_cancelled(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    contact_point_2 = dummy_data_by_identifier_in_primary_source["cp-2"]

    select_entity_type(page, "ContactPoint")
    select_result(page, "goner", str(contact_point_1.stableTargetId))
    select_result(page, "keeper", str(contact_point_2.stableTargetId))
    page.get_by_test_id("submit-button").click()

    # the dialog names both items, so the user can see what is about to happen
    description = page.get_by_test_id("submit-merge-description")
    expect(description).to_be_visible()
    expect(description).to_contain_text(str(contact_point_1.stableTargetId))
    expect(description).to_contain_text(str(contact_point_2.stableTargetId))
    page.screenshot(path="tests_merge_test_main-test_submit_dialog.png")

    # both identifiers open their edit page in a new tab
    for contact_point in (contact_point_1, contact_point_2):
        link = description.get_by_role("link", name=str(contact_point.stableTargetId))
        expect(link).to_have_attribute("href", f"/item/{contact_point.stableTargetId}")
        expect(link).to_have_attribute("target", "_blank")

    # cancelling closes the dialog without sending anything to the backend
    page.get_by_test_id("submit-merge-cancel-button").click()
    expect(description).not_to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_submit_merge_surfaces_backend_error(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]

    # picking the same item on both sides is rejected by the backend's
    # `not_self_merge` precondition, which makes this a stable way to cover the
    # dialog -> submit -> escalate_error path
    select_entity_type(page, "ContactPoint")
    select_result(page, "goner", str(contact_point_1.stableTargetId))
    select_result(page, "keeper", str(contact_point_1.stableTargetId))
    page.get_by_test_id("submit-button").click()
    page.get_by_test_id("submit-merge-confirm-button").click()

    expect(page.get_by_text("backend Error")).to_be_visible()
    page.screenshot(path="tests_merge_test_main-test_submit_merge_error.png")


@pytest.mark.integration
@pytest.mark.xfail(
    reason="the backend's /v0/merge is stubbed and fails with 500 NotImplementedError",
    strict=False,
)
@pytest.mark.usefixtures("load_dummy_data")
def test_submit_merge(
    merge_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = merge_page
    contact_point_1 = dummy_data_by_identifier_in_primary_source["cp-1"]
    contact_point_2 = dummy_data_by_identifier_in_primary_source["cp-2"]
    goner_identifier = str(contact_point_1.stableTargetId)

    select_entity_type(page, "ContactPoint")
    select_result(page, "goner", goner_identifier)
    select_result(page, "keeper", str(contact_point_2.stableTargetId))
    page.get_by_test_id("submit-button").click()
    page.get_by_test_id("submit-merge-confirm-button").click()

    # a green toast confirms the merge
    expect(
        page.get_by_text(build_ui_label_regex("merge.toast_success.title"))
    ).to_be_visible()

    # and both sides refresh, so the superseded item is gone from either list
    for side in ("goner", "keeper"):
        container = page.get_by_test_id(f"{side}-search-results-container")
        expect_summary(container, 1, 1, 1)
        expect(
            container.get_by_test_id(f"search-result-{goner_identifier}")
        ).not_to_be_visible()


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

    page.get_by_test_id("search-button-goner").click()
    goner_results = page.get_by_test_id("goner-search-results-container")
    expect_summary(goner_results, 1, 1, 1)
    page.screenshot(path="tests_merge_test_main-test_resolves_identifier.png")
    result = goner_results.get_by_test_id(f"search-result-{activity_1.stableTargetId}")
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
    goner_results = page.get_by_test_id("goner-search-results-container")
    resource_r2_result = goner_results.get_by_test_id(
        f"search-result-{resource_r2.stableTargetId}"
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

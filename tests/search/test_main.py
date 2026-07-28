import re

import pytest
from playwright.sync_api import Page, expect

from mex.common.models import (
    MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
    AnyExtractedModel,
    ExtractedActivity,
    ExtractedPrimarySource,
    ExtractedResource,
)
from tests.conftest import build_search_summary_regex, build_ui_label_regex


@pytest.fixture
def search_page(
    base_url: str,
    reader_user_page: Page,
) -> Page:
    page = reader_user_page
    page.goto(base_url)
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_index(search_page: Page, extracted_activity: ExtractedActivity) -> None:
    page = search_page

    # load page and establish section is visible
    component = page.get_by_test_id("search-results-component")
    expect(component).to_be_visible()
    page.screenshot(path="tests_search_test_main-test_index-on-load.png")

    # check heading is showing
    expect(page.get_by_test_id("search-results-summary")).to_be_visible()

    # check mex primary source is showing
    primary_source = page.get_by_test_id(
        f"search-result-{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    expect(primary_source.first).to_be_visible()

    # check activity is showing
    activity = page.get_by_test_id(f"search-result-{extracted_activity.stableTargetId}")
    activity.scroll_into_view_if_needed()
    expect(activity).to_be_visible()
    expect(activity).to_contain_text("info@contact-point.one")  # resolved preview

    page.screenshot(path="tests_search_test_main-test_index-focus-activity.png")


@pytest.mark.integration
@pytest.mark.usefixtures("load_pagination_dummy_data")
def test_pagination(search_page: Page) -> None:
    page = search_page

    pagination_previous = page.get_by_test_id("pagination-previous-button")
    pagination_next = page.get_by_test_id("pagination-next-button")
    pagination_page_select = page.get_by_test_id("pagination-page-select")

    pagination_page_select.scroll_into_view_if_needed()
    page.screenshot(path="tests_search_test_main_test_pagination.png")

    # check if:
    # - previous is disabled
    # - select shows all expected page numbers
    # - next is enabled
    expect(pagination_previous).to_be_disabled()
    expect(pagination_page_select).to_have_text("1")
    pagination_page_select.click()
    opt1 = page.get_by_role("option", name="1")
    expect(opt1).to_be_visible()
    expect(opt1).to_have_attribute("data-state", "checked")
    expect(page.get_by_role("option", name="2")).to_be_visible()
    expect(page.get_by_role("option", name="3")).to_be_visible()
    expect(pagination_next).to_be_enabled()
    # close the overlay, otherwise u cant click sth else
    opt1.click()

    pagination_next.click()
    expect(pagination_previous).to_be_enabled()
    expect(pagination_page_select).to_have_text("2")
    expect(pagination_next).to_be_enabled()

    pagination_next.click()
    expect(pagination_previous).to_be_enabled()
    expect(pagination_page_select).to_have_text("3")
    expect(pagination_next).to_be_disabled()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_search_input(search_page: Page) -> None:
    page = search_page

    # check sidebar is showing
    sidebar = page.get_by_test_id("search-sidebar")
    expect(sidebar).to_be_visible()

    # wait for initial state to load (Reflex hydration complete)
    expect(page.get_by_test_id("search-results-summary")).to_be_visible()

    # test search input is showing and functioning
    search_input = page.get_by_test_id("search-input")
    expect(search_input).to_be_visible()
    search_input.fill("Bioinformatics")
    search_input.press("Enter")
    page.wait_for_timeout(10000)  # wait for loading
    search_results_summary = page.get_by_test_id("search-results-summary")
    expect(search_results_summary).to_be_visible()
    page.screenshot(
        path="tests_search_test_main-test_search_input-on-search-input-1-found.png"
    )
    expect(page.get_by_test_id("search-results-summary")).to_have_text(
        build_search_summary_regex(1, 1, 1)
    )

    search_input.fill("totally random search dPhGDHu3uiEcU6VNNs0UA74bBdubC3")
    page.get_by_test_id("search-button").click()
    page.screenshot(
        path="tests_search_test_main-test_search_input-on-search-input-0-found.png"
    )
    expect(page.get_by_test_id("search-results-summary")).to_have_text(
        build_search_summary_regex(0, 0, 0)
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_entity_types(search_page: Page) -> None:
    page = search_page

    # check sidebar is showing
    sidebar = page.get_by_test_id("search-sidebar")
    expect(sidebar).to_be_visible()

    # check entity types are showing and functioning
    entity_types = page.get_by_test_id("entity-types")
    expect(entity_types).to_be_visible()
    entity_types.get_by_test_id("entity-type-Activity").click()
    expect(page.get_by_text(build_search_summary_regex(1, 1, 1))).to_be_visible()
    page.screenshot(
        path="tests_search_test_main-test_entity_types-on-select-entity-1-found.png"
    )
    entity_types.get_by_test_id("entity-type-Activity").click()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_had_primary_sources(
    search_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = search_page

    extracted_primary_source_one = dummy_data_by_identifier_in_primary_source["ps-1"]
    assert isinstance(extracted_primary_source_one, ExtractedPrimarySource)

    # check sidebar is showing
    sidebar = page.get_by_test_id("search-sidebar")
    expect(sidebar).to_be_visible()

    # activate tab for had primary source filtering
    tab = page.get_by_test_id("reference-filter-strategy-had-primary-source-tab")
    tab.click()

    # check primary sources are showing and functioning
    primary_sources = page.get_by_test_id("primary-source-filter")
    primary_sources.scroll_into_view_if_needed()
    expect(primary_sources).to_be_visible()
    # check that title is resolved if primary source has a title
    assert (
        extracted_primary_source_one.title[0].value
        in primary_sources.all_text_contents()[0]
    )

    primary_sources.get_by_text("Primary Source One").click()
    summary = page.get_by_test_id("search-results-summary")
    expect(summary).to_be_visible()
    expect(summary).to_contain_text(build_search_summary_regex(1, 4, 4))
    page.screenshot(
        path="tests_search_test_main-test_had_primary_sources-on-select-primary-source-1-found.png"
    )
    primary_sources.get_by_text("Primary Source One").click()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_load_search_params(
    base_url: str,
    search_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = search_page
    expected_model = dummy_data_by_identifier_in_primary_source["cp-2"]

    page.goto(
        f"{base_url}?q=help&page=1&entityType=ContactPoint&entityType=Consent"
        f"&hadPrimarySource={expected_model.hadPrimarySource}&referenceFilterStrategy=had_primary_source"
    )

    # check 1 item is showing
    expect(page.get_by_text(build_search_summary_regex(1, 1, 1))).to_be_visible()
    page.screenshot(
        path="tests_search_test_main-test_load_search_params-on-params-loaded.png"
    )
    search_result_cards = page.locator(".search-result-card")
    expect(search_result_cards).to_have_count(1)
    expect(search_result_cards).to_contain_text("help@contact-point.two")

    # check entity types are loaded from url
    entity_types = page.get_by_test_id("entity-types")
    unchecked = entity_types.get_by_role("checkbox", checked=False)
    expect(unchecked).to_have_count(11)
    checked = entity_types.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(2)

    # check primary sources are loaded from url
    primary_sources = page.get_by_test_id("primary-source-filter")
    unchecked = primary_sources.get_by_role("checkbox", checked=False)
    expect(unchecked).to_have_count(3)
    checked = primary_sources.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(1)


@pytest.mark.integration
def test_reference_filter_fields_for_entity_type(search_page: Page) -> None:
    page = search_page

    hps_tab = page.get_by_test_id("reference-filter-strategy-had-primary-source-tab")
    hps_tab.click()
    expect(page.get_by_test_id("primary-source-filter")).to_be_visible()

    dyn_tab = page.get_by_test_id("reference-filter-strategy-dynamic-tab")
    dyn_tab.click()
    expect(page.get_by_test_id("reference-field-filter")).to_be_visible()

    # select person entity
    entity_types = page.get_by_test_id("entity-types")
    entity_types.get_by_text("Person").click()

    ref_filter_field = page.get_by_test_id("reference-field-filter-field")
    ref_filter_field.click()

    page.screenshot(
        path="tests_search_test_main-test_reference_filter_fields_for_entity_type-on_field_click.png"
    )

    expected_person_fields = [
        "Fachgebiet",
        "Affiliation",
        "Primärsystem",
        "Stabiler Identifikator",
    ]
    for field in expected_person_fields:
        select_item = page.get_by_role("option", name=field, exact=True)
        expect(select_item).to_be_visible()


@pytest.mark.parametrize(
    ("locale_id", "expected_items"),
    [
        pytest.param(
            "de",
            [
                "Affiliation",
                "Autor*in",
                "Datei",
                "Fachgebiet",
                "Kontakt",
                "Nachfolge von",
            ],
            id="de",
        ),
        pytest.param(
            "en",
            [
                "Affiliation",
                "Access platform",
                "Contact",
                "Author",
                "Files",
                "Publishing institution",
            ],
            id="en",
        ),
    ],
)
@pytest.mark.integration
def test_reference_filter_field_translation(
    search_page: Page,
    locale_id: str,
    expected_items: list[str],
) -> None:
    page = search_page

    # switch language to specified locale
    lang_switcher = page.get_by_test_id("language-switcher")
    lang_switcher.click()
    page.get_by_test_id(f"language-switcher-menu-item-{locale_id}").click()

    # check expected items existing
    page.get_by_test_id("reference-field-filter-field").click()
    for item in expected_items:
        expect(page.get_by_role("option", name=item, exact=True)).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_reference_filter(
    search_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = search_page

    contact = dummy_data_by_identifier_in_primary_source["cp-1"]

    # open select
    page.get_by_test_id("reference-field-filter-field").click()
    # click concat option
    page.get_by_role("option", name=re.compile(r"Kontakt|Contact")).click()
    # add invalid field
    page.get_by_test_id("reference-field-filter-add-id").click()
    page.get_by_test_id("reference-field-filter-id-0").fill("invalidIdentifier!")
    # check for validation error msg
    expect(
        page.get_by_test_id("reference-field-filter").get_by_text("pattern")
    ).to_be_visible()
    page.screenshot(
        path="tests_search_test_main-test_reference_filter-reference_filter_invalid_search.png"
    )

    # set correct contact identifier
    page.get_by_test_id("reference-field-filter-id-0").fill(contact.stableTargetId)
    expect(
        page.get_by_test_id("reference-field-filter").get_by_text("pattern")
    ).not_to_be_visible()

    page.screenshot(
        path="tests_search_test_main-test_reference_filter-reference_filter_valid_search.png"
    )
    expect(page.get_by_text(build_search_summary_regex(1, 3, 3))).to_be_visible()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_push_search_params(
    base_url: str,
    search_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = search_page

    primary_source = dummy_data_by_identifier_in_primary_source["ps-1"]
    assert type(primary_source) is ExtractedPrimarySource

    # load page and verify url
    page.goto(base_url)
    page.wait_for_url(base_url)

    # select an entity type
    entity_types = page.get_by_test_id("entity-types")
    expect(entity_types).to_be_visible()
    page.screenshot(path="tests_search_test_main-test_push_search_params-on-load.png")

    activity_checkbox = entity_types.get_by_test_id("entity-type-Activity")
    activity_checkbox.click()

    # wait for the checkbox to actually become checked (websocket roundtrip complete)
    # Find the actual checkbox input by its accessible role and wait for it to be checked
    activity_checkbox_input = entity_types.get_by_test_id("entity-type-Activity")
    expect(activity_checkbox_input).to_be_checked()

    # verify exactly one checkbox is checked
    checked = entity_types.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(1)
    page.screenshot(path="tests_search_test_main-test_push_search_params-on-click.png")

    # wait for search results section to stabilize
    expect(page.get_by_test_id("search-results-component")).to_be_visible()

    # expect parameter change to be reflected in url
    page.wait_for_url(
        "**/?q=&page=1&entityType=Activity&referenceFilterStrategy=dynamic&referenceField="
    )

    # add a query string to the search constraints
    search_input = page.get_by_test_id("search-input")
    expect(search_input).to_be_visible()
    search_input.fill("Une activité active")
    search_input.press("Enter")

    # wait for search results to update
    expect(page.get_by_test_id("search-results-component")).to_be_visible()

    # expect parameter change to be reflected in url
    page.wait_for_url(
        "**?q=Une+activit%C3%A9+active&page=1&entityType=Activity"
        "&referenceFilterStrategy=dynamic&referenceField="
    )

    # activate tab for had primary source filtering
    tab = page.get_by_test_id("reference-filter-strategy-had-primary-source-tab")
    tab.click()

    # select a primary source
    primary_sources = page.get_by_test_id("primary-source-filter")
    expect(primary_sources).to_be_visible()
    page.screenshot(path="tests_search_test_main-test_push_search_params-on-load-2.png")
    checkbox = primary_sources.get_by_text(primary_source.title[0].value)
    expect(checkbox).to_be_visible()
    checkbox.click()
    page.screenshot(
        path="tests_search_test_main-test_push_search_params-on-click-2.png"
    )

    # wait for the checkbox to actually become checked
    ps_id = dummy_data_by_identifier_in_primary_source["ps-1"].stableTargetId
    primary_source_checkbox_input = primary_sources.get_by_test_id(
        f"primary-source-filter-{ps_id}"
    )
    expect(primary_source_checkbox_input).to_be_checked()

    # wait for search results to update
    expect(page.get_by_test_id("search-results-component")).to_be_visible()

    # verify exactly one checkbox is checked
    checked = primary_sources.get_by_role("checkbox", checked=True)
    expect(checked).to_have_count(1)

    # expect parameter change to be reflected in url
    page.wait_for_url(
        "**/?q=Une+activit%C3%A9+active&page=1&entityType=Activity&"
        "referenceFilterStrategy=had_primary_source&"
        f"hadPrimarySource={primary_source.stableTargetId}&referenceField="
    )


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_additional_titles_badge(
    base_url: str,
    search_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    # search for resources
    page = search_page
    page.goto(f"{base_url}?entityType=Resource")

    resource_r2 = dummy_data_by_identifier_in_primary_source["r-2"]
    assert isinstance(resource_r2, ExtractedResource)
    resource_r2_result = page.get_by_test_id(
        f"search-result-{resource_r2.stableTargetId}"
    )
    expect(resource_r2_result).to_be_visible()
    page.screenshot(path="tests_search_test_additional_titles_badge_on_load.png")
    first_title = resource_r2.title[0]

    # expect title is visible and there are additional titles for 'r2'
    expect(resource_r2_result).to_contain_text(first_title.value)
    expect(page.get_by_test_id("additional-titles-badge")).to_be_visible()
    # wait for the (re-rendering) result card to settle before scrolling, so the
    # non-retrying scroll action does not act on a detached element
    expect(page.get_by_test_id("additional-titles-badge")).to_have_text(
        build_ui_label_regex("components.titles.additional_titles")
    )
    page.get_by_test_id("additional-titles-badge").scroll_into_view_if_needed()
    page.screenshot(path="tests_search_test_additional_titles_badge_on_visible.png")

    # hover additional titles
    box = page.get_by_test_id("additional-titles-badge").bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=5)
    page.get_by_test_id("additional-titles-badge").hover()
    page.screenshot(path="tests_search_test_additional_titles_badge_on_hover.png")

    # check tooltip content
    tooltip = page.get_by_test_id("tooltip-additional-titles")
    expect(tooltip).to_be_visible()
    expect(tooltip).not_to_contain_text(first_title.value)
    for title in resource_r2.title[1:]:
        expect(tooltip).to_contain_text(title.value)

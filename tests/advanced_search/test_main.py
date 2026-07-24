import re
from collections.abc import Iterable

import pytest
from playwright.sync_api import Page, expect

from mex.common.backend_api.connector import (
    BackendApiConnector,
)
from mex.common.fields import (
    REFERENCE_FIELDS_BY_CLASS_NAME,
)
from mex.common.models import (
    MERGED_MODEL_CLASSES,
    MERGED_MODEL_CLASSES_BY_NAME,
    ActivityRuleSetResponse,
    AdditiveActivity,
    AnyExtractedModel,
    AnyMergedModel,
    ExtractedActivity,
    MergedPrimarySource,
    MergedResource,
)
from mex.common.models.organization import MergedOrganization
from mex.common.models.person import MergedPerson
from mex.common.transform import ensure_prefix


@pytest.fixture
def advanced_search_page(
    base_url: str,
    reader_user_page: Page,
    load_dummy_data: None,  # noqa: ARG001
) -> Page:
    page = reader_user_page
    page.goto(f"{base_url}/advanced-search")
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


search_result_item_regex = re.compile(r"search-result-(.*)")


def _make_screenshot(page: Page, name: str) -> None:
    page.screenshot(path=f"tests_advanced_search_test_main_{name}.png")


@pytest.mark.integration
def test_query_filter(advanced_search_page: Page) -> None:
    page = advanced_search_page

    _make_screenshot(page, "test_query_filter_init")
    query_input = page.get_by_test_id("filter-query")
    query_input.fill("Primary")
    query_input.press("Enter")
    _make_screenshot(page, "test_query_filter_search_by_enter_key")
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(2)

    query_input.fill("NonExistingString alsjhsdf sffsdk fsd")
    page.get_by_test_id("filter-query-submit").click()

    _make_screenshot(page, "test_query_filter_search_by_button")
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(0)


@pytest.mark.parametrize(
    ("entity_types", "expected_count"),
    [
        pytest.param([MergedPrimarySource.stemType], 4),
        pytest.param([MergedResource.stemType], 2),
        pytest.param([MergedPrimarySource.stemType, MergedResource.stemType], 6),
    ],
)
@pytest.mark.integration
def test_entity_types_filter(
    advanced_search_page: Page,
    entity_types: list[str],
    expected_count: int,
) -> None:
    page = advanced_search_page

    all_checkboxes = page.get_by_test_id("filter-entity-types").get_by_role("checkbox")
    assert all_checkboxes.count() == len(MERGED_MODEL_CLASSES_BY_NAME)
    for checkbox in all_checkboxes.all():
        checkbox.uncheck()

    _make_screenshot(page, "test_entity_types_filter_all_unchecked")

    for entity_type in entity_types:
        page.get_by_test_id(f"filter-entity-type-{entity_type}").check()

    page.screenshot(
        path=f"test_entity_types_filter_checked_{'_'.join(entity_types)}.png"
    )

    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(expected_count)


@pytest.mark.integration
def test_reference_filter_one_field_filter(
    advanced_search_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = advanced_search_page

    # Test one ref matching
    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-0-field").click()

    page.get_by_test_id(
        re.compile(
            r"ref-filter-value-label-select-item-(.+)-(.*)\"field\":\s*\"contact\"(.*)"
        )
    ).click()
    page.get_by_test_id("ref-filter-0-add-value").click()
    page.get_by_test_id("filter-ref-0-value-0-value").fill(
        extracted_activity.contact[1]
    )
    _make_screenshot(page, "test_reference_filter_one_field_filter_contact_set")
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(1)

    # Add another non existing contact value, should remain 1 match
    page.get_by_test_id("ref-filter-0-add-value").click()
    page.get_by_test_id("filter-ref-0-value-1-value").fill("AABBPxM98fOIPnPLr0AABB")
    _make_screenshot(
        page, "test_reference_filter_one_field_filter_additional_imaginary_contact"
    )
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(1)

    # Remove ref filter values and ref filter himself (one by one)
    page.get_by_test_id("filter-ref-0-value-1-remove").click()
    page.get_by_test_id("filter-ref-0-value-0-remove").click()
    page.get_by_test_id("ref-filter-0-remove").click()
    _make_screenshot(page, "test_reference_filter_one_field_filter_cleanup")
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(10)


@pytest.mark.parametrize(
    ("entity_types_filter"),
    [
        pytest.param([]),
        pytest.param([MergedPrimarySource]),
        pytest.param([MergedResource]),
        pytest.param([MergedPerson, MergedOrganization]),
    ],
)
@pytest.mark.integration
def test_reference_filter_field_dependency(
    advanced_search_page: Page, entity_types_filter: list[type[AnyMergedModel]]
) -> None:
    page = advanced_search_page

    def _get_unique_field_label_combinations(
        stem_types: Iterable[str] = [],
    ) -> set[str]:
        unique_ref_fields_with_label: set[str] = set()
        for merged_model_class in MERGED_MODEL_CLASSES:
            if not stem_types or merged_model_class.stemType in stem_types:
                for field in REFERENCE_FIELDS_BY_CLASS_NAME[
                    ensure_prefix(merged_model_class.stemType, "Extracted")
                ]:
                    unique_ref_fields_with_label.add(f"{field}")
        return unique_ref_fields_with_label

    # select the correct filters
    for type_filter in entity_types_filter:
        page.get_by_test_id(f"filter-entity-type-{type_filter.stemType}").check()

    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-0-field").click()

    unique_ref_fields_with_label = _get_unique_field_label_combinations(
        [x.stemType for x in entity_types_filter]
    )

    select_options = page.get_by_test_id(
        re.compile(r"ref-filter-value-label-select-item-.*")
    )
    expect(select_options).to_have_count(len(unique_ref_fields_with_label))


@pytest.mark.integration
def test_reference_filter_combinations(
    advanced_search_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = advanced_search_page

    # Add shared contact
    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-0-field").click()

    page.get_by_test_id(
        re.compile(
            r"ref-filter-value-label-select-item-(.+)-(.*)\"field\":\s*\"contact\"(.*)"
        )
    ).click()
    page.get_by_test_id("ref-filter-0-add-value").click()
    page.get_by_test_id("filter-ref-0-value-0-value").fill(
        extracted_activity.contact[0]
    )
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(3)
    _make_screenshot(page, "test_reference_filter_combinations_filter_contact_set")

    # Add unique responsibleUnit
    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-1-field").click()

    page.get_by_test_id(
        re.compile(
            r"ref-filter-value-label-select-item-(.+)-(.*)\"field\":\s*\"responsibleUnit\"(.*)"
        )
    ).click()
    page.get_by_test_id("ref-filter-1-add-value").click()
    page.get_by_test_id("filter-ref-1-value-0-value").fill(
        extracted_activity.responsibleUnit[0]
    )
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(1)
    _make_screenshot(
        page, "test_reference_filter_combinations_filter_contact_responsibleUnit_set"
    )


@pytest.mark.integration
def test_reference_filter_combinations_with_editor_added_involved_unit(
    advanced_search_page: Page,
    extracted_activity: ExtractedActivity,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = advanced_search_page
    ou1_id = dummy_data_by_identifier_in_primary_source["ou-1"].stableTargetId

    # Add involvedUnit to Activity1
    connector = BackendApiConnector.get()
    rules = ActivityRuleSetResponse(
        stableTargetId=extracted_activity.stableTargetId,
        additive=AdditiveActivity(involvedUnit=[ou1_id]),
    )
    connector.ingest([rules])

    # Add shared contact
    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-0-field").click()

    page.get_by_test_id(
        re.compile(
            r"ref-filter-value-label-select-item-(.+)-(.*)\"field\":\s*\"contact\"(.*)"
        )
    ).click()
    page.get_by_test_id("ref-filter-0-add-value").click()
    page.get_by_test_id("filter-ref-0-value-0-value").fill(
        extracted_activity.contact[0]
    )
    page.wait_for_timeout(5000)
    _make_screenshot(
        page,
        "test_reference_filter_combinations_with_editor_added_involved_unit_contact_set",
    )
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(3)

    # Add unique responsibleUnit
    page.get_by_test_id("add-reference-filter-button").click()
    page.get_by_test_id("ref-filter-1-field").click()

    page.get_by_test_id(
        re.compile(
            r"ref-filter-value-label-select-item-(.+)-(.*)\"field\":\s*\"involvedUnit\"(.*)"
        )
    ).click()
    page.get_by_test_id("ref-filter-1-add-value").click()
    page.get_by_test_id("filter-ref-1-value-0-value").fill(ou1_id)
    page.wait_for_timeout(5000)
    _make_screenshot(
        page,
        "test_reference_filter_combinations_with_editor_added_involved_unit_contact_involvedUnit_set",
    )
    expect(page.get_by_test_id(search_result_item_regex)).to_have_count(1)

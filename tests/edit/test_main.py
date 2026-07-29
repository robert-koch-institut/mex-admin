import re
from typing import Literal

import pytest
from playwright.sync_api import Page, expect

from mex.admin.rules.transform import get_required_mergeable_field_names
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.fields import (
    MERGEABLE_FIELDS_BY_CLASS_NAME,
    REQUIRED_FIELDS_BY_CLASS_NAME,
)
from mex.common.models import (
    MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
    ActivityRuleSetRequest,
    ActivityRuleSetResponse,
    AdditiveActivity,
    AdditiveContactPoint,
    AnyExtractedModel,
    ContactPointRuleSetRequest,
    ExtractedActivity,
    ExtractedOrganizationalUnit,
    ExtractedPrimarySource,
    SubtractiveActivity,
    WorkflowActivity,
)
from mex.common.transform import ensure_prefix
from mex.common.types import (
    ActivityType,
    Identifier,
    PublishingTarget,
    Text,
    TextLanguage,
    Theme,
)


@pytest.fixture
def edit_page(
    base_url: str,
    writer_user_page: Page,
    extracted_activity: ExtractedActivity,
    load_dummy_data: None,  # noqa: ARG001
) -> Page:
    page = writer_user_page
    page.goto(f"{base_url}/item/{extracted_activity.stableTargetId}")
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


@pytest.fixture
def load_superseded_by_entites(
    extracted_activity: ExtractedActivity,
) -> list[ExtractedActivity]:
    connector = BackendApiConnector.get()

    activity_2 = ExtractedActivity(
        abstract=[],
        contact=extracted_activity.contact,
        hadPrimarySource=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
        identifierInPrimarySource="supersededBy-1",
        responsibleUnit=extracted_activity.responsibleUnit,
        shortName=["A2-S1"],
        title=[Text(value="Aktivität 2 Superseded 1", language=TextLanguage.DE)],
    )

    activity_3 = ExtractedActivity(
        abstract=[],
        contact=extracted_activity.contact,
        hadPrimarySource=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
        identifierInPrimarySource="supersededBy-2",
        responsibleUnit=extracted_activity.responsibleUnit,
        shortName=["A3-S2"],
        title=[Text(value="Aktivität 3 Superseded 2", language=TextLanguage.DE)],
    )

    connector.ingest(
        [
            activity_2,
            activity_3,
            ActivityRuleSetResponse(
                additive=AdditiveActivity(
                    supersededBy=extracted_activity.stableTargetId
                ),
                stableTargetId=activity_2.stableTargetId,
            ),
            ActivityRuleSetResponse(
                additive=AdditiveActivity(
                    supersededBy=extracted_activity.stableTargetId
                ),
                stableTargetId=activity_3.stableTargetId,
            ),
        ]
    )  # type: ignore[type-var]

    return [activity_2, activity_3]


@pytest.fixture
def load_delete_reset_data(
    dummy_data: list[AnyExtractedModel],
) -> dict[Literal["delete", "reset"] | None, str]:
    connector = BackendApiConnector.get()
    connector.ingest(dummy_data)

    delete_resp = connector.create_rule_set(
        ContactPointRuleSetRequest(
            additive=AdditiveContactPoint(email=["DELETE_ME@test.de"])
        )
    )
    cp1: AnyExtractedModel = next(
        x for x in dummy_data if x.identifierInPrimarySource == "cp-1"
    )
    connector.update_rule_set(
        cp1.stableTargetId,
        ContactPointRuleSetRequest(
            additive=AdditiveContactPoint(email=["another_email@test.com"])
        ),
    )

    ou1: AnyExtractedModel = next(
        x for x in dummy_data if x.identifierInPrimarySource == "ou-1"
    )

    return {
        "delete": delete_resp.stableTargetId,
        "reset": cp1.stableTargetId,
        None: ou1.stableTargetId,
    }


@pytest.mark.integration
def test_edit_page_delete_reset_button(
    base_url: str,
    writer_user_page: Page,
    load_delete_reset_data: dict[Literal["delete", "reset"] | None, str],
) -> None:
    page = writer_user_page

    def _navigate(stable_id: str) -> None:
        page.goto(f"{base_url}/item/{stable_id}")
        page_body = page.get_by_test_id("page-body")
        expect(page_body).to_be_visible()

    _navigate(load_delete_reset_data[None])
    expect(page.get_by_test_id("delete-reset-dialog-button")).not_to_be_visible()

    reset_id = load_delete_reset_data["reset"]
    _navigate(reset_id)
    dialog_button = page.get_by_test_id("delete-reset-dialog-button")
    expect(dialog_button).to_be_visible()

    # cancelling the dialog must close it and leave the rules untouched
    dialog_button.click()
    confirm_button = page.get_by_test_id("delete-reset-button")
    expect(confirm_button).to_be_visible()
    page.get_by_test_id("delete-reset-cancel-button").click()
    expect(confirm_button).not_to_be_visible()
    expect(dialog_button).to_be_visible()

    dialog_button.click()
    page.get_by_test_id("delete-reset-button").click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_delete_reset_button-reset_clicked.png"
    )
    page.wait_for_url(f"{base_url}/item/{reset_id}")
    expect(page.locator(".editor-toast")).to_be_visible()
    expect(page.get_by_test_id("delete-reset-dialog-button")).not_to_be_visible()

    delete_id = load_delete_reset_data["delete"]
    _navigate(delete_id)
    dialog_button = page.get_by_test_id("delete-reset-dialog-button")
    expect(dialog_button).to_be_visible()
    dialog_button.click()
    page.get_by_test_id("delete-reset-button").click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_delete_reset_button-delete_clicked.png"
    )
    page.wait_for_url(f"{base_url}/")
    expect(page.locator(".editor-toast")).to_be_visible()


@pytest.mark.integration
def test_edit_page_updates_nav_bar(edit_page: Page) -> None:
    page = edit_page
    nav_bar = page.get_by_test_id("nav-bar")
    expect(nav_bar).to_be_visible()
    page.screenshot(path="tests_edit_test_main-test_edit_page_updates_nav_bar.png")
    nav_item = nav_bar.get_by_test_id("nav-item-/item/[item_id]")
    expect(nav_item).to_have_class(re.compile(r"(^|\s)nav-item-active(\s|$)"))


@pytest.mark.integration
def test_edit_page_renders_heading(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = edit_page
    heading = page.get_by_test_id("edit-heading")
    expect(heading).to_be_visible()
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_heading.png")
    expect(heading).to_have_text(re.compile(r"Aktivität 1\s*DE"))

    connector = BackendApiConnector.get()
    connector.update_rule_set(
        extracted_activity.stableTargetId,
        ActivityRuleSetRequest(
            additive=AdditiveActivity(
                title=[Text(value="New title who dis?", language=None)]
            ),
            subtractive=SubtractiveActivity(
                title=[Text(value="Aktivität 1", language=TextLanguage.DE)],
            ),
        ),
    )
    page.reload()
    heading = page.get_by_test_id("edit-heading")
    expect(heading).to_be_visible()
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_new_heading.png")
    expect(heading).to_have_text(re.compile(r"New title*"))


@pytest.mark.integration
def test_edit_page_renders_fields(edit_page: Page) -> None:
    page = edit_page
    funding_program = page.get_by_test_id("field-fundingProgram-name")
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_fields.png")
    expect(funding_program).to_be_visible()
    # identifierInPrimarySource is NOT in MERGEABLE_FIELDS_BY_CLASS_NAME and has to be added
    expect(page.get_by_role("row")).to_have_count(
        len(
            set(MERGEABLE_FIELDS_BY_CLASS_NAME["ExtractedActivity"])
            | set(MERGEABLE_FIELDS_BY_CLASS_NAME["AdditiveActivity"])
        )
        + 1
    )


@pytest.mark.integration
def test_edit_page_renders_primary_sources(
    edit_page: Page,
    extracted_activity: ExtractedActivity,
    dummy_data_by_stable_target_id: dict[Identifier, AnyExtractedModel],
) -> None:
    page = edit_page
    had_primary_source = dummy_data_by_stable_target_id[
        extracted_activity.hadPrimarySource
    ]
    assert type(had_primary_source) is ExtractedPrimarySource

    primary_source = page.get_by_test_id(
        f"primary-source-title-{extracted_activity.hadPrimarySource}-name"
    )
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_primary_sources.png"
    )
    expect(primary_source).to_be_visible()
    expect(primary_source).to_contain_text(had_primary_source.title[0].value)
    link = primary_source.get_by_role("link")
    expect(link).to_have_attribute(
        "href", f"/item/{extracted_activity.hadPrimarySource}"
    )


@pytest.mark.integration
def test_edit_page_renders_text(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = edit_page
    text = page.get_by_test_id(f"value-title-{extracted_activity.hadPrimarySource}-0")
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_text.png")
    expect(text).to_be_visible()
    expect(text).to_contain_text("Aktivität 1")  # text value
    expect(text).to_contain_text(TextLanguage.DE.name)  # language badge


@pytest.mark.integration
def test_edit_page_renders_vocab(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = edit_page
    theme = page.get_by_test_id(f"value-theme-{extracted_activity.hadPrimarySource}-0")
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_vocab.png")
    expect(theme).to_be_visible()
    expect(theme).to_contain_text(
        Theme["INFECTIOUS_DISEASES_AND_EPIDEMIOLOGY"].name
    )  # theme value
    expect(theme).to_contain_text("Theme")  # vocabulary name


@pytest.mark.integration
def test_edit_page_renders_link(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = edit_page
    website_0 = page.get_by_test_id(
        f"value-website-{extracted_activity.hadPrimarySource}-0"
    )
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_link.png")
    expect(website_0).to_be_visible()
    link_0 = website_0.get_by_role("link")
    expect(link_0).to_contain_text("Activity Homepage")  # link title
    expect(link_0).to_have_attribute("href", "https://activity-1")  # link href
    expect(link_0).to_have_attribute("target", "_blank")  # external link

    website_1 = page.get_by_test_id(
        f"value-website-{extracted_activity.hadPrimarySource}-1"
    )
    expect(website_1).to_be_visible()
    link_1 = website_1.get_by_role("link")
    expect(link_1).to_contain_text("https://activity-homepage-1")  # link title
    expect(link_1).to_have_attribute("href", "https://activity-homepage-1")  # link href
    expect(link_1).to_have_attribute("target", "_blank")  # external link


@pytest.mark.integration
def test_edit_page_renders_temporal(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    page = edit_page
    start = page.get_by_test_id(f"value-start-{extracted_activity.hadPrimarySource}-0")
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_temporal.png")
    expect(start).to_be_visible()
    expect(start).to_contain_text("1999-12-24")  # temporal localization


@pytest.mark.integration
def test_edit_page_resolves_identifier(
    edit_page: Page,
    dummy_data_by_stable_target_id: dict[Identifier, AnyExtractedModel],
    extracted_activity: ExtractedActivity,
) -> None:
    page = edit_page
    extracted_organizational_unit = dummy_data_by_stable_target_id[
        extracted_activity.contact[1]
    ]
    assert type(extracted_organizational_unit) is ExtractedOrganizationalUnit

    contact = page.get_by_test_id(
        f"value-contact-{extracted_activity.hadPrimarySource}-1"
    )
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_identifier.png")
    expect(contact).to_be_visible()
    link = contact.get_by_role("link")
    expect(link).to_contain_text(
        extracted_organizational_unit.shortName[0].value
    )  # resolved short name of unit
    expect(link).to_have_attribute(
        "href",
        f"/item/{extracted_activity.contact[1]}",  # link href
    )
    expect(link).not_to_have_attribute("target", "_blank")  # internal link


@pytest.mark.parametrize(
    ("switch_id"),
    [
        (r"switch-abstract-{had_primary_source}"),
        (r"switch-abstract-{had_primary_source}-1"),
        (r"switch-website-{had_primary_source}-1"),
    ],
    ids=["toggle primary source", "toggle value", "toggle link without text"],
)
@pytest.mark.integration
def test_edit_page_switch_roundtrip(
    edit_page: Page, extracted_activity: ExtractedActivity, switch_id: str
) -> None:
    switch_id = switch_id.format(had_primary_source=extracted_activity.hadPrimarySource)
    test_id = f"tests_edit_test_main-test_edit_page_switch_roundtrip_{switch_id}"
    page = edit_page

    # verify initial state: toggle is enabled
    switch = page.get_by_test_id(switch_id)
    expect(switch).to_have_count(1)
    switch.scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-onload.png")
    expect(switch).to_be_visible()
    expect(switch).to_have_attribute("data-state", "checked")

    # click on the toggle to disable the primary source / specific value
    switch.click()
    expect(switch).to_have_attribute("data-state", "unchecked")
    page.screenshot(path=f"{test_id}-disabled.png")

    # click on the save button and verify the toast
    submit = page.get_by_test_id("submit-button")
    submit.scroll_into_view_if_needed()
    submit.click()
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    page.screenshot(path=f"{test_id}-toast_1.png")

    # force a page reload
    page.reload()

    # verify the state after first saving: toggle is off
    switch = page.get_by_test_id(switch_id)
    expect(switch).to_have_count(1)
    switch.scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-reload_1.png")
    expect(switch).to_be_visible()
    expect(switch).to_have_attribute("data-state", "unchecked")

    # click on the toggle to re-enable the primary source / specific value
    switch.click()
    expect(switch).to_have_attribute("data-state", "checked")
    page.screenshot(path=f"{test_id}-enabled.png")

    # click on the save button again and verify the toast again
    submit = page.get_by_test_id("submit-button")
    submit.scroll_into_view_if_needed()
    submit.click()
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    page.screenshot(path=f"{test_id}-toast_2.png")

    # force a page reload again
    page.reload()

    # verify the state after second saving: toggle is on again
    switch = page.get_by_test_id(switch_id)
    page.screenshot(path=f"{test_id}-reload_2.png")
    expect(switch).to_have_count(1)
    expect(switch).to_be_visible()
    expect(switch).to_have_attribute("data-state", "checked")


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
@pytest.mark.parametrize(
    ("field_name", "switch_count"),
    [
        ("identifierInPrimarySource", 0),
        ("website", 3),
    ],
)
def test_field_switches_behavior(
    base_url: str,
    writer_user_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
    field_name: str,
    switch_count: int,
) -> None:
    page = writer_user_page
    item = dummy_data_by_identifier_in_primary_source["a-1"]

    page.goto(f"{base_url}/item/{item.stableTargetId}")
    expect(page.get_by_test_id("page-body")).to_be_visible()

    field = page.get_by_test_id(f"field-{field_name}")
    expect(field).to_be_visible()

    switches = field.locator("[data-testid^='switch-']")
    expect(switches).to_have_count(switch_count)


@pytest.mark.integration
def test_edit_page_renders_new_additive_button(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-fundingProgram-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_new_additive_button.png"
    )
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    additive_rule_input = page.get_by_test_id("additive-rule-fundingProgram-0-text")
    additive_rule_input.scroll_into_view_if_needed()
    expect(additive_rule_input).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_remove_additive_button(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-fundingProgram-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_remove_additive_button.png"
    )
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    remove_additive_rule_button = page.get_by_test_id(
        "additive-rule-fundingProgram-0-remove-button"
    )
    expect(remove_additive_rule_button).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_text_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-shortName-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_text_input.png")

    text_input = page.get_by_test_id("additive-rule-shortName-0-text")
    expect(text_input).to_be_visible()
    badge_select = page.get_by_test_id("additive-rule-shortName-0-badge")
    expect(badge_select).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_textarea_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-alternativeTitle-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_textarea_input.png"
    )

    textarea_input = page.get_by_test_id("additive-rule-alternativeTitle-0-text")
    expect(textarea_input).to_be_visible()
    assert textarea_input.evaluate("el => el.tagName.toLowerCase()") == "textarea"

    badge_select = page.get_by_test_id("additive-rule-alternativeTitle-0-badge")
    expect(badge_select).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_identifier_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-involvedUnit-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_identifier_input.png"
    )

    identifier_input = page.get_by_test_id("additive-rule-involvedUnit-0-identifier")
    expect(identifier_input).to_be_visible()


@pytest.mark.integration
def test_edit_page_resolves_additive_identifier(
    edit_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-involvedUnit-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    organizational_unit = dummy_data_by_identifier_in_primary_source["ou-1"]
    assert isinstance(organizational_unit, ExtractedOrganizationalUnit)
    identifier_input = page.get_by_test_id("additive-rule-involvedUnit-0-identifier")
    expect(identifier_input).to_be_visible()
    identifier_input.fill(organizational_unit.stableTargetId)
    edit_button = page.get_by_test_id(
        f"edit-toggle-involvedUnit-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}-0"
    )
    edit_button.click()

    # verify identifier is correctly rendered
    identifier_card = page.get_by_test_id("additive-rule-involvedUnit-0")
    rendered_identifier = identifier_card.get_by_role(
        "link", name=organizational_unit.shortName[0].value
    )
    expect(rendered_identifier).to_have_count(1)
    expect(rendered_identifier.first).to_have_attribute(
        "href", f"/item/{organizational_unit.stableTargetId}"
    )

    # assert raw identifier value is retained
    edit_button.click()
    identifier_input = page.get_by_test_id("additive-rule-involvedUnit-0-identifier")
    expect(identifier_input).to_have_attribute(
        "value", organizational_unit.stableTargetId
    )


@pytest.mark.integration
def test_edit_page_renders_link_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-website-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(path="tests_edit_test_main-test_edit_page_renders_link_input.png")

    text_input = page.get_by_test_id("additive-rule-website-0-text")
    expect(text_input).to_be_visible()
    badge_select = page.get_by_test_id("additive-rule-website-0-badge")
    expect(badge_select).to_be_visible()
    href_input = page.get_by_test_id("additive-rule-website-0-href")
    expect(href_input).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_vocabulary_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-activityType-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_vocabulary_input_closed.png"
    )

    badge_select = page.get_by_test_id("additive-rule-activityType-0-badge")
    expect(badge_select).to_be_visible()
    expect(
        page.get_by_text(ActivityType["THIRD_PARTY_FUNDED_PROJECT"].name)
    ).to_be_visible()
    badge_select.focus()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_vocabulary_input_open.png"
    )
    page.keyboard.press("Enter")
    page.locator("body").focus()
    expect(
        page.get_by_text(ActivityType["INTERNAL_PROJECT_ENDEAVOR"].name)
    ).to_be_visible()


@pytest.mark.integration
def test_edit_page_renders_temporal_input(edit_page: Page) -> None:
    page = edit_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-end-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_temporal_input_closed.png"
    )

    badge_select = page.get_by_test_id("additive-rule-end-0-badge")
    expect(badge_select).to_be_visible()
    expect(page.get_by_text("year")).to_be_visible()
    badge_select.click()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_temporal_input_open.png"
    )
    precision_options = page.get_by_role("group").get_by_role("option")
    expect(precision_options).to_have_count(3)
    expect(precision_options).to_have_text(["year", "month", "day"])


@pytest.mark.integration
def test_edit_page_additive_rule_roundtrip(
    edit_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    page = edit_page
    test_id = "tests_edit_test_main-test_edit_page_additive_rule_roundtrip"

    # click button for new additive rule on contact field
    new_additive_button = page.get_by_test_id(
        f"new-additive-contact-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-on_load.png")
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    # fill a string into the additive rule input
    input_id = "additive-rule-contact-0-identifier"
    additive_rule_input = page.get_by_test_id(input_id)
    expect(additive_rule_input).to_be_visible()
    contact_point_2 = dummy_data_by_identifier_in_primary_source["cp-2"]
    rule_value = contact_point_2.stableTargetId
    additive_rule_input.fill(rule_value)
    page.screenshot(path=f"{test_id}-input-filled.png")

    # save the rule-set
    submit_button = page.get_by_test_id("submit-button")
    submit_button.scroll_into_view_if_needed()
    submit_button.click()

    # click on the save button and verify the toast
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")
    page.screenshot(path=f"{test_id}-toast.png")

    # force a page reload
    page.reload()

    # verify the state after first saving: additive rule is present
    rendered_input_id = "additive-rule-contact-0"
    additive_rule_rendered = page.get_by_test_id(rendered_input_id)
    expect(additive_rule_rendered).to_have_count(1)
    additive_rule_rendered.scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-reload_1.png")
    expect(additive_rule_rendered).to_be_visible()

    # click edit button
    edit_button = page.get_by_test_id(
        f"edit-toggle-contact-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}-0"
    )
    edit_button.scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-on_load.png")
    expect(edit_button).to_be_visible()
    edit_button.click()

    # verify content of additive rule
    additive_rule_input = page.get_by_test_id(input_id)
    expect(additive_rule_input).to_be_visible()
    expect(additive_rule_input).to_have_attribute("value", rule_value)

    # now remove the additive rule for a full roundtrip
    remove_additive_rule_button = page.get_by_test_id(
        "additive-rule-contact-0-remove-button"
    )
    expect(remove_additive_rule_button).to_be_visible()
    remove_additive_rule_button.click()

    # check the rule input is gone
    additive_rule_rendered = page.get_by_test_id(rendered_input_id)
    expect(additive_rule_rendered).to_have_count(0)

    # click on the save button and force a page reload again
    submit_button = page.get_by_test_id("submit-button")
    submit_button.scroll_into_view_if_needed()
    submit_button.click()
    page.wait_for_timeout(30000)  # wait for save operation
    page.reload()

    # check the rule input is still gone
    page.get_by_test_id("field-contact").scroll_into_view_if_needed()
    page.screenshot(path=f"{test_id}-reload_2.png")
    additive_rule_rendered = page.get_by_test_id(rendered_input_id)
    expect(additive_rule_rendered).to_have_count(0)


@pytest.mark.integration
def test_required_fields_red_asterisk(
    edit_page: Page, extracted_activity: ExtractedActivity
) -> None:
    expected_required_fields = [
        "contact",
        "responsibleUnit",
        "title",
    ]
    expected_optional_fields = [
        "abstract",
        "activityType",
        "alternativeTitle",
        "documentation",
        "end",
        "externalAssociate",
        "funderOrCommissioner",
        "fundingProgram",
        "involvedPerson",
        "involvedUnit",
        "isPartOfActivity",
        "publication",
        "relatedActivity",
        "shortName",
        "start",
        "succeeds",
        "supersededBy",
        "theme",
        "website",
    ]

    required_mergeable_fields = get_required_mergeable_field_names(extracted_activity)
    assert set(required_mergeable_fields) == set(expected_required_fields)

    merged_type = ensure_prefix(extracted_activity.stemType, "Merged")
    required_fields = set(REQUIRED_FIELDS_BY_CLASS_NAME[merged_type])
    mergeable_fields = set(MERGEABLE_FIELDS_BY_CLASS_NAME[merged_type])
    optional_mergeable_fields = sorted(mergeable_fields - required_fields)
    assert set(optional_mergeable_fields) == set(expected_optional_fields)

    for field_name in expected_required_fields + expected_optional_fields:
        field = edit_page.get_by_test_id(f"field-{field_name}-name")
        expect(field).to_be_visible()

        asterisk = field.get_by_text("*", exact=True)
        if field_name in expected_required_fields:
            expect(asterisk).to_be_visible()
            expect(asterisk).to_have_css("color", "rgb(255, 99, 71)")
        else:
            expect(asterisk).to_have_count(0)


@pytest.fixture
def workflow_forbidden_invenio(extracted_activity: ExtractedActivity) -> None:
    connector = BackendApiConnector.get()
    connector.ingest(
        [
            ActivityRuleSetResponse(
                stableTargetId=extracted_activity.stableTargetId,
                workflow=WorkflowActivity(
                    forbiddenPublishingTarget=[PublishingTarget.INVENIO]
                ),
            )
        ]
    )


@pytest.mark.integration
def test_all_publish_targets_rendered(edit_page: Page) -> None:
    for target in PublishingTarget:
        expect(
            edit_page.get_by_test_id(f"publish-target-{target.value}")
        ).to_be_visible()


@pytest.mark.integration
def test_no_invenio_publish_target_to_publish_invenio(
    edit_page: Page,
    extracted_activity: ExtractedActivity,
    workflow_forbidden_invenio: None,  # noqa: ARG001
) -> None:
    page = edit_page

    # wait for fields(rule is loaded when fields are)
    expect(page.get_by_test_id("field-abstract")).to_be_visible()
    page.screenshot(
        path="tests_edit_test_no_invenio_publish_target_to_publish_invenio.png"
    )

    expect(page.get_by_test_id("publish-targets")).to_be_visible()
    expect(
        page.get_by_test_id(
            f"publish-target-{PublishingTarget.INVENIO.value}"
        ).get_by_role("switch")
    ).not_to_be_checked()
    expect(
        page.get_by_test_id(
            f"publish-target-{PublishingTarget.DATENKOMPASS.value}"
        ).get_by_role("switch")
    ).to_be_checked()

    page.get_by_test_id(f"publish-target-{PublishingTarget.INVENIO.value}").get_by_role(
        "switch"
    ).click()

    page.screenshot(
        path="tests_edit_test_no_invenio_publish_target_to_publish_invenio_clicked.png"
    )
    page.get_by_test_id("submit-button").click()
    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")

    expect(
        page.get_by_test_id(
            f"publish-target-{PublishingTarget.INVENIO.value}"
        ).get_by_role("switch")
    ).to_be_checked()
    page.screenshot(
        path="tests_edit_test_no_invenio_publish_target_to_publish_invenio_saved.png"
    )

    rule_set = BackendApiConnector.get().get_rule_set(extracted_activity.stableTargetId)
    assert rule_set.workflow.forbiddenPublishingTarget == []


@pytest.mark.integration
def test_edit_page_submit_button_disabled_while_submitting(edit_page: Page) -> None:
    edit_page.get_by_test_id(
        f"new-additive-alternativeTitle-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    edit_page.get_by_test_id("additive-rule-alternativeTitle-0-text").fill(
        "new alternative title"
    )
    # check default state
    submit_button = edit_page.get_by_test_id("submit-button")
    initial_text = submit_button.text_content()
    initial_text = initial_text or ""
    expect(submit_button).to_have_text(initial_text)
    expect(submit_button).not_to_be_disabled()

    # submit item
    submit_button.click()
    expect(submit_button).not_to_have_text(initial_text)
    expect(submit_button).to_be_disabled()

    # check if back in default state after saving
    edit_page.wait_for_timeout(30000)
    expect(submit_button).to_have_text(initial_text)
    expect(submit_button).not_to_be_disabled()


@pytest.mark.parametrize(
    ("locale_id", "field_name", "expected_field_label"),
    [
        pytest.param(
            "de",
            "alternativeTitle",
            "Alternativtitel",
            id="de:alternativeTitle",
        ),
        pytest.param(
            "en",
            "alternativeTitle",
            "Alternative title",
            id="en:alternativeTitle",
        ),
        pytest.param(
            "de",
            "abstract",
            "Kurzbeschreibung",
            id="de:abstract",
        ),
        pytest.param(
            "en",
            "abstract",
            "Abstract",
            id="en:abstract",
        ),
    ],
)
@pytest.mark.integration
def test_edit_page_additive_add_remove_button_text_translation(
    edit_page: Page, locale_id: str, field_name: str, expected_field_label: str
) -> None:
    edit_page.get_by_test_id("language-switcher").click()
    edit_page.get_by_test_id(f"language-switcher-menu-item-{locale_id}").click()
    add_alt_title_btn = edit_page.get_by_test_id(
        f"new-additive-{field_name}-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    expect(add_alt_title_btn).to_have_text(re.compile(f"{expected_field_label}"))
    add_alt_title_btn.click()
    expect(
        edit_page.get_by_test_id(f"additive-rule-{field_name}-0-remove-button")
    ).to_have_text(re.compile(rf"[\w\s]*{expected_field_label}[\w\s]*"))


@pytest.mark.integration
def test_edit_page_discard_changes_button_roundtrip(
    edit_page: Page,
    extracted_activity: ExtractedActivity,
) -> None:
    discard_dialog_button = edit_page.get_by_test_id("discard-changes-dialog-button")
    expect(discard_dialog_button).not_to_be_visible()

    # add/remove new alternative title and check button visibility
    edit_page.get_by_test_id(
        f"new-additive-alternativeTitle-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    edit_page.get_by_test_id("additive-rule-alternativeTitle-0-text").fill(
        "new added alternative title"
    )
    expect(discard_dialog_button).to_be_visible()
    edit_page.get_by_test_id("additive-rule-alternativeTitle-0-remove-button").click()
    expect(discard_dialog_button).not_to_be_visible()

    # add new alternative title, save and check button visibility
    edit_page.get_by_test_id(
        f"new-additive-alternativeTitle-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    edit_page.get_by_test_id("additive-rule-alternativeTitle-0-text").fill(
        "new saved added alternative title"
    )
    expect(discard_dialog_button).to_be_visible()
    edit_page.get_by_test_id("submit-button").click()
    expect(discard_dialog_button).not_to_be_visible()

    # toggle existing value and check button visibility
    edit_page.screenshot(
        path="tests_edit_test_main-test_discard_changes_button_roundtrip-ps-abstract-before-click.png"
    )
    edit_page.get_by_test_id(
        f"switch-abstract-{extracted_activity.hadPrimarySource}-0"
    ).click()
    expect(discard_dialog_button).to_be_visible()
    edit_page.get_by_test_id(
        f"switch-abstract-{extracted_activity.hadPrimarySource}-0"
    ).click()
    expect(discard_dialog_button).not_to_be_visible()

    # toggle primary source and check button visibility
    edit_page.get_by_test_id(
        f"switch-abstract-{extracted_activity.hadPrimarySource}"
    ).click()
    expect(discard_dialog_button).to_be_visible()
    edit_page.get_by_test_id(
        f"switch-abstract-{extracted_activity.hadPrimarySource}"
    ).click()
    expect(discard_dialog_button).not_to_be_visible()

    # do changes navigate away, come back and check if changes still present, discard change
    edit_page.get_by_test_id(
        f"new-additive-shortName-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    shortname_text = edit_page.get_by_test_id("additive-rule-shortName-0-text")
    shortname_text.fill("shortNameChanges")
    # give the state some time to sync changes into local storage
    edit_page.wait_for_timeout(1_000)
    navigate_back_url = edit_page.url
    # navigate away with a full page unload (no network needed), then come back
    edit_page.goto("about:blank")
    assert edit_page.url == "about:blank"
    edit_page.goto(navigate_back_url, wait_until="load")
    expect(discard_dialog_button).to_be_visible()
    expect(shortname_text).to_have_value("shortNameChanges")

    # cancelling the dialog must close it and keep the changes
    discard_dialog_button.click()
    discard_button = edit_page.get_by_test_id("discard-changes-button")
    expect(discard_button).to_be_visible()
    edit_page.get_by_test_id("discard-changes-cancel-button").click()
    expect(discard_button).not_to_be_visible()
    expect(shortname_text).to_have_value("shortNameChanges")

    discard_dialog_button.click()
    edit_page.get_by_test_id("discard-changes-button").click()
    expect(
        edit_page.get_by_test_id("additive-rule-shortName-0-text")
    ).not_to_be_visible()
    expect(discard_dialog_button).not_to_be_visible()


@pytest.mark.integration
def test_superseded_by_backward_visibility(
    edit_page: Page,
    load_superseded_by_entites: list[ExtractedActivity],
) -> None:
    superseded_by_backward = edit_page.get_by_test_id("field-supersededBy-backward")
    superseded_by_backward.is_visible()
    superseded_by_backward.scroll_into_view_if_needed()
    edit_page.reload()
    edit_page.wait_for_timeout(20_000)
    edit_page.screenshot(
        path="tests_edit_test_main-test_superseded_by_backward_visibility.png"
    )

    search_results = superseded_by_backward.get_by_test_id(
        re.compile(r"search-result-.*")
    )
    expect(search_results).to_have_count(2)

    for item in load_superseded_by_entites:
        superseded_by_backward.get_by_test_id(
            f"search-result-{item.stableTargetId}"
        ).is_visible()


@pytest.mark.integration
def test_edit_page_renders_not_found_for_unknown_identifier(
    base_url: str, edit_page: Page
) -> None:
    # navigating away from a loaded item must not leak its stem type into the
    # next item, otherwise an unknown identifier opens an empty editor
    page = edit_page
    expect(page.get_by_test_id("edit-heading")).to_be_visible()

    page.goto(f"{base_url}/item/{Identifier.generate()}")

    load_error = page.get_by_test_id("edit-load-error")
    expect(load_error).to_be_visible()
    page.screenshot(
        path="tests_edit_test_main-test_edit_page_renders_not_found_for_unknown_identifier.png"
    )
    expect(page.get_by_test_id("edit-heading")).not_to_be_visible()

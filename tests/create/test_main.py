import re
from typing import TypedDict

import pytest
from playwright.sync_api import Locator, Page, expect

from mex.common.backend_api.connector import BackendApiConnector
from mex.common.fields import MERGEABLE_FIELDS_BY_CLASS_NAME
from mex.common.models import (
    MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
    AnyExtractedModel,
)
from tests.conftest import build_ui_label_regex

url_regex = re.compile(r"/create/(\w+)")


@pytest.fixture
def create_page(
    base_url: str,
    writer_user_page: Page,
    load_dummy_data: None,  # noqa: ARG001
) -> Page:
    page = writer_user_page
    page.goto(f"{base_url}/create")
    expect(page).to_have_url(url_regex)
    page_body = page.get_by_test_id("page-body")
    expect(page_body).to_be_visible()
    return page


class DraftPage(TypedDict):
    page: Page
    draft_id: str
    discard_button: Locator
    draft_menu_trigger: Locator
    draft_menu_item: Locator
    discard_dialog_button: Locator


@pytest.fixture
def draft_create_page(
    create_page: Page,
) -> DraftPage:
    create_page.evaluate("() => window.localStorage.clear()")

    match = re.search(url_regex, create_page.url)
    assert match
    draft_id = match.group(1)
    expect(create_page.get_by_test_id("page-body")).to_be_visible()
    discard_button = create_page.get_by_test_id("discard-draft-button")
    draft_menu_trigger = create_page.get_by_test_id("draft-menu-trigger")
    discard_draft_dialog_button = create_page.get_by_test_id(
        "discard-draft-dialog-button"
    )
    expect(discard_button).not_to_be_visible()
    expect(draft_menu_trigger).not_to_be_visible()
    expect(discard_draft_dialog_button).not_to_be_visible()

    return DraftPage(
        page=create_page,
        draft_menu_trigger=draft_menu_trigger,
        draft_id=draft_id,
        discard_dialog_button=discard_draft_dialog_button,
        discard_button=discard_button,
        draft_menu_item=create_page.get_by_test_id(f"draft-{draft_id}-menu-item"),
    )


@pytest.mark.integration
def test_create_page_updates_nav_bar(create_page: Page) -> None:
    page = create_page
    nav_bar = page.get_by_test_id("nav-bar")
    page.screenshot(path="tests_create_test_main-test_create_page_updates_nav_bar.png")
    expect(nav_bar).to_be_visible()
    nav_item = nav_bar.get_by_test_id("nav-item-/create")
    expect(nav_item).to_contain_text(
        build_ui_label_regex("layout.nav_bar.create_navitem")
    )
    expect(nav_item).to_have_class(re.compile(r"(^|\s)nav-item-active(\s|$)"))


@pytest.mark.integration
def test_create_page_renders_heading(create_page: Page) -> None:
    page = create_page
    heading = page.get_by_test_id("create-heading")
    page.screenshot(path="tests_create_test_main-test_create_page_renders_heading.png")
    expect(heading).to_be_visible()


@pytest.mark.integration
def test_create_page_renders_fields(create_page: Page) -> None:
    page = create_page
    page.get_by_test_id("entity-type-select").click()
    page.get_by_test_id(re.compile(r"value-label-select-item-(.+)-Resource")).click()
    page.screenshot(
        path="tests_create_test_main-test_create_page_renders_fields_select.png"
    )
    expect(page.get_by_role("row")).to_have_count(
        len(
            set(MERGEABLE_FIELDS_BY_CLASS_NAME["ExtractedResource"])
            | set(MERGEABLE_FIELDS_BY_CLASS_NAME["AdditiveResource"])
        )
    )


@pytest.mark.integration
def test_create_page_test_additive_buttons(create_page: Page) -> None:
    page = create_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-description-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    page.screenshot(
        path="tests_create_test_main-test_edit_page_renders_new_additive_button.png"
    )
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    additive_rule_input = page.get_by_test_id("additive-rule-description-0-text")
    expect(additive_rule_input).to_be_visible()

    remove_additive_rule_button = page.get_by_test_id(
        "additive-rule-description-0-remove-button"
    )
    expect(remove_additive_rule_button).to_be_visible()
    remove_additive_rule_button.click()
    expect(remove_additive_rule_button).not_to_be_visible()


@pytest.mark.requires_rki_infrastructure
@pytest.mark.integration
def test_create_page_submit_item(create_page: Page) -> None:
    page = create_page
    new_additive_button = page.get_by_test_id(
        f"new-additive-title-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    )
    new_additive_button.scroll_into_view_if_needed()
    expect(new_additive_button).to_be_visible()
    new_additive_button.click()

    additive_rule_input = page.get_by_test_id("additive-rule-title-0-text")
    expect(additive_rule_input).to_be_visible()
    additive_rule_input.fill("Test01234567")
    page.screenshot(path="tests_create_test_main-test_edit_page_save_item_input.png")

    submit_button = page.get_by_test_id("submit-button")
    submit_button.click()
    page.wait_for_timeout(30_000)
    page.screenshot(
        path="tests_create_test_main-test_edit_page_save_item_input_submit_pressed.png"
    )

    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "success")

    connector = BackendApiConnector.get()
    result = connector.fetch_merged_items(query_string="Test01234567")
    assert result.total == 1


@pytest.mark.parametrize(
    (
        "locale_id",
        "expected_access_platform_field_label",
    ),
    [
        pytest.param("de", "Zugriffsplattform", id="locale de"),
        pytest.param("en", "Access platform", id="locale en"),
    ],
)
@pytest.mark.integration
def test_language_switcher(
    create_page: Page, locale_id: str, expected_access_platform_field_label: str
) -> None:
    # language switcher should be there
    lang_switcher = create_page.get_by_test_id("language-switcher")
    expect(lang_switcher).to_be_visible()

    # change language and wait for reload
    lang_switcher.click()
    create_page.get_by_test_id(f"language-switcher-menu-item-{locale_id}").click()
    create_page.screenshot(
        path=f"tests_create_test_main-test_language_switcher-switcher_clicked-{locale_id}.png"
    )

    # select entity_type resource
    create_page.get_by_test_id("entity-type-select").click(timeout=30_000)
    create_page.get_by_test_id(
        re.compile(r"value-label-select-item-(.+)-Resource")
    ).click()
    create_page.wait_for_timeout(20000)
    create_page.screenshot(
        path=f"tests_create_test_main-test_language_switcher-resource_selected-{locale_id}.png"
    )
    # find the accessPlatform field label and check the text
    field_access_platform = create_page.get_by_test_id("field-accessPlatform-name")
    expect(field_access_platform).to_have_text(expected_access_platform_field_label)


@pytest.mark.integration
def test_search_reference_dialog(
    create_page: Page,
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    dialog_prefix = "search-reference-dialog"
    field_contact = create_page.get_by_test_id("field-contact")
    field_contact.get_by_test_id(
        f"new-additive-contact-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    field_contact.get_by_test_id(f"{dialog_prefix}-button").click()

    query_input = create_page.get_by_test_id(f"{dialog_prefix}-query-input")
    search_results = create_page.get_by_test_id("search-results-list")
    expect(search_results.locator(".search-result-card")).to_have_count(3)

    query_input.fill("OU")
    query_input.press("Enter")
    expect(search_results.locator(".search-result-card")).to_have_count(1)

    ou = dummy_data_by_identifier_in_primary_source["ou-1"]
    create_page.get_by_test_id(f"{dialog_prefix}-result-select-button").click()
    expect(
        create_page.get_by_test_id(f"{dialog_prefix}-query-input")
    ).not_to_be_visible()
    expect(
        field_contact.get_by_test_id("additive-rule-contact-0-identifier")
    ).to_have_value(ou.stableTargetId)

    field_uic = create_page.get_by_test_id("field-unitInCharge")
    field_uic.get_by_test_id(
        f"new-additive-unitInCharge-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    field_uic.get_by_test_id(f"{dialog_prefix}-button").click()
    expect(search_results.locator(".search-result-card")).to_have_count(1)
    create_page.locator(".rt-DialogOverlay").click(position={"x": 10, "y": 10})
    expect(
        field_uic.get_by_test_id("additive-rule-unitInCharge-0-identifier")
    ).to_have_value("")


@pytest.mark.integration
def test_create_page_test_draft_creation_on_entity_type_change(
    draft_create_page: DraftPage,
) -> None:
    create_page = draft_create_page["page"]

    create_page.get_by_test_id("entity-type-select").click()
    create_page.get_by_test_id(
        re.compile(r"value-label-select-item-(.+)-Resource")
    ).click()

    expect(draft_create_page["discard_dialog_button"]).to_be_visible()
    expect(draft_create_page["draft_menu_trigger"]).to_have_text("1")
    draft_create_page["draft_menu_trigger"].click()
    expect(draft_create_page["draft_menu_item"]).to_be_visible()


@pytest.mark.integration
def test_create_page_test_draft_creation_on_field_edit(
    draft_create_page: DraftPage,
) -> None:
    create_page = draft_create_page["page"]

    create_page.get_by_test_id(
        f"new-additive-title-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    expect(draft_create_page["discard_dialog_button"]).to_be_visible()
    expect(draft_create_page["draft_menu_trigger"]).to_have_text("1")
    draft_create_page["draft_menu_trigger"].click()
    expect(draft_create_page["draft_menu_item"]).to_be_visible()


@pytest.mark.integration
def test_create_page_test_discard_draft(
    draft_create_page: DraftPage,
) -> None:
    create_page = draft_create_page["page"]

    create_page.get_by_test_id(
        f"new-additive-title-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    create_page.get_by_test_id("additive-rule-title-0-text").fill(
        "Draft title for activity"
    )
    expect(draft_create_page["discard_dialog_button"]).to_be_visible()
    expect(draft_create_page["draft_menu_trigger"]).to_have_text("1")

    draft_create_page["discard_dialog_button"].click()
    draft_create_page["discard_button"].click()
    expect(draft_create_page["discard_dialog_button"]).not_to_be_visible()
    expect(draft_create_page["draft_menu_trigger"]).not_to_be_visible()


@pytest.mark.integration
def test_logout_unsaved_changes_dialog_on_draft_logout_normal(
    draft_create_page: DraftPage,
) -> None:
    page = draft_create_page["page"]

    def _screenshot(name: str) -> None:
        page.screenshot(
            path=f"tests_create_test_main-test_logout_unsaved_changes_dialog_on_draft_logout_normal-{name}.png"
        )

    # create and add contact there should be a draft
    page.get_by_test_id(
        f"new-additive-contact-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    expect(page.get_by_test_id("draft-menu-trigger")).to_be_visible()
    _screenshot("changes")

    # click logout and expect dialog
    page.get_by_test_id("user-menu").click()
    page.get_by_test_id("logout-button").click()
    _screenshot("dialog")
    expect(page.get_by_test_id("unsaved-changes-dialog")).to_be_visible()

    # cancel logout and delete draft
    page.get_by_test_id("unsaved-changes-dialog-cancel-button").click()
    expect(page.get_by_test_id("draft-menu-trigger")).to_be_visible()
    page.get_by_test_id("discard-draft-dialog-button").click()
    page.get_by_test_id("discard-draft-button").click()
    # wait some time to sync local storages
    page.wait_for_timeout(30000)
    expect(page.get_by_test_id("draft-menu-trigger")).not_to_be_visible()
    _screenshot("changes_removed")

    # logout should work normal (no dialog anymore)
    page.get_by_test_id("user-menu").click()
    logout_button = page.get_by_test_id("logout-button")
    expect(logout_button).to_be_visible()
    _screenshot("user_menu")
    page.get_by_test_id("logout-button").click()
    page.wait_for_url(re.compile(r"(.*)\/login\/?"))
    _screenshot("logout")
    expect(page.get_by_test_id("login-button")).to_be_visible()


@pytest.mark.integration
def test_logout_unsaved_changes_dialog_on_draft(draft_create_page: DraftPage) -> None:
    page = draft_create_page["page"]

    def _screenshot(name: str) -> None:
        page.screenshot(
            path=f"tests_create_test_main-test_logout_unsaved_changes_dialog_on_draft-{name}.png"
        )

    # create and add contact there should be a draft
    page.get_by_test_id(
        f"new-additive-contact-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    expect(page.get_by_test_id("draft-menu-trigger")).to_be_visible()
    _screenshot("changes")

    # click logout and expect dialog
    page.get_by_test_id("user-menu").click()
    page.get_by_test_id("logout-button").click()
    _screenshot("dialog")
    expect(page.get_by_test_id("unsaved-changes-dialog")).to_be_visible()
    page.get_by_test_id("unsaved-changes-dialog-logout-button").click()

    # logout should work
    page.wait_for_url(re.compile(r"(.*)\/login\/?"))
    _screenshot("logout")
    expect(page.get_by_test_id("login-button")).to_be_visible()


@pytest.mark.integration
def test_create_page_test_draft_menu_item_text(
    draft_create_page: DraftPage,
) -> None:
    create_page = draft_create_page["page"]

    create_page.get_by_test_id(
        f"new-additive-description-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    create_page.get_by_test_id("additive-rule-description-0-text").fill(
        "New Description."
    )

    expect(draft_create_page["discard_dialog_button"]).to_be_visible()
    expect(draft_create_page["draft_menu_trigger"]).to_have_text("1")
    draft_create_page["draft_menu_trigger"].click()
    expect(draft_create_page["draft_menu_item"]).to_be_visible()
    expect(draft_create_page["draft_menu_item"]).to_have_text("AccessPlatform")
    # force the menu overlay to close
    create_page.mouse.click(10, 10)
    create_page.get_by_test_id(
        f"new-additive-title-{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}"
    ).click()
    create_page.get_by_test_id("additive-rule-title-0-text").fill(
        "Draft title for access platform"
    )
    draft_create_page["draft_menu_trigger"].click()
    expect(draft_create_page["draft_menu_item"]).to_be_visible()
    expect(draft_create_page["draft_menu_item"]).to_have_text(
        "Draft title for access platform"
    )

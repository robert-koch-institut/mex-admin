import pytest
from playwright.sync_api import Page, expect
from pydantic import SecretStr

from tests.conftest import build_ui_label_regex


@pytest.mark.integration
def test_login_logout(
    base_url: str, page: Page, writer_user_credentials: tuple[str, SecretStr]
) -> None:
    page.goto(base_url)

    page.wait_for_url(f"{base_url}/login")
    page.get_by_test_id("input-username").fill(
        writer_user_credentials[0],
    )
    page.get_by_test_id("input-password").fill(
        writer_user_credentials[1].get_secret_value(),
    )
    page.screenshot(path="tests_login_test_main-test_login_logout-on-load.png")

    page.get_by_test_id("login-button").click()
    expect(page.get_by_test_id("nav-bar")).to_be_visible()
    expect(page.get_by_test_id("search-results-component")).to_be_visible()
    page.screenshot(path="tests_login_test_main-test_login_logout-after-login.png")

    page.get_by_test_id("user-menu").click()
    expect(page.get_by_test_id("logout-button")).to_be_visible()
    page.get_by_test_id("logout-button").click()
    page.wait_for_url(base_url)
    page.screenshot(path="tests_login_test_main-test_login_logout-after-logout.png")
    expect(page.get_by_test_id("login-button")).to_be_visible()
    expect(page.get_by_test_id("nav-bar")).not_to_be_visible()
    expect(page.get_by_test_id("search-results-component")).not_to_be_visible()


@pytest.mark.integration
def test_login_failure(base_url: str, page: Page) -> None:
    page.goto(base_url)

    page.wait_for_url(f"{base_url}/login")
    page.get_by_test_id("input-username").fill("Mallory")
    page.get_by_test_id("input-password").fill("i-have-no-access")
    page.screenshot(path="tests_login_test_main-test_login_failure-on-load.png")

    page.get_by_test_id("login-button").click()

    toast = page.locator(".editor-toast").first
    expect(toast).to_be_visible()
    expect(toast).to_have_attribute("data-type", "error")
    page.screenshot(path="tests_login_test_main-test_login_failure-on-toast.png")
    expect(toast).to_have_text(build_ui_label_regex("login.invalid_credentials"))
    expect(page).to_have_url(f"{base_url}/login")


@pytest.mark.integration
def test_login_with_enter_key(
    base_url: str, page: Page, writer_user_credentials: tuple[str, SecretStr]
) -> None:
    page.goto(base_url)

    page.get_by_test_id("input-username").fill(writer_user_credentials[0])
    password_input = page.get_by_test_id("input-password")
    password_input.fill(writer_user_credentials[1].get_secret_value())
    page.screenshot(path="tests_login_test_main-test_login_with_enter_key-on-load.png")

    password_input.press("Enter")
    expect(page.get_by_test_id("nav-bar")).to_be_visible()
    expect(page.get_by_test_id("search-results-component")).to_be_visible()
    page.screenshot(
        path="tests_login_test_main-test_login_with_enter_key-after-login.png"
    )

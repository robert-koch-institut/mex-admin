from collections.abc import Generator
from datetime import datetime
from zoneinfo import ZoneInfo

import reflex as rx
from reflex.event import EventSpec
from requests import RequestException

from mex.admin.exceptions import escalate_error, response_payload
from mex.admin.label_var import label_var
from mex.admin.models import NavItem, SearchResult
from mex.admin.settings import AdminSettings
from mex.admin.state import State
from mex.admin.transform import transform_models_to_search_results
from mex.common.backend_api.connector import BackendApiConnector, ReferenceFilter
from mex.common.models import (
    AdditiveConsent,
    AnyRuleSetRequest,
    AnyRuleSetResponse,
    ConsentRuleSetRequest,
)
from mex.common.types import (
    ConsentStatus,
    ConsentType,
    YearMonthDayTime,
)


class ConsentState(State):
    """State for the consent component."""

    consent_status: SearchResult | None = None

    @rx.var
    def _consent_nav_items(self) -> list[NavItem]:
        return [
            NavItem(
                title=self.label_nav_bar_consent_navitem,
                route_ids=["/consent"],
                raw_path="/consent",
            ),
        ]

    @rx.var
    def consent_nav_items_translated(self) -> list[NavItem]:
        """Get the translated consent nav items, based on the current_locale.

        Returns:
            The translated consent nav items.
        """
        return [self._translate_nav_item(item) for item in self._consent_nav_items]

    @rx.var
    def consent_md(self) -> str:
        """Get the translated consent markdown, based on the current_locale.

        Returns:
            The translated consent markdown.
        """
        settings = AdminSettings.get()
        path = settings.admin_assets_dir / f"consent_{self.current_locale}.md"
        return path.read_text(encoding="utf-8")

    @rx.var(cache=False)
    def consent_datetime(self) -> str:
        """Update datetime for a users consent status."""
        if not self.consent_status:
            return ""
        timestamp_str = self.consent_status.title[0].text
        timestamp_dt = datetime.fromisoformat(str(timestamp_str))
        timestamp_local = timestamp_dt.astimezone(ZoneInfo("Europe/Berlin"))
        return timestamp_local.strftime("%d.%m.%Y %H:%M")

    @rx.var
    def is_consent_valid_for_processing(self) -> bool:
        """Check if the consent status badge is VALID_FOR_PROCESSING."""
        if not self.consent_status or not self.consent_status.preview:
            return False
        return self.consent_status.preview[0].badge == "VALID_FOR_PROCESSING"

    @rx.event
    def get_consent(self) -> Generator[EventSpec | None]:
        """Fetch the user's consent status."""
        if not self.merged_login_person:
            yield None
            return

        connector = BackendApiConnector.get()
        try:
            response = connector.fetch_preview_items(
                query_string=None,
                entity_type=["MergedConsent"],
                reference_filters=[
                    ReferenceFilter(
                        field="hasDataSubject",
                        identifiers=[str(self.merged_login_person.identifier)],
                    )
                ],
            )
        except RequestException as exc:
            self.is_loading = False
            yield None
            yield from escalate_error(
                "backend", "No Consent could be fetched.", response_payload(exc)
            )
        else:
            if response.total > 0:
                self.consent_status = transform_models_to_search_results(
                    [response.items[0]]
                )[0]
            else:
                self.consent_status = None

    @rx.event
    def submit_rule_set(
        self,
        consented: str,
    ) -> Generator[EventSpec | None]:
        """Convert the fields to a rule set and submit it to the backend."""
        if not self.merged_login_person:
            yield None
            return

        is_consenting = consented == "consent"

        # Check if the consent status would actually change
        if (
            self.consent_status
            and self.is_consent_valid_for_processing == is_consenting
        ):
            yield None
            return

        additive_consent = AdditiveConsent(
            hasConsentStatus=(
                ConsentStatus["VALID_FOR_PROCESSING"]
                if is_consenting
                else ConsentStatus["INVALID_FOR_PROCESSING"]
            ),
            hasDataSubject=self.merged_login_person.identifier,
            isIndicatedAtTime=YearMonthDayTime(
                datetime.now(tz=ZoneInfo("Europe/Berlin")).isoformat()
            ),
            hasConsentType=(
                ConsentType["EXPRESSED_CONSENT"] if is_consenting else None
            ),
        )

        rule_set_request = ConsentRuleSetRequest(additive=additive_consent)
        try:
            self._send_rule_set_request(rule_set_request)
        except RequestException as exc:
            self.reset()  # type: ignore[no-untyped-call]
            yield from escalate_error(
                "backend", "error submitting rule set", response_payload(exc)
            )
            return
        else:
            yield type(self).get_consent()  # type: ignore[operator]
            yield type(self).show_submit_success_toast()  # type: ignore[operator]

    def _send_rule_set_request(self, rule_set: AnyRuleSetRequest) -> AnyRuleSetResponse:
        """Send the rule set to the backend."""
        connector = BackendApiConnector.get()
        # TODO(ND): use user auth for backend requests (stop-gap MX-1616)
        if self.consent_status:
            return connector.update_rule_set(self.consent_status.identifier, rule_set)
        return connector.create_rule_set(rule_set)

    @rx.event
    def show_submit_success_toast(self) -> EventSpec:
        """Show a toast for a successfully submitted rule-set."""
        return rx.toast.success(
            title=self.label_save_success_dialog_title,
            description=self.label_save_success_dialog_content,
            class_name="editor-toast",
            close_button=True,
            dismissible=True,
            duration=5000,
        )

    @label_var(
        label_id="consent.consent_status.consented_format", deps=["consent_datetime"]
    )
    def label_consent_status_consented_format(self) -> list[str]:
        """Label for consent.consent_status.consented_format."""
        return [self.consent_datetime]

    @label_var(
        label_id="consent.consent_status.declined_format", deps=["consent_datetime"]
    )
    def label_consent_status_declined_format(self) -> list[str]:
        """Label for consent.consent_status.declined_format."""
        return [self.consent_datetime]

    @label_var(label_id="consent.consent_retraction_denial")
    def label_consent_retraction_denial(self) -> None:
        """Label for consent.consent_retraction_denial."""

    @label_var(label_id="consent.consent_status.no_consent")
    def label_consent_status_no_consent(self) -> None:
        """Label for consent.status.no_consent."""

    @label_var(label_id="consent.resources.title")
    def label_resources_title(self) -> None:
        """Label for resources.title."""

    @label_var(label_id="consent.projects.title")
    def label_projects_title(self) -> None:
        """Label for projects.title."""

    @label_var(label_id="consent.publications.title")
    def label_publications_title(self) -> None:
        """Label for publications.title."""

    @label_var(label_id="consent.user_data.loading")
    def label_user_data_loading(self) -> None:
        """Label for user_data.loading  ."""

    @label_var(label_id="consent.consent_box.consent_button")
    def label_consent_box_consent_button(self) -> None:
        """Label for consent_box.consent_button."""

    @label_var(label_id="consent.consent_box.no_consent_button")
    def label_consent_box_no_consent_button(self) -> None:
        """Label for consent_box.no_consent_button."""

    @label_var(label_id="consent.consent_status.loading")
    def label_consent_status_loading(self) -> None:
        """Label for consent_status.loading."""

    @label_var(label_id="consent.save_success_dialog.title")
    def label_save_success_dialog_title(self) -> None:
        """Label for save_success_dialog.title."""

    @label_var(label_id="consent.save_success_dialog.content")
    def label_save_success_dialog_content(self) -> None:
        """Label for save_success_dialog.content."""

    @label_var(label_id="consent.nav_bar.consent_navitem")
    def label_nav_bar_consent_navitem(self) -> None:
        """Label for nav_bar.consent_navitem."""

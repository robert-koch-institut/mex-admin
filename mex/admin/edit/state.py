from collections.abc import Generator
from urllib.parse import parse_qs, urlparse

import reflex as rx
from reflex.event import EventSpec
from requests import HTTPError

from mex.admin.label_var import label_var
from mex.admin.models import SearchResult
from mex.admin.rules.state import RuleState
from mex.admin.transform import transform_models_to_search_results
from mex.admin.utils import resolve_editor_value
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.logging import logger
from mex.common.types import PublishingTarget


class EditState(RuleState):
    """State for the edit component."""

    is_deleting: bool = False

    @rx.var
    async def superseded_by_backward(self) -> list[SearchResult]:
        """Load the superseding items for the current item."""
        results: list[SearchResult] = []

        if self.item_id:
            connector = BackendApiConnector.get()
            try:
                results = transform_models_to_search_results(
                    connector.fetch_all_merged_items(
                        reference_field="supersededBy",
                        referenced_identifier=[self.item_id],
                    )
                )

            except HTTPError as ex:
                logger.error(
                    "%s - %s: %s",
                    "backend",
                    "error fetching superseding items using 'fetch_all_merged_items'.",
                    ex.response.json(),
                    exc_info=False,
                )

        for result in results:
            for preview in result.preview:
                if preview.identifier and not preview.text:
                    await resolve_editor_value(preview)

        return results

    @rx.event
    def toggle_publish_target(self, publish_target_id: str) -> None:
        """Toggle the given publish target by id."""
        if self.workflow_rule:
            target = PublishingTarget(publish_target_id)
            if publish_target_id in self.workflow_rule.forbiddenPublishingTarget:
                self.workflow_rule.forbiddenPublishingTarget.remove(target)
            else:
                self.workflow_rule.forbiddenPublishingTarget.append(target)

    @rx.event
    def delete_reset(self) -> Generator[EventSpec | None]:
        """Call the delete or reset function."""
        self.is_deleting = True
        yield None

        if self.item_id:
            connector = BackendApiConnector.get()
            connector.delete_rule_set(self.item_id)

            if self.delete_reset_mode == "delete":
                yield rx.redirect("/")
                yield rx.toast.success(
                    title=self.label_delete_rules_success_toast_title,
                    description=self.label_delete_rules_success_toast_text,
                    class_name="editor-toast",
                    close_button=True,
                    dismissible=True,
                    duration=5000,
                )
            elif self.delete_reset_mode == "reset":
                yield rx.redirect(f"/item/{self.item_id}")
                yield rx.toast.success(
                    title=self.label_reset_rules_success_toast_title,
                    description=self.label_reset_rules_success_toast_text,
                    class_name="editor-toast",
                    close_button=True,
                    dismissible=True,
                    duration=5000,
                )

        self.is_deleting = False

    @rx.event
    def show_submit_success_toast_on_redirect(self) -> Generator[EventSpec]:
        """Show a success toast when the saved param is set."""
        parsed_url = urlparse(self.router.url)
        params = parse_qs(parsed_url.query)
        if "saved" in params:
            yield EditState.show_submit_success_toast  # type: ignore[misc]
            params.pop("saved")
            if event := self.push_url_params(params):
                yield event

    @label_var(label_id="edit.publish_targets")
    def label_publish_targets(self) -> None:
        """Label for publish_targets."""

    @label_var(label_id="edit.discard_changes.button")
    def label_discard_changes_button(self) -> None:
        """Label for discard_changes.button."""

    @label_var(label_id="edit.discard_changes_dialog.title")
    def label_discard_changes_dialog_title(self) -> None:
        """Label for discard_changes_dialog.title."""

    @label_var(label_id="edit.discard_changes_dialog.description")
    def label_discard_changes_dialog_description(self) -> None:
        """Label for discard_changes_dialog.description."""

    @label_var(label_id="edit.discard_changes_dialog.cancel_button")
    def label_discard_changes_dialog_cancel_button(self) -> None:
        """Label for discard_changes_dialog.cancel_button."""

    @label_var(label_id="edit.discard_changes_dialog.discard_button")
    def label_discard_changes_dialog_discard_button(self) -> None:
        """Label for discard_changes_dialog.discard_button."""

    @label_var(label_id="edit.reset_rules.button")
    def label_reset_rules_button(self) -> None:
        """Label for reset_rules.button."""

    @label_var(label_id="edit.delete_rules.button")
    def label_delete_rules_button(self) -> None:
        """Label for delete_rules.button."""

    @label_var(label_id="edit.delete_rules.success_toast_title")
    def label_delete_rules_success_toast_title(self) -> None:
        """Label for delete_rules.success_toast_title."""

    @label_var(label_id="edit.delete_rules.success_toast_text")
    def label_delete_rules_success_toast_text(self) -> None:
        """Label for delete_rules.success_toast_text."""

    @label_var(label_id="edit.reset_rules.success_toast_title")
    def label_reset_rules_success_toast_title(self) -> None:
        """Label for reset_rules.success_toast_title."""

    @label_var(label_id="edit.reset_rules.success_toast_text")
    def label_reset_rules_success_toast_text(self) -> None:
        """Label for reset_rules.success_toast_text."""

    @label_var(label_id="edit.field_supersededBy.label")
    def label_field_superseded_by_label(self) -> None:
        """Label for field_supersededBy.label."""

    @label_var(label_id="edit.field_supersededBy.description")
    def label_field_superseded_by_description(self) -> None:
        """Label for field_supersededBy_description."""

    @label_var(label_id="edit.field_supersededBy.empty")
    def label_field_superseded_by_empty(self) -> None:
        """Label for field_supersededBy_empty."""

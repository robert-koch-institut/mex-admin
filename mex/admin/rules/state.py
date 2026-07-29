import copy
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING, Literal, cast

import reflex as rx
from pydantic import ValidationError
from reflex.event import EventSpec
from requests import HTTPError, RequestException
from starlette import status

from mex.admin.exceptions import escalate_error
from mex.admin.label_var import label_var
from mex.admin.locale_service import LocaleService
from mex.admin.models import EditorValue, sequence_is_equal
from mex.admin.rules.local_storage_mixin_state import LocalStorageMixinState
from mex.admin.rules.models import (
    EditorField,
    EditorPrimarySource,
    FieldTranslation,
    LocalDraft,
    LocalEdit,
    PublishTarget,
    ValidationMessage,
)
from mex.admin.rules.transform import (
    transform_fields_to_rule_set,
    transform_models_to_fields,
    transform_publish_targets_to_workflow,
    transform_validation_error_to_messages,
    transform_workflow_to_publish_targets,
)
from mex.admin.state import State
from mex.admin.transform import (
    transform_models_to_stem_type,
    transform_models_to_title,
)
from mex.admin.utils import resolve_editor_value, resolve_identifier
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.merged.main import create_merged_item
from mex.common.models import (
    RULE_SET_REQUEST_CLASSES,
    RULE_SET_REQUEST_CLASSES_BY_NAME,
    RULE_SET_RESPONSE_CLASSES_BY_NAME,
    AnyExtractedModel,
    AnyRuleSetRequest,
    AnyRuleSetResponse,
    AnyWorkflowModel,
)
from mex.common.transform import ensure_postfix
from mex.common.types import Identifier, Validation

locale_service = LocaleService.get()


def _error_payload(exc: RequestException) -> str:
    """Return the response body of a failed request, or the error itself."""
    if exc.response is not None:
        return exc.response.text
    return str(exc)


class RuleState(State, LocalStorageMixinState):
    """Base state for the edit and create components."""

    _api_fields: list[EditorField] = []

    is_submitting: bool = False
    is_loading: bool = True
    load_error: Literal["not_found", "backend"] | None = None
    delete_reset_mode: Literal["delete", "reset"] | None = None
    item_title: list[EditorValue] = []
    fields: list[EditorField] = []
    stem_type: str | None = None
    validation_messages: list[ValidationMessage] = []
    workflow_rule: AnyWorkflowModel | None = None

    if TYPE_CHECKING:
        item_id: str
        draft_id: str

    @rx.var(cache=True, deps=["fields", "_api_fields"])
    def has_changes(self) -> bool:
        """Indicates if the current edit state differs from the original loaded state.

        Returns:
            Returns True if the current edit state differs from the original
            loaded state; otherwise False.
        """
        fields: list[EditorField] = self.get_value("fields")
        api_fields: list[EditorField] = self.get_value("_api_fields")

        return not sequence_is_equal(fields, api_fields)

    @rx.var
    def publish_targets(self) -> list[PublishTarget]:
        """Get a list of publish targets with enable state."""
        return transform_workflow_to_publish_targets(self.workflow_rule)

    @rx.event
    def update_local_state(self) -> None:
        """Updates the local edits and drafts with current values."""
        _fields = self.get_value("fields")
        if self.item_id:
            self.update_edit(
                self.item_id,
                LocalEdit(fields=_fields),
            )  # type: ignore[operator]
        elif self.draft_id:
            self.update_draft(
                self.draft_id,
                LocalDraft(
                    fields=_fields,
                    stem_type=self.stem_type or "",
                ),
            )  # type: ignore[operator]

    @rx.event
    def delete_local_state(self) -> None:
        """Delete local state for draft or edit."""
        if self.item_id:
            self.delete_edit(self.item_id)  # type: ignore[operator]
        elif self.draft_id:
            self.delete_draft(self.draft_id)  # type: ignore[operator]

    @rx.var(cache=True, deps=["fields", "current_locale"])
    def translated_fields(self) -> list[FieldTranslation]:
        """Compute the translated fields based on fields and current_locale.

        Returns:
            Translated fields containing label and description translation.
        """
        if self.stem_type:
            fields = cast("list[EditorField]", self.get_value("fields"))
            return [
                FieldTranslation(
                    field=field,
                    label=locale_service.get_field_label(
                        self.current_locale, self.stem_type, field.name
                    ),
                    description=locale_service.get_field_description(
                        self.current_locale, self.stem_type, field.name
                    ),
                )
                for field in fields
            ]
        return []

    @rx.event(background=True)
    async def resolve_identifiers(self) -> None:
        """Resolve identifiers to human readable display values."""
        for field in self.fields:
            for primary_source in field.primary_sources:
                name = primary_source.name
                if name.identifier and not name.text:
                    async with self:
                        await resolve_editor_value(name)
                for editor_value in primary_source.editor_values:
                    if editor_value.identifier and not editor_value.text:
                        async with self:
                            await resolve_editor_value(editor_value)

    @classmethod
    def _contains_any_rule(
        cls, rule_set: AnyRuleSetResponse | AnyRuleSetRequest
    ) -> bool:
        """Check if a rule set response contains any rule."""
        return any(
            [
                rule_set.additive.model_dump(exclude_defaults=True),
                rule_set.subtractive.model_dump(exclude_defaults=True),
                rule_set.preventive.model_dump(exclude_defaults=True),
            ]
        )

    def _get_extracted_items(self) -> list[AnyExtractedModel]:
        """Get the list of extracted items the rules should apply to."""
        if self.item_id:
            connector = BackendApiConnector.get()
            extracted_items_response = connector.fetch_extracted_items(
                stable_target_id=self.item_id
            )
            return extracted_items_response.items
        return []

    def _get_rule_set(self) -> AnyRuleSetRequest | AnyRuleSetResponse:
        """Get or create a rule set request or response."""
        if self.item_id:
            connector = BackendApiConnector.get()
            try:
                return connector.get_rule_set(self.item_id)
            except HTTPError as exc:
                if (
                    exc.response.status_code == status.HTTP_404_NOT_FOUND
                    and self.stem_type
                ):
                    rule_set_response_class = RULE_SET_RESPONSE_CLASSES_BY_NAME[
                        ensure_postfix(self.stem_type, "RuleSetResponse")
                    ]
                    return rule_set_response_class(stableTargetId=self.item_id)
                raise
        if stem_type := self.stem_type:
            rule_set_request_class = RULE_SET_REQUEST_CLASSES_BY_NAME[
                ensure_postfix(stem_type, "RuleSetRequest")
            ]
        else:
            rule_set_request_class = RULE_SET_REQUEST_CLASSES[0]
        return rule_set_request_class()

    @rx.event
    def refresh(self) -> Generator[EventSpec | None]:
        """Refresh the edit or create page."""
        self.delete_reset_mode = None
        self.fields.clear()
        self.validation_messages.clear()
        self.load_error = None
        self.is_loading = True
        # flush the loading state to the frontend before the blocking calls below
        yield None

        if not self.item_id and not self.draft_id:
            self.is_loading = False
            yield rx.redirect(path=f"/create/{Identifier.generate()}")
            return

        try:
            extracted_items = self._get_extracted_items()
        except RequestException as exc:
            self.is_loading = False
            self.load_error = "backend"
            yield from escalate_error(
                "backend", "error fetching extracted items", _error_payload(exc)
            )
            return

        if extracted_items:
            self.stem_type = transform_models_to_stem_type(extracted_items)
        try:
            rule_set = self._get_rule_set()
        except RequestException as exc:
            self.is_loading = False
            # a missing rule-set for an item without any extracted items means
            # there is nothing to edit under this identifier at all
            self.load_error = (
                "not_found"
                if exc.response is not None
                and exc.response.status_code == status.HTTP_404_NOT_FOUND
                and not extracted_items
                else "backend"
            )
            yield from escalate_error(
                "backend", "error fetching rule items", _error_payload(exc)
            )
            return

        if rule_set and self.item_id:
            self.stem_type = transform_models_to_stem_type([rule_set.additive])
            self.workflow_rule = rule_set.workflow

        if self.item_id:
            preview = create_merged_item(
                identifier=Identifier(self.item_id),
                extracted_items=extracted_items,
                rule_set=rule_set,
                validation=Validation.LENIENT,
            )
            self.item_title = transform_models_to_title([preview])

        if rule_set and self._contains_any_rule(rule_set):
            self.delete_reset_mode = "reset" if extracted_items else "delete"

        loaded_fields = transform_models_to_fields(
            extracted_items,
            additive=rule_set.additive,
            subtractive=rule_set.subtractive,
            preventive=rule_set.preventive,
        )

        if self.item_id:
            self.fields = (
                self.edits[self.item_id].fields
                if self.item_id in self.edits
                else loaded_fields
            )
        elif self.draft_id:
            draft = self.drafts.get(self.draft_id)
            self.fields = draft.fields if draft else loaded_fields
            self.stem_type = draft.stem_type if draft else self.stem_type
        else:
            self.fields = loaded_fields

        self._api_fields = copy.deepcopy(loaded_fields)
        self.is_loading = False

    def _send_rule_set_request(self, rule_set: AnyRuleSetRequest) -> AnyRuleSetResponse:
        """Send the rule set to the backend."""
        connector = BackendApiConnector.get()
        # TODO(ND): use the user auth for backend requests (stop-gap MX-1616)
        if self.item_id:
            return connector.update_rule_set(self.item_id, rule_set)
        return connector.create_rule_set(rule_set)

    @rx.event
    def submit_rule_set(self) -> Generator[EventSpec]:
        """Convert the fields to a rule set and submit it to the backend."""
        if self.stem_type is None:
            self.reset()  # type: ignore[no-untyped-call]
            return
        try:
            rule_set_request = transform_fields_to_rule_set(self.stem_type, self.fields)
            rule_set_request.workflow = transform_publish_targets_to_workflow(
                self.stem_type, self.publish_targets
            )
        except ValidationError as exc:
            self.validation_messages = transform_validation_error_to_messages(exc)
            return
        try:
            rule_set_response = self._send_rule_set_request(rule_set_request)
        except HTTPError as exc:
            self.reset()  # type: ignore[no-untyped-call]
            yield from escalate_error(
                "backend", "error submitting rule set", exc.response.text
            )
            return

        yield RuleState.delete_local_state  # type: ignore[misc]

        # clear cache to show edits in the UI
        resolve_identifier.cache_clear()
        # trigger redirect to edit page or refresh state
        if rule_set_response.stableTargetId != self.item_id:
            yield rx.redirect(f"/item/{rule_set_response.stableTargetId}/?saved")
        else:
            yield RuleState.refresh  # type: ignore[misc]
            yield RuleState.show_submit_success_toast  # type: ignore[misc]
            yield RuleState.resolve_identifiers

    @rx.event
    def set_is_submitting(self, value: bool) -> None:  # noqa: FBT001
        """Set the is_submitting attribute.

        Args:
            value: The value for is_submitting.
        """
        self.is_submitting = value

    @rx.event
    def show_submit_success_toast(self) -> Generator[EventSpec]:
        """Show a toast for a successfully submitted rule-set."""
        yield rx.toast.success(
            title=self.label_save_success_dialog_title,
            description=self.label_save_success_dialog_message_format,
            class_name="editor-toast",
            close_button=True,
            dismissible=True,
            duration=5000,
        )

    @rx.event
    def clear_validation_messages(self) -> None:
        """Clear all validation messages."""
        self.validation_messages.clear()

    def _get_primary_sources_by_field_name(
        self, field_name: str
    ) -> list[EditorPrimarySource]:
        """Get all primary sources for the given field name."""
        for field in self.fields:
            if field.name == field_name:
                return field.primary_sources
        msg = f"field not found: {field_name}"
        raise ValueError(msg)

    def _get_editable_primary_source_by_field_name(
        self, field_name: str
    ) -> EditorPrimarySource:
        """Get the (first) primary source that allows an editable rule."""
        for primary_source in self._get_primary_sources_by_field_name(field_name):
            if primary_source.input_config.allow_additive:
                return primary_source
        msg = f"editable field not found: {field_name}"
        raise ValueError(msg)

    @rx.event
    def toggle_primary_source(
        self,
        field_name: str,
        href: str | None,
        enabled: bool,  # noqa: FBT001
    ) -> Generator[EventSpec]:
        """Toggle the `enabled` flag of a primary source."""
        for primary_source in self._get_primary_sources_by_field_name(field_name):
            if primary_source.name.href == href:
                primary_source.enabled = enabled
                yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def toggle_field_value(
        self,
        field_name: str,
        value: EditorValue,
        enabled: bool,  # noqa: FBT001
    ) -> Generator[EventSpec]:
        """Toggle the `enabled` flag of a field value."""
        for primary_source in self._get_primary_sources_by_field_name(field_name):
            for editor_value in primary_source.editor_values:
                if editor_value == value:
                    editor_value.enabled = enabled
                    yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def toggle_field_value_editing(
        self,
        field_name: str,
        index: int,
    ) -> Generator[EventSpec]:
        """Toggle editing of a field value."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values[
            index
        ].being_edited = not primary_source.editor_values[index].being_edited
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def add_additive_value(self, field_name: str) -> Generator[EventSpec]:
        """Add an additive rule to the given field."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values.append(EditorValue(being_edited=True))
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def remove_additive_value(
        self, field_name: str, index: int
    ) -> Generator[EventSpec]:
        """Remove an additive rule from the given field."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values.pop(index)
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def set_text_value(
        self, field_name: str, index: int, value: str
    ) -> Generator[EventSpec]:
        """Set the text attribute on an additive editor value."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values[index].text = value
        yield RuleState.update_local_state  # type: ignore[misc]

    async def _apply_identifier_value(
        self, field_name: str, index: int, value: str
    ) -> EditorValue:
        """Set and resolve the identifier attribute on an additive editor value."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        editor_value = primary_source.editor_values[index]
        editor_value.identifier = value
        editor_value.href = f"/item/{value}"
        await resolve_editor_value(editor_value)
        return editor_value

    @rx.event
    async def set_identifier_value(
        self, field_name: str, index: int, value: str
    ) -> AsyncGenerator[EventSpec]:
        """Set the identifier attribute on an additive editor value."""
        await self._apply_identifier_value(field_name, index, value)
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    async def select_identifier_value(
        self, field_name: str, index: int, value: str
    ) -> AsyncGenerator[EventSpec]:
        """Set the identifier on an additive editor value and stop editing it."""
        editor_value = await self._apply_identifier_value(field_name, index, value)
        editor_value.being_edited = False
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def set_badge_value(
        self, field_name: str, index: int, value: str
    ) -> Generator[EventSpec]:
        """Set the badge attribute on an additive editor value."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values[index].badge = value
        yield RuleState.update_local_state  # type: ignore[misc]

    @rx.event
    def set_href_value(
        self, field_name: str, index: int, value: str
    ) -> Generator[EventSpec]:
        """Set an external href on an additive editor value."""
        primary_source = self._get_editable_primary_source_by_field_name(field_name)
        primary_source.editor_values[index].href = value
        primary_source.editor_values[index].external = True
        yield RuleState.update_local_state  # type: ignore[misc]

    @label_var(label_id="rules.additive_rule.add_button_prefix")
    def label_additive_rule_add_button_prefix(self) -> None:
        """Label for additive_rule.add_button."""

    @label_var(label_id="rules.additive_rule.remove_button_prefix")
    def label_additive_rule_remove_button_prefix(self) -> None:
        """Label for additive_rule.remove_button."""

    @label_var(label_id="rules.validation_result_dialog.close_button")
    def label_validation_result_dialog_close_button(self) -> None:
        """Label for validation_result_dialog.close_button."""

    @label_var(label_id="rules.validation_result_dialog.title")
    def label_validation_result_dialog_title(self) -> None:
        """Label for validation_result_dialog.title."""

    @label_var(label_id="rules.save_button.format", deps=["label_stem_type"])
    def label_save_button_format(self) -> list[str]:
        """Label for save_button.format."""
        return [self.label_stem_type]

    @label_var(label_id="rules.save_button.saving_format", deps=["label_stem_type"])
    def label_save_button_saving_format(self) -> list[str]:
        """Label for save_button.saving_format."""
        return [self.label_stem_type]

    @label_var(label_id="rules.save_success_dialog.title")
    def label_save_success_dialog_title(self) -> None:
        """Label for save_success_dialog.title."""

    @label_var(
        label_id="rules.save_success_dialog.message_format", deps=["label_stem_type"]
    )
    def label_save_success_dialog_message_format(self) -> list[str]:
        """Label for save_success_dialog.message_format."""
        return [self.label_stem_type]

    @rx.var
    def label_stem_type(self) -> str:
        """Label for stem_type."""
        return (
            self._locale_service.get_ui_label(self.current_locale, self.stem_type)
            if self.stem_type
            else ""
        )

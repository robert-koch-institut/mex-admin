import reflex as rx

from mex.admin.rules.models import (
    LocalDraft,
    LocalDraftStorageObject,
    LocalEdit,
    LocalEditStorageObject,
    UserDraft,
    UserEdit,
)
from mex.admin.transform import transform_fields_to_title


class LocalStorageMixinState(rx.State, mixin=True):
    """State-Mixin for handling local drafts and edits of AdminFields."""

    local_draft_store: str = rx.LocalStorage('{"value": {}}', sync=True)
    local_edit_store: str = rx.LocalStorage('{"value": {}}', sync=True)

    @rx.var
    def drafts(self) -> dict[str, UserDraft]:
        """Get all local drafts."""

        def _create_draft(x: LocalDraft, identifier: str) -> UserDraft:
            titles = transform_fields_to_title(x.stem_type, x.fields)
            return UserDraft(
                identifier=identifier,
                stem_type=x.stem_type,
                fields=x.fields,
                title=titles[0],
            )

        draft_store = LocalDraftStorageObject.model_validate_json(
            self.local_draft_store
        )
        return {
            key: _create_draft(value, key) for key, value in draft_store.value.items()
        }

    @rx.var
    def draft_count(self) -> int:
        """Get the count/size/length of drafts."""
        return len(self.drafts)

    @rx.var
    def edits(self) -> dict[str, UserEdit]:
        """Get all local edits."""

        def _create_edit(x: LocalEdit, identifier: str) -> UserEdit:
            return UserEdit(
                identifier=identifier,
                fields=x.fields,
            )

        edit_store = LocalEditStorageObject.model_validate_json(self.local_edit_store)
        return {
            key: _create_edit(value, key) for key, value in edit_store.value.items()
        }

    @rx.var
    def edit_count(self) -> int:
        """Get the count/size/length of edits."""
        return len(self.edits)

    @rx.event
    def update_draft(self, identifier: str, draft: LocalDraft) -> None:
        """Update a LocalDraft with the given identifier."""
        draft_store = LocalDraftStorageObject.model_validate_json(
            self.local_draft_store
        )
        draft_store.value[identifier] = draft
        self.local_draft_store = draft_store.model_dump_json()

    @rx.event
    def update_edit(self, identifier: str, edit: LocalEdit) -> None:
        """Update a LocalEdit with the given identifier."""
        edit_store = LocalEditStorageObject.model_validate_json(self.local_edit_store)
        edit_store.value[identifier] = edit
        self.local_edit_store = edit_store.model_dump_json()

    @rx.event
    def delete_draft(self, identifier: str) -> None:
        """Delete a LocalDraft with the given identifier."""
        draft_store = LocalDraftStorageObject.model_validate_json(
            self.local_draft_store
        )
        if identifier in draft_store.value:
            draft_store.value.pop(identifier)
            self.local_draft_store = draft_store.model_dump_json()

    @rx.event
    def delete_edit(self, identifier: str) -> None:
        """Delete a LocalEdit with the given identifier."""
        edit_store = LocalEditStorageObject.model_validate_json(self.local_edit_store)
        if identifier in edit_store.value:
            edit_store.value.pop(identifier)
            self.local_edit_store = edit_store.model_dump_json()

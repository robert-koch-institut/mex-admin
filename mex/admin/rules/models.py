from pydantic import BaseModel

from mex.admin.models import EditorValue, EqualityDetector, sequence_is_equal
from mex.common.types import MergedPrimarySourceIdentifier


class InputConfig(BaseModel):
    """Model for configuring input masks."""

    badge_default: str | None = None  # value to pre-select in drop-down menu
    badge_options: list[str] = []  # possible values to show in drop-down menu
    badge_titles: list[str] = []  # title for the collection of drop-drown choices
    editable_href: bool = False  # whether the href attribute is editable as text
    editable_badge: bool = False  # whether the badge is editable as a drop-down
    editable_identifier: bool = False  # whether the identifier is editable as text
    editable_text: bool = False  # whether the text is editable as plain text
    allow_additive: bool = False  # whether this field belongs to an additive rule
    render_textarea: bool = False  # whether this field is rendered as a textarea
    allow_subtractive: bool = True  # whether this field belongs to an subtractive rule
    allow_preventive: bool = True  # whether this field belongs to an preventive rule


class ValidationMessage(BaseModel):
    """Model for describing validation errors."""

    field_name: str
    message: str
    input: str


class EditorPrimarySource(BaseModel):
    """Model for describing the editor state for one primary source."""

    name: EditorValue
    identifier: MergedPrimarySourceIdentifier
    input_config: InputConfig
    editor_values: list[EditorValue]
    enabled: bool

    def is_equal(self, other: EqualityDetector) -> bool:
        """Check if self and other are equal."""
        if isinstance(other, EditorPrimarySource):
            return (
                self.identifier == other.identifier
                and self.enabled == other.enabled
                and sequence_is_equal(self.editor_values, other.editor_values)
            )
        return False


class EditorField(BaseModel):
    """Model for describing the editor state for a single field."""

    name: str
    value_type: list[str]
    primary_sources: list[EditorPrimarySource]
    is_required: bool

    def is_equal(self, other: EqualityDetector) -> bool:
        """Check if self and other are equal."""
        if isinstance(other, EditorField):
            return self.name == other.name and sequence_is_equal(
                self.primary_sources, other.primary_sources
            )
        return False


class PublishTarget(BaseModel):
    """Model for publish targets with label and enable state."""

    identifier: str
    label: str
    enabled: bool


class FieldTranslation(BaseModel):
    """Wraps an editor field to add translated label and description."""

    field: EditorField
    label: str
    description: str


class LocalEdit(BaseModel):
    """Model to store local edits in the browser."""

    fields: list[EditorField]


class LocalDraft(LocalEdit):
    """Model to store local drafts in the browser."""

    stem_type: str


class UserEdit(LocalEdit):
    """Model to represent local edits."""

    identifier: str


class UserDraft(LocalDraft):
    """Model to represent local drafts."""

    identifier: str
    title: EditorValue


class LocalDraftStorageObject(BaseModel):
    """Model to de-/serialize local drafts in browsers local storage."""

    value: dict[str, LocalDraft]


class LocalEditStorageObject(BaseModel):
    """Model to de-/serialize local edits in browsers local storage."""

    value: dict[str, LocalEdit]

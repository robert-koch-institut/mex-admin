from collections.abc import Sequence
from importlib.resources import files
from typing import Protocol

import yaml
from pydantic import BaseModel, TypeAdapter

from mex.common.types import MergedPersonIdentifier


class EqualityDetector(Protocol):
    """Interface for checking equality without overriding __eq__."""

    def is_equal(self, other: EqualityDetector) -> bool: ...  # noqa: D102


def sequence_is_equal(
    left: Sequence[EqualityDetector], right: Sequence[EqualityDetector]
) -> bool:
    """Check if the given sequences are equal (based on EqualityDetector.is_equal)."""
    try:
        return all(a.is_equal(b) for a, b in zip(left, right, strict=True))
    except ValueError:
        return False  # sequences don't have same length


class EditorValue(BaseModel):
    """Model for describing atomic values in the admin."""

    text: str | None = None
    identifier: str | None = None
    badge: str | None = None
    href: str | None = None
    external: bool = False
    enabled: bool = True
    being_edited: bool = False

    def is_equal(self, other: EqualityDetector) -> bool:
        """Check if self and other are equal."""
        if isinstance(other, EditorValue):
            exclude = {"text"} if other.identifier and not other.text else set()
            self_dict = self.model_dump(exclude=exclude)
            other_dict = other.model_dump(exclude=exclude)
            return self_dict == other_dict
        return False


class User(BaseModel):
    """Info on the currently logged-in user."""

    name: str
    write_access: bool


class MergedLoginPerson(BaseModel):
    """Info on the currently logged-in user from the merged login endpoint."""

    identifier: MergedPersonIdentifier | None = None
    full_name: list[str] | None = None
    email: list[str] | None = None
    orcid_id: list[str] | None = None


class NavItem(BaseModel):
    """Model for one navigation bar item."""

    title: str
    route_ids: list[str]
    raw_path: str
    active: bool = False


class ModelConfig(BaseModel):
    """Configuration for how to display an entity type in the frontend."""

    title: str
    preview: list[str] = []
    textarea: list[str] = []


MODEL_CONFIG_BY_STEM_TYPE = TypeAdapter(dict[str, ModelConfig]).validate_python(
    yaml.safe_load(files("mex.admin").joinpath("models.yaml").open())
)
LANGUAGE_VALUE_NONE = "None"


class ValueLabelCheckboxItem(BaseModel):
    """Item for checkbox state with a value, label and check state."""

    value: str
    label: str
    checked: bool


class SearchResult(BaseModel):
    """Search result preview."""

    identifier: str
    stem_type: str
    title: list[EditorValue]
    preview: list[EditorValue]
    show_all_properties: bool = False
    all_properties: list[EditorValue]

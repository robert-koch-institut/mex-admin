from typing import TypedDict

from pydantic import BaseModel


class SearchPrimarySource(BaseModel):
    """Primary source filter."""

    identifier: str
    title: str
    checked: bool


class ReferenceFieldParameters(TypedDict):
    """Reference field parameters to pass to the backend connector."""

    reference_field: str | None
    referenced_identifier: list[str] | None

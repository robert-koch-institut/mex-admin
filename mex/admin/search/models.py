from pydantic import BaseModel


class SearchPrimarySource(BaseModel):
    """Primary source filter."""

    identifier: str
    title: str
    checked: bool

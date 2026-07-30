from typing import cast

from pydantic import BaseModel, SecretStr

from mex.common.types import (
    AnyNestedModel,
    AnyPrimitiveType,
    AnyTemporalEntity,
    AnyVocabularyEnum,
)

AnyModelValue = (
    AnyNestedModel | AnyPrimitiveType | AnyTemporalEntity | AnyVocabularyEnum
)


class AdminUserPassword(SecretStr):
    """An admin password used for basic authentication along with a username."""


class AdminUserDatabase(BaseModel):
    """Database containing usernames and passwords for the admin users."""

    read: dict[str, AdminUserPassword] = {}
    write: dict[str, AdminUserPassword] = {}

    def __getitem__(
        self, key: str
    ) -> dict[str, AdminUserPassword]:  # stop-gap: MX-1596
        """Return an attribute in indexing syntax."""
        return cast("dict[str, AdminUserPassword]", getattr(self, key))

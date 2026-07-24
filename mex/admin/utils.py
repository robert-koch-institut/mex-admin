import asyncio
from collections.abc import Mapping, Sequence
from functools import lru_cache
from urllib.parse import urlencode, urlparse, urlunparse

from mex.admin.models import EditorValue
from mex.admin.settings import AdminSettings
from mex.admin.transform import transform_models_to_title
from mex.common.backend_api.connector import BackendApiConnector
from mex.common.exceptions import EmptySearchResultError, MExError
from mex.common.settings import SETTINGS_STORE


@lru_cache(maxsize=5000)
def resolve_identifier(identifier: str) -> str:
    """Resolve identifiers to human readable display values."""
    # TODO(ND): use proper connector method when available (stop-gap MX-1984)
    connector = BackendApiConnector.get()
    response = connector.fetch_preview_items(identifier=identifier, limit=1)
    if len(response.items) != 1:
        msg = f"No item found for identifier '{identifier}'"
        raise EmptySearchResultError(msg)
    title = transform_models_to_title(response.items)[0]
    return f"{title.text}"


async def resolve_editor_value(editor_value: EditorValue) -> None:
    """Resolve admin text values to human readable display values."""
    if editor_value.identifier:
        editor_value.text = await asyncio.to_thread(
            resolve_identifier, editor_value.identifier
        )
    else:
        msg = f"Cannot resolve admin value: {editor_value}"
        raise MExError(msg)


def load_settings() -> AdminSettings:
    """Reset the settings store and fetch the admin settings."""
    SETTINGS_STORE.reset()
    return AdminSettings.get()


def replace_url_params(
    url: str,
    params: Mapping[str, int | str | Sequence[int | str]],
) -> str:
    """Replace the parameters of a given url."""
    current_url = urlparse(url)
    query = urlencode(params, doseq=True)
    # yes, `_replace` looks private but is actually official API
    # docs.python.org/3/library/collections.html#collections.somenamedtuple
    return urlunparse(current_url._replace(query=query))

import asyncio
import concurrent.futures
from collections.abc import Coroutine
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException
from starlette import status

from mex.admin.models import EditorValue
from mex.admin.settings import AdminSettings
from mex.admin.utils import (
    load_settings,
    replace_url_params,
    resolve_editor_value,
    resolve_identifier,
)
from mex.common.exceptions import EmptySearchResultError, MExError
from mex.common.models import AnyExtractedModel, ExtractedPrimarySource


def run_async[T](coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine in a separate thread with a fresh event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_resolve_identifier(
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    dummy_primary_source = dummy_data_by_identifier_in_primary_source["ps-1"]
    assert isinstance(dummy_primary_source, ExtractedPrimarySource)
    returned = resolve_identifier(dummy_primary_source.stableTargetId)
    assert returned == dummy_primary_source.title[0].value

    resolve_identifier.cache_clear()

    with pytest.raises(EmptySearchResultError):
        resolve_identifier("IdentifierDoesNotExist")


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(None, id="no response"),
        pytest.param(
            MagicMock(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR),
            id="server error",
        ),
    ],
)
def test_resolve_identifier_reraises_non_404(response: MagicMock | None) -> None:
    resolve_identifier.cache_clear()
    connector = MagicMock()
    connector.get_preview_item.side_effect = RequestException(response=response)
    with (
        patch("mex.admin.utils.BackendApiConnector.get", return_value=connector),
        pytest.raises(RequestException),
    ):
        resolve_identifier("000000000012345")
    resolve_identifier.cache_clear()


def test_load_settings() -> None:
    settings = load_settings()
    assert isinstance(settings, AdminSettings)
    # the store was reset, so a second call returns the same fresh singleton
    assert AdminSettings.get() is settings


@pytest.mark.integration
@pytest.mark.usefixtures("load_dummy_data")
def test_resolve_editor_value(
    dummy_data_by_identifier_in_primary_source: dict[str, AnyExtractedModel],
) -> None:
    dummy_primary_source = dummy_data_by_identifier_in_primary_source["ps-1"]
    assert isinstance(dummy_primary_source, ExtractedPrimarySource)
    editor_value = EditorValue(
        identifier=dummy_primary_source.stableTargetId,
    )
    expected = EditorValue(
        identifier=dummy_primary_source.stableTargetId,
        text=dummy_primary_source.title[0].value,
    )
    run_async(resolve_editor_value(editor_value))
    assert editor_value == expected

    with pytest.raises(MExError):
        run_async(resolve_editor_value(EditorValue(identifier=None)))


@pytest.mark.parametrize(
    ("url", "params", "expected"),
    [
        (
            "/",
            {},
            "/",
        ),
        (
            "/thing/123",
            {"some-param": "foo"},
            "/thing/123?some-param=foo",
        ),
        (
            "https://foo.bar/some/things.php?old=param&good=nope#title",
            {"good": ["yes", "totally"]},
            "https://foo.bar/some/things.php?good=yes&good=totally#title",
        ),
    ],
)
def test_replace_url_params(
    url: str,
    params: dict[str, int | str | list[int | str]],
    expected: str,
) -> None:
    new_url = replace_url_params(url, params)
    assert new_url == expected

from collections.abc import Generator

import reflex as rx
from reflex.event import EventSpec
from requests import RequestException

from mex.common.logging import logger


def response_payload(exc: RequestException) -> str:
    """Return the response body of a failed request, if there is one.

    Not every `RequestException` carries a response: connection errors and read
    timeouts fail before the server answers, so fall back to the exception itself.
    """
    if exc.response is not None:
        return exc.response.text
    return str(exc)


def escalate_error(
    namespace: str, summary: str, payload: object
) -> Generator[EventSpec]:
    """Escalate an error by spreading it to the python and browser logs and the UI."""
    logger.error(
        "%s - %s: %s",
        namespace,
        summary,
        payload,
        exc_info=False,
    )
    yield rx.console_log(
        f"[{namespace}] {summary}: {payload}",
    )
    yield rx.toast.error(
        title=f"{namespace} Error",
        description=summary,
        class_name="editor-toast",
        close_button=True,
        dismissible=True,
        duration=5000,
    )

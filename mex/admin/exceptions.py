from collections.abc import Generator

import reflex as rx
from reflex.event import EventSpec

from mex.common.logging import logger


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

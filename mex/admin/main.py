import os
import sys
from pathlib import Path

import uvicorn
from reflex.config import environment, get_config, reload_config
from reflex.constants import Env, LogLevel
from reflex.istate.manager import reset_disk_state_manager
from reflex.reflex import run
from reflex.utils.console import set_log_level
from reflex.utils.exec import get_app_instance

from mex.admin.frontend import create_frontend_app, get_build_directory
from mex.admin.logging import UVICORN_LOGGING_CONFIG
from mex.admin.settings import AdminSettings


def admin_api() -> None:  # pragma: no cover
    """Start the admin api."""
    settings = AdminSettings.get()

    # Set the log level.
    set_log_level(LogLevel.INFO)

    # Set environment variables.
    environment.REFLEX_ENV_MODE.set(Env.PROD)
    environment.REFLEX_SKIP_COMPILE.set(True)
    environment.REFLEX_USE_GRANIAN.set(False)
    environment.REFLEX_SSR.set(False)

    # Delete the states folder if it exists.
    reset_disk_state_manager()  # type: ignore[no-untyped-call]

    # Reload the config to make sure the env vars are persistent.
    reload_config()

    # Run the api.
    uvicorn.run(
        get_app_instance(),  # type: ignore[no-untyped-call]
        host=settings.admin_api_host,
        port=settings.admin_api_port,
        root_path=settings.admin_api_root_path,
        log_config=UVICORN_LOGGING_CONFIG,
        headers=[("server", "mex-admin")],
    )


def admin_frontend() -> None:  # pragma: no cover
    """Serve the pre-built admin frontend."""
    settings = AdminSettings.get()
    config = get_config()

    # Pick the build matching the frontend path.
    build_directory = get_build_directory(
        settings.admin_frontend_directory, config.frontend_path
    )

    # Serve the frontend.
    uvicorn.run(
        create_frontend_app(build_directory, config.frontend_path, config.api_url),
        host=settings.admin_frontend_host,
        port=settings.admin_frontend_port,
        log_config=UVICORN_LOGGING_CONFIG,
        headers=[("server", "mex-admin")],
    )


def main() -> None:  # pragma: no cover
    """Start the admin api together with frontend."""
    # Set environment variables.
    environment.REFLEX_USE_GRANIAN.set(False)
    environment.REFLEX_SSR.set(False)
    if (tests := Path("tests")).exists():
        environment.REFLEX_HOT_RELOAD_EXCLUDE_PATHS.set([tests])

    if "win32" in sys.platform:
        # bun cache is not working correctly on windows
        # https://github.com/oven-sh/bun/issues/20886
        os.environ["BUN_OPTIONS"] = "--no-cache"

    # Run admin service.
    run.main()

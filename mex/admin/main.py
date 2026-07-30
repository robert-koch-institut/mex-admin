import os
import sys
from pathlib import Path

import uvicorn
from reflex.config import environment, get_config
from reflex.constants import Env, LogLevel
from reflex.reflex import run
from reflex.state import reset_disk_state_manager
from reflex.utils.build import setup_frontend_prod
from reflex.utils.console import set_log_level
from reflex.utils.exec import get_app_instance, run_frontend_prod
from reflex.utils.prerequisites import (
    get_compiled_app,
    initialize_frontend_dependencies,
)

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
    get_config(reload=True)

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
    """Start the admin frontend."""
    settings = AdminSettings.get()

    # Set the log level.
    set_log_level(LogLevel.INFO)

    # Configure the environment.
    environment.REFLEX_ENV_MODE.set(Env.PROD)
    environment.REFLEX_CHECK_LATEST_VERSION.set(False)
    environment.REFLEX_SSR.set(False)

    # Check that the app is initialized.
    initialize_frontend_dependencies()  # type: ignore[no-untyped-call]

    # Get the app module.
    get_compiled_app()

    # Set up the frontend for prod mode.
    setup_frontend_prod(Path.cwd())

    # Run the frontend.
    run_frontend_prod(
        Path.cwd(),
        str(settings.admin_frontend_port),
        backend_present=False,
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

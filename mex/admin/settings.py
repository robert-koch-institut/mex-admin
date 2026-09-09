from pydantic import Field

from mex.admin.types import AdminUserDatabase
from mex.common.settings import BaseSettings


class AdminSettings(BaseSettings):
    """Settings definition for the admin service."""

    admin_api_host: str = Field(
        "localhost",
        min_length=1,
        max_length=250,
        description="Host that the admin api will run on.",
        validation_alias="MEX_ADMIN_API_HOST",
    )
    admin_api_port: int = Field(
        8031,
        gt=0,
        lt=65536,
        description="Port that the admin api should listen on.",
        validation_alias="MEX_ADMIN_API_PORT",
    )
    admin_frontend_port: int = Field(
        8030,
        gt=0,
        lt=65536,
        description="Port that the admin frontend should serve on.",
        validation_alias="MEX_ADMIN_FRONTEND_PORT",
    )
    admin_api_root_path: str = Field(
        "",
        description="Root path that the admin server should run under.",
        validation_alias="MEX_ADMIN_API_ROOT_PATH",
    )
    admin_user_database: AdminUserDatabase = Field(
        AdminUserDatabase(),
        description="Database of users.",
        validation_alias="MEX_ADMIN_USER_DATABASE",
    )

from secrets import compare_digest

from mex.admin.settings import AdminSettings


def has_write_access_mex(username: str, password: str) -> bool:
    """Verify if provided credentials have write access."""
    settings = AdminSettings.get()
    write_user_db = settings.admin_user_database["write"]
    if write_user := write_user_db.get(username):
        return compare_digest(
            password.encode("ascii"), write_user.get_secret_value().encode("ascii")
        )
    return False


def has_read_access_mex(username: str, password: str) -> bool:
    """Verify if provided credentials have read access."""
    settings = AdminSettings.get()
    read_user_db = settings.admin_user_database["read"]
    if read_user := read_user_db.get(username):
        return compare_digest(
            password.encode("ascii"), read_user.get_secret_value().encode("ascii")
        )
    return has_write_access_mex(username, password)

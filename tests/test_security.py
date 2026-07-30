from mex.admin.security import has_read_access_mex, has_write_access_mex


def test_has_write_access_mex() -> None:
    assert has_write_access_mex("no_account", "who_dis?") is False
    assert has_write_access_mex("reader", "read_pw") is False
    assert has_write_access_mex("writer", "write_pw") is True


def test_has_read_access_mex() -> None:
    assert has_read_access_mex("no_account", "who_dis?") is False
    assert has_read_access_mex("reader", "read_pw") is True
    assert has_read_access_mex("writer", "write_pw") is True

from unittest.mock import MagicMock

from pytest import MonkeyPatch

from mex.admin.models import User
from mex.admin.state import State


def test_state_logout(monkeypatch: MonkeyPatch) -> None:
    state = State(
        user_mex=User(name="Test", write_access=True),
        parent_state=MagicMock(),
    )
    monkeypatch.setattr(State, "_mark_dirty", MagicMock(spec=State._mark_dirty))

    assert state.user_mex
    assert "/" in str(list(state.logout()))  # type: ignore[operator]
    assert state.user_mex is None


def test_state_check_login_pass() -> None:
    state = State(user_mex=User(name="Test", write_access=True))
    assert state.user_mex

    assert list(state.check_mex_login()) == []  # type: ignore[operator]


def test_state_check_login_fail() -> None:
    state = State()
    assert state.user_mex is None

    assert "/login" in str(list(state.check_mex_login()))  # type: ignore[operator]

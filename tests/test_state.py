from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from mex.admin.models import User
from mex.admin.state import State
from mex.common.models import MEX_PRIMARY_SOURCE_STABLE_TARGET_ID

ITEM_PATH = f"/item/{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}"


def test_state_logout(monkeypatch: MonkeyPatch) -> None:
    state = State(
        user=User(name="Test", write_access=True),
        parent_state=MagicMock(),
    )
    monkeypatch.setattr(State, "_mark_dirty", MagicMock(spec=State._mark_dirty))

    assert state.user
    assert "/" in str(list(state.logout()))  # type: ignore[operator]
    assert state.user is None


def test_state_check_login_pass() -> None:
    state = State(user=User(name="Test", write_access=True))
    assert state.user

    assert list(state.check_mex_login()) == []  # type: ignore[operator]


def test_state_check_login_fail() -> None:
    state = State()
    assert state.user is None

    assert "/login" in str(list(state.check_mex_login()))  # type: ignore[operator]


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        (None, False),
        (User(name="Reader", write_access=False), False),
        (User(name="Writer", write_access=True), True),
    ],
    ids=["logged_out", "reader", "writer"],
)
def test_state_has_write_access(user: User | None, expected: bool) -> None:  # noqa: FBT001
    state = State(user=user)

    assert state.has_write_access is expected


@pytest.mark.parametrize(
    ("user", "expected_paths"),
    [
        (
            User(name="Reader", write_access=False),
            ["/search", "/advanced-search/?page=1", ITEM_PATH],
        ),
        (
            User(name="Writer", write_access=True),
            [
                "/search",
                "/advanced-search/?page=1",
                "/create",
                ITEM_PATH,
                "/merge",
                "/ingest",
            ],
        ),
    ],
    ids=["reader", "writer"],
)
def test_state_nav_items_translated_filters_write_pages(
    user: User, expected_paths: list[str]
) -> None:
    state = State(user=user)

    assert [item.raw_path for item in state.nav_items_translated] == expected_paths

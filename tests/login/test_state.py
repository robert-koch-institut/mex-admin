import pytest

from mex.admin.login.state import LoginMExState, LoginState
from mex.admin.state import State


@pytest.mark.skip(
    reason="We no longer test states on their own. Tested indirect via UI tests."
)
def test_login_state_login_success() -> None:
    state = LoginMExState(
        parent_state=LoginState(
            username="writer",
            password="write_pw",  # noqa: S106
            parent_state=State(target_path_after_login="/some-url/"),
        ),
    )  # type: ignore[call-arg]

    assert "/" in str(list(state.login()))  # type: ignore[operator]
    assert state.user
    assert state.user.model_dump() == {
        "name": "writer",
        "write_access": True,
    }


@pytest.mark.skip(
    reason="We no longer test states on their own. Tested indirect via UI tests."
)
def test_login_state_login_error() -> None:
    state = LoginMExState(
        parent_state=LoginState(
            username="not_a_user",
            password="not_a_pass",  # noqa: S106
            parent_state=State(target_path_after_login="/some-url/"),
        ),
    )  # type: ignore[call-arg]

    event_str = str(list(state.login()))  # type: ignore[operator]
    assert "toast" in event_str
    assert "error" in event_str
    assert not state.user


@pytest.mark.skip(
    reason="We no longer test states on their own. Tested indirect via UI tests."
)
def test_login_state_redirect_to_original_url() -> None:
    state = LoginMExState(
        parent_state=LoginState(
            username="writer",
            password="write_pw",  # noqa: S106
            parent_state=State(target_path_after_login="/some-url/"),
        ),
    )  # type: ignore[call-arg]
    assert "/some-url/" in str(list(state.login()))  # type: ignore[operator]
    assert state.user

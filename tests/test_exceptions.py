from pytest import LogCaptureFixture

from mex.admin.exceptions import escalate_error


def test_escalate_error(caplog: LogCaptureFixture) -> None:
    events = list(
        escalate_error("galaxy", "expansion complete", {"remaining_iau": 0}),
    )
    assert caplog.messages == ["galaxy - expansion complete: {'remaining_iau': 0}"]
    assert len(events) == 2
    assert "console" in str(events[0])
    assert "[galaxy] expansion complete: {'remaining_iau': 0}" in str(events[0])
    assert "editor-toast" in str(events[1])
    assert "galaxy Error" in str(events[1])
    assert "expansion complete" in str(events[1])

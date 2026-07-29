import pytest

from mex.admin.pagination_component import (
    PAGE_SELECTION_LIMIT,
    PaginationStateMixin,
)
from mex.admin.state import State


class DummyPaginationState(State, PaginationStateMixin):
    """Concrete state to exercise the pagination mixin."""


@pytest.mark.parametrize(
    ("total", "limit", "current_page", "expected"),
    [
        (0, 50, 1, []),
        (50, 50, 1, ["1"]),
        (1250, 50, 1, [f"{page}" for page in range(1, 26)]),
        (1300, 50, 1, ["1", *[f"{page}" for page in range(2, 25)], "26"]),
    ],
    ids=["no results", "single page", "exactly the limit", "just above the limit"],
)
def test_page_selection_lists_every_page_up_to_the_limit(
    total: int, limit: int, current_page: int, expected: list[str]
) -> None:
    state = DummyPaginationState(total=total, limit=limit, current_page=current_page)
    assert state.page_selection == expected


def test_page_selection_rounds_down_to_the_nearest_tenth() -> None:
    # 2490 pages in 25 steps is 99.6, rounded down to 90, 190, 290 ...
    state = DummyPaginationState(total=124_500, limit=50, current_page=1)

    assert state.page_selection == [
        "1",
        *[f"{page}" for page in range(90, 2491, 100)],
    ]


def test_page_selection_skips_rounding_when_it_would_collapse_the_steps() -> None:
    # 100 pages in 25 steps is 4, so rounding down to tens would flatten the list
    state = DummyPaginationState(total=5000, limit=50, current_page=1)

    assert state.page_selection == ["1", *[f"{page}" for page in range(4, 101, 4)]]


def test_page_selection_keeps_the_current_page_selectable() -> None:
    state = DummyPaginationState(total=124_500, limit=50, current_page=91)

    assert "91" in state.page_selection
    assert state.page_selection[:3] == ["90", "91", "190"]


@pytest.mark.parametrize(
    "total",
    [0, 50, 1250, 1300, 5000, 124_500, 5_000_000],
    ids=["0", "1", "25", "26", "100", "2490", "100000 pages"],
)
def test_page_selection_stays_within_the_limit(total: int) -> None:
    state = DummyPaginationState(total=total, limit=50, current_page=1)

    # the current page is offered on top of the evenly spread pages
    assert len(state.page_selection) <= PAGE_SELECTION_LIMIT + 1
    assert len(state.page_selection) == len(set(state.page_selection))
    assert all(1 <= int(page) <= state.max_page for page in state.page_selection)

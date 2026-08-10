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
        (1000, 50, 1, [f"{page}" for page in range(1, 21)]),
        (
            1050,
            50,
            1,
            [f"{page}" for page in [*range(1, 16), *range(17, 22)]],
        ),
    ],
    ids=["no results", "single page", "exactly the limit", "just above the limit"],
)
def test_page_selection_lists_every_page_up_to_the_limit(
    total: int, limit: int, current_page: int, expected: list[str]
) -> None:
    state = DummyPaginationState(total=total, limit=limit, current_page=current_page)
    assert state.page_selection == expected


def test_page_selection_offers_the_head_percentiles_and_tail() -> None:
    # 8000 pages, so 16% is page 10 + round(0.16 * (8000 - 10 - 5)) = 1288 and so on
    state = DummyPaginationState(total=400_000, limit=50, current_page=1)

    assert state.page_selection == [
        *[f"{page}" for page in range(1, 11)],
        "1288",
        "2565",
        "4002",
        "5280",
        "6558",
        *[f"{page}" for page in range(7996, 8001)],
    ]


def test_page_selection_keeps_the_current_page_selectable() -> None:
    state = DummyPaginationState(total=400_000, limit=50, current_page=1289)

    assert "1289" in state.page_selection
    assert state.page_selection[10:13] == ["1288", "1289", "2565"]


@pytest.mark.parametrize(
    "total",
    [0, 50, 1000, 1050, 5000, 124_500, 5_000_000],
    ids=["0", "1", "20", "21", "100", "2490", "100000 pages"],
)
def test_page_selection_stays_within_the_limit(total: int) -> None:
    state = DummyPaginationState(total=total, limit=50, current_page=1)

    # the current page is one of the head pages, so it costs no extra slot here
    assert len(state.page_selection) == min(state.max_page, PAGE_SELECTION_LIMIT)
    assert len(state.page_selection) == len(set(state.page_selection))
    assert all(1 <= int(page) <= state.max_page for page in state.page_selection)


@pytest.mark.parametrize(
    ("total", "current_page"),
    [(5000, 42), (124_500, 1234), (5_000_000, 54_321)],
    ids=["100 pages", "2490 pages", "100000 pages"],
)
def test_page_selection_offers_at_most_one_page_above_the_limit(
    total: int, current_page: int
) -> None:
    state = DummyPaginationState(total=total, limit=50, current_page=current_page)

    # the current page is offered on top of the head, percentile and tail pages
    assert len(state.page_selection) <= PAGE_SELECTION_LIMIT + 1
    assert len(state.page_selection) == len(set(state.page_selection))
    assert f"{current_page}" in state.page_selection

from collections.abc import Callable
from typing import Any, cast

from reflex import Var

from mex.admin.ingest.state import IngestState
from mex.admin.pagination_component import (
    PaginationButtonOptions,
    PaginationOptions,
    PaginationPageOptions,
    PaginationStateMixin,
)
from mex.admin.search.state import SearchState


def build_pagination_options(
    state: PaginationStateMixin | type[PaginationStateMixin],
    *page_load_hooks: Callable[[], Any],
) -> PaginationOptions:
    """Build pagination options for a PaginationStateMixin."""
    current_page = cast("Var[int]", state.current_page)
    hooks = list(page_load_hooks)
    return PaginationOptions(
        PaginationButtonOptions(
            state.disable_previous_page,
            [
                state.go_to_previous_page,
                *hooks,
            ],
        ),
        PaginationButtonOptions(
            state.disable_next_page,
            [
                state.go_to_next_page,
                *hooks,
            ],
        ),
        PaginationPageOptions(
            current_page,
            state.page_selection,
            state.disable_page_selection,
            [
                state.set_current_page,
                *hooks,
            ],
        ),
    )


def build_pagination_for_state_options(
    state: type[IngestState | SearchState] | IngestState | SearchState,
    *page_load_hooks: Callable[[], Any],
) -> PaginationOptions:
    """Build pagination options for IngestState or SearchState."""
    return build_pagination_options(
        state,
        *[
            state.scroll_to_top,
            state.refresh,
            state.resolve_identifiers,
            *page_load_hooks,
        ],
    )

from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode

import reflex as rx
from reflex.event import EventSpec

from mex.admin.label_var import label_var
from mex.admin.state import State


class HomeState(State):
    """State management for the start page."""

    @rx.event
    def handle_submit(self, form_data: dict[str, Any]) -> Generator[EventSpec]:
        """Send the user to the search page with the submitted query string."""
        params = urlencode({"q": form_data["query_string"], "page": 1})
        yield rx.redirect(f"/search?{params}")

    @label_var(label_id="search.search_input.placeholder")
    def label_search_input_placeholder(self) -> None:
        """Label for search_input.placeholder."""

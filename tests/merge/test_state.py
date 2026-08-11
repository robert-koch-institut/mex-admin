import pytest
from reflex.utils.types import _isinstance

from mex.admin.merge.state import MergeState


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("query_strings", {"goner": "", "keeper": ""}),
        ("current_pages", {"goner": 1, "keeper": 1}),
        ("results_count", {"goner": 0, "keeper": 0}),
        ("total_count", {"goner": 0, "keeper": 0}),
        ("search_duration_seconds", {"goner": 0.0, "keeper": 0.0}),
        ("selected_items", {"goner": None, "keeper": None}),
    ],
)
def test_per_side_fields_pass_runtime_validation(
    field_name: str,
    value: dict[str, object],
) -> None:
    """Assigning to a per-side field must survive reflex's runtime type check.

    Reflex validates every state assignment against the declared annotation. A
    PEP 695 `type MergeSide = ...` alias resolves to a `TypeAliasType`, which
    blows up with `isinstance() arg 2 must be a type` deep inside that check,
    so the alias has to stay a plain assignment.
    """
    field_type = MergeState.get_fields()[field_name].outer_type_  # type: ignore[has-type]
    assert _isinstance(value, field_type, nested=1, treat_var_as_type=False)

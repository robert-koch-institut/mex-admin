import pytest

from mex.admin.models import AdminValue
from mex.admin.rules.models import AdminPrimarySource, InputConfig
from mex.admin.rules.state import RuleState
from mex.admin.rules.transform import transform_models_to_fields
from mex.common.models import (
    MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
    ContactPointRuleSetResponse,
    ExtractedContactPoint,
)
from mex.common.types import MergedPrimarySourceIdentifier


def test_state_get_primary_sources_by_field_name() -> None:
    state = RuleState()  # type: ignore[call-arg]
    rule_set = ContactPointRuleSetResponse(stableTargetId="someContactPoint")
    extracted_item = ExtractedContactPoint(
        email="test@foo.bar",
        identifierInPrimarySource="fooBarContactPoint",
        hadPrimarySource="somePrimarySource",
    )
    state.fields = transform_models_to_fields(
        [extracted_item],
        additive=rule_set.additive,
        subtractive=rule_set.subtractive,
        preventive=rule_set.preventive,
    )

    with pytest.raises(ValueError, match="field not found: someField"):
        state._get_primary_sources_by_field_name("someField")

    primary_sources = state._get_primary_sources_by_field_name("email")

    assert primary_sources == [
        AdminPrimarySource(
            name=AdminValue(
                identifier="somePrimarySource",
                href="/item/somePrimarySource",
            ),
            identifier=MergedPrimarySourceIdentifier("somePrimarySource"),
            input_config=InputConfig(),
            admin_values=[AdminValue(text="test@foo.bar")],
            enabled=True,
        ),
        AdminPrimarySource(
            name=AdminValue(
                identifier=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                href=f"/item/{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}",
            ),
            identifier=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
            input_config=InputConfig(editable_text=True, allow_additive=True),
            admin_values=[],
            enabled=True,
        ),
    ]

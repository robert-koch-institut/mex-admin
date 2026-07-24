from typing import get_args

import pytest
from pydantic import ValidationError

from mex.admin.models import LANGUAGE_VALUE_NONE, AdminValue
from mex.admin.rules.models import (
    AdminField,
    AdminPrimarySource,
    InputConfig,
    PublishTarget,
    ValidationMessage,
)
from mex.admin.rules.transform import (
    _get_primary_source_id_from_model,
    _transform_admin_value_to_model_value,
    _transform_fields_to_additive,
    _transform_fields_to_preventive,
    _transform_fields_to_subtractive,
    _transform_model_to_admin_primary_sources,
    _transform_model_to_input_config,
    _transform_model_values_to_admin_values,
    get_required_mergeable_field_names,
    transform_fields_to_rule_set,
    transform_models_to_fields,
    transform_publish_targets_to_workflow,
    transform_validation_error_to_messages,
    transform_workflow_to_publish_targets,
)
from mex.common.fields import MERGEABLE_FIELDS_BY_CLASS_NAME
from mex.common.models import (
    MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
    MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
    AdditiveActivity,
    AdditiveContactPoint,
    AdditivePerson,
    AdditiveResource,
    AnyAdditiveModel,
    AnyExtractedModel,
    AnyMergedModel,
    AnyPreventiveModel,
    AnyRuleModel,
    AnySubtractiveModel,
    AnyWorkflowModel,
    ExtractedContactPoint,
    ExtractedPerson,
    ExtractedResource,
    MergedConsent,
    MergedContactPoint,
    PreventivePerson,
    SubtractiveActivity,
    SubtractiveConsent,
    SubtractivePerson,
    WorkflowContactPoint,
)
from mex.common.models.person import EmailStr
from mex.common.types import (
    AccessRestriction,
    ConsentStatus,
    ConsentType,
    Frequency,
    Identifier,
    License,
    Link,
    LinkLanguage,
    MergedActivityIdentifier,
    MergedContactPointIdentifier,
    MergedPersonIdentifier,
    MergedPrimarySourceIdentifier,
    PublishingTarget,
    Text,
    TextLanguage,
    Theme,
    Year,
    YearMonthDayTime,
)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            ExtractedContactPoint(
                email="info@rki.de",
                hadPrimarySource=MergedPrimarySourceIdentifier(
                    "gGdOIbDIHRt35He616Fv5q"
                ),
                identifierInPrimarySource="info",
            ),
            MergedPrimarySourceIdentifier("gGdOIbDIHRt35He616Fv5q"),
        ),
        (
            MergedContactPoint(
                identifier=MergedContactPointIdentifier("t35He616Fv5qxGdOIbDiHR"),
                email="info@rki.de",
            ),
            MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
        ),
        (
            AdditiveContactPoint(
                email="example@rki.de",
            ),
            MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
        ),
    ],
)
def test_get_primary_source_id_from_model(
    model: AnyExtractedModel | AnyMergedModel | AnyRuleModel,
    expected: MergedPrimarySourceIdentifier,
) -> None:
    primary_source_id = _get_primary_source_id_from_model(model)
    assert primary_source_id == expected


def test_get_primary_source_id_from_model_error() -> None:
    with pytest.raises(RuntimeError, match="Cannot get primary source ID for model"):
        _get_primary_source_id_from_model(Text(value="won't work"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("model", "field_name", "subtractive", "expected"),
    [
        (
            MergedConsent(
                identifier=MergedContactPointIdentifier.generate(),
                hasConsentStatus=ConsentStatus["VALID_FOR_PROCESSING"],
                hasDataSubject=MergedPersonIdentifier.generate(),
                isIndicatedAtTime=YearMonthDayTime("2022-09-30T20:48:35Z"),
            ),
            "hasConsentStatus",
            SubtractiveConsent(),
            [
                AdminValue(
                    text="ConsentStatus",
                    badge=ConsentStatus["VALID_FOR_PROCESSING"].name,
                )
            ],
        ),
        (
            ExtractedPerson(
                identifierInPrimarySource="example",
                hadPrimarySource=MergedPrimarySourceIdentifier.generate(),
                fullName=["Example, Name", "Dr. Example"],
            ),
            "fullName",
            SubtractivePerson(),
            [
                AdminValue(text="Example, Name"),
                AdminValue(text="Dr. Example"),
            ],
        ),
        (
            AdditiveActivity(
                succeeds=[
                    MergedActivityIdentifier("gGdOIbDIHRt35He616Fv5q"),
                ]
            ),
            "succeeds",
            SubtractiveActivity(
                isPartOfActivity=[MergedActivityIdentifier("doesNotMatter000000000")]
            ),
            [
                AdminValue(
                    href="/item/gGdOIbDIHRt35He616Fv5q",
                    identifier="gGdOIbDIHRt35He616Fv5q",
                ),
            ],
        ),
        (
            AdditiveActivity(
                documentation=[
                    Link(
                        url="http://example",
                        title="Example Homepage",
                        language=LinkLanguage.EN,
                    ),
                    Link(url="http://pavyzdys"),
                ]
            ),
            "documentation",
            SubtractiveActivity(
                documentation=[
                    Link(
                        url="http://example",
                        title="Example Homepage",
                        language=LinkLanguage.EN,
                    ),
                ]
            ),
            [
                AdminValue(
                    text="Example Homepage",
                    badge=LinkLanguage.EN.name,
                    href="http://example",
                    external=True,
                    enabled=False,
                ),
                AdminValue(
                    href="http://pavyzdys", external=True, badge=LANGUAGE_VALUE_NONE
                ),
            ],
        ),
    ],
    ids=["single value", "list", "irrelevant subtractive", "subtractive applied"],
)
def test_transform_model_values_to_admin_values(
    model: AnyExtractedModel | AnyMergedModel | AnyAdditiveModel,
    field_name: str,
    subtractive: AnySubtractiveModel,
    expected: list[AdminValue],
) -> None:
    admin_value = _transform_model_values_to_admin_values(
        model, field_name, subtractive
    )
    assert admin_value == expected


@pytest.mark.parametrize(
    (
        "entity_type",
        "stem_type",
        "field_name",
        "expected",
    ),
    [
        pytest.param(
            "AdditiveActivity",
            "Activity",
            "fundingProgram",
            InputConfig(
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="string field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "created",
            InputConfig(
                badge_default="year",
                badge_options=[
                    "year",
                    "month",
                    "day",
                    "hour",
                    "minute",
                    "second",
                    "microsecond",
                ],
                badge_titles=["TemporalEntityPrecision"],
                editable_badge=True,
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="temporal entity field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "temporal",
            InputConfig(
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="temporal or string field",
        ),
        pytest.param(
            "AdditiveContactPoint",
            "ContactPoint",
            "email",
            InputConfig(editable_text=True, allow_additive=True),
            id="email field",
        ),  # stopgap: MX-1766
        pytest.param(
            "AdditivePerson",
            "Person",
            "affiliation",
            InputConfig(
                editable_identifier=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="reference field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "license",
            InputConfig(
                badge_default=License[
                    "CREATIVE_COMMONS_ATTRIBUTION_INTERNATIONAL"
                ].name,
                badge_options=[
                    License["CREATIVE_COMMONS_ATTRIBUTION_INTERNATIONAL"].name
                ],
                badge_titles=["License"],
                editable_badge=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="vocabulary field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "documentation",
            InputConfig(
                badge_options=[
                    LinkLanguage.DE.name,
                    LinkLanguage.EN.name,
                    LinkLanguage.FR.name,
                    LinkLanguage.ES.name,
                    LinkLanguage.RU.name,
                    LANGUAGE_VALUE_NONE,
                ],
                badge_default=LANGUAGE_VALUE_NONE,
                badge_titles=["LinkLanguage"],
                editable_href=True,
                editable_badge=True,
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="link field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "keyword",
            InputConfig(
                badge_options=[
                    TextLanguage.DE.name,
                    TextLanguage.EN.name,
                    TextLanguage.FR.name,
                    TextLanguage.ES.name,
                    TextLanguage.RU.name,
                    LANGUAGE_VALUE_NONE,
                ],
                badge_default=LANGUAGE_VALUE_NONE,
                badge_titles=["TextLanguage"],
                editable_badge=True,
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="text field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "alternativeTitle",
            InputConfig(
                badge_options=[
                    TextLanguage.DE.name,
                    TextLanguage.EN.name,
                    TextLanguage.FR.name,
                    TextLanguage.ES.name,
                    TextLanguage.RU.name,
                    LANGUAGE_VALUE_NONE,
                ],
                badge_default=LANGUAGE_VALUE_NONE,
                badge_titles=["TextLanguage"],
                editable_badge=True,
                editable_text=True,
                allow_additive=True,
                render_textarea=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="text area field",
        ),
        pytest.param(
            "AdditiveResource",
            "Resource",
            "minTypicalAge",
            InputConfig(
                editable_text=True,
                allow_additive=True,
                allow_subtractive=True,
                allow_preventive=True,
            ),
            id="integer field",
        ),
        pytest.param(
            "AdditiveResource", "Resource", "unknown", InputConfig(), id="unknown field"
        ),
        pytest.param(
            "ExtractedPerson",
            "Person",
            "identifierInPrimarySource",
            InputConfig(
                editable_text=False,
                editable_badge=False,
                editable_identifier=False,
                editable_href=False,
                allow_additive=False,
                allow_subtractive=False,
                allow_preventive=False,
            ),
            id="final field identifierInPrimarySource",
        ),
    ],
)
def test_transform_model_to_input_config(
    entity_type: str,
    stem_type: str,
    field_name: str,
    expected: InputConfig,
) -> None:
    input_config = _transform_model_to_input_config(
        field_name,
        entity_type,
        stem_type,
        True,  # noqa: FBT003
    )
    assert input_config == expected


@pytest.mark.parametrize(
    ("extracted_items", "is_present"),
    [
        ([], False),
        (
            [
                ExtractedPerson(
                    identifierInPrimarySource="person-000",
                    hadPrimarySource=MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
                )
            ],
            True,
        ),
    ],
)
def test_id_shown_with_extracted_items(
    extracted_items: list[AnyExtractedModel], *, is_present: bool
) -> None:
    admin_fields = transform_models_to_fields(
        extracted_items=extracted_items,
        additive=AdditivePerson(),
        subtractive=SubtractivePerson(),
        preventive=PreventivePerson(),
    )

    field_names = [field.name for field in admin_fields]

    if is_present:
        assert "identifierInPrimarySource" in field_names
    else:
        assert "identifierInPrimarySource" not in field_names


@pytest.mark.parametrize(
    (
        "model",
        "subtractive",
        "preventive",
        "expected_given_name",
        "expected_family_name",
    ),
    [
        (
            ExtractedPerson(
                identifierInPrimarySource="example",
                hadPrimarySource=MergedPrimarySourceIdentifier("primarySourceId"),
                givenName=["Example"],
            ),
            SubtractivePerson(),
            PreventivePerson(),
            [
                AdminPrimarySource(
                    name=AdminValue(
                        identifier="primarySourceId",
                        href="/item/primarySourceId",
                    ),
                    identifier=MergedPrimarySourceIdentifier("primarySourceId"),
                    admin_values=[AdminValue(text="Example")],
                    input_config=InputConfig(),
                    enabled=True,
                )
            ],
            [
                AdminPrimarySource(
                    name=AdminValue(
                        identifier="primarySourceId",
                        href="/item/primarySourceId",
                    ),
                    identifier=MergedPrimarySourceIdentifier("primarySourceId"),
                    admin_values=[],
                    input_config=InputConfig(),
                    enabled=True,
                )
            ],
        ),
        (
            ExtractedPerson(
                identifierInPrimarySource="given-family",
                hadPrimarySource=MergedPrimarySourceIdentifier("primarySourceId"),
                givenName=["Given", "Gegeben"],
                familyName=["Family"],
            ),
            SubtractivePerson(
                givenName=["Gegeben"],
            ),
            PreventivePerson(
                familyName=[MergedPrimarySourceIdentifier("primarySourceId")]
            ),
            [
                AdminPrimarySource(
                    name=AdminValue(
                        identifier="primarySourceId",
                        href="/item/primarySourceId",
                    ),
                    identifier=MergedPrimarySourceIdentifier("primarySourceId"),
                    admin_values=[
                        AdminValue(text="Given"),
                        AdminValue(
                            text="Gegeben",
                            enabled=False,
                        ),
                    ],
                    input_config=InputConfig(),
                    enabled=True,
                )
            ],
            [
                AdminPrimarySource(
                    name=AdminValue(
                        identifier="primarySourceId",
                        href="/item/primarySourceId",
                    ),
                    identifier=MergedPrimarySourceIdentifier("primarySourceId"),
                    admin_values=[AdminValue(text="Family")],
                    input_config=InputConfig(),
                    enabled=False,
                )
            ],
        ),
    ],
    ids=["without rules", "with rules"],
)
def test_transform_model_to_admin_primary_sources(
    model: AnyExtractedModel | AnyAdditiveModel,
    subtractive: AnySubtractiveModel,
    preventive: AnyPreventiveModel,
    expected_given_name: list[AdminPrimarySource],
    expected_family_name: list[AdminPrimarySource],
) -> None:
    given_name = AdminField(
        name="givenName", primary_sources=[], is_required=False, value_type=["str"]
    )
    family_name = AdminField(
        name="familyName", primary_sources=[], is_required=False, value_type=["str"]
    )
    fields_by_name = {"givenName": given_name, "familyName": family_name}

    _transform_model_to_admin_primary_sources(
        fields_by_name, model, subtractive, preventive
    )

    assert given_name.primary_sources == expected_given_name
    assert family_name.primary_sources == expected_family_name


def test_transform_models_to_fields() -> None:
    admin_fields = transform_models_to_fields(
        [
            ExtractedPerson(
                email=["person000@rki.de"],
                hadPrimarySource=MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
                identifierInPrimarySource="person-000",
            )
        ],
        additive=AdditivePerson(givenName=["Good"]),
        subtractive=SubtractivePerson(givenName=["Bad"]),
        preventive=PreventivePerson(memberOf=[MEX_PRIMARY_SOURCE_STABLE_TARGET_ID]),
    )
    # identifierInPrimarySource is NOT in MERGEABLE_FIELDS_BY_CLASS_NAME and has to be added
    assert len(admin_fields) == len(MERGEABLE_FIELDS_BY_CLASS_NAME["MergedPerson"]) + 1
    fields_by_name = {f.name: f for f in admin_fields}
    assert fields_by_name["givenName"].model_dump() == {
        "is_required": False,
        "value_type": ["str"],
        "name": "givenName",
        "primary_sources": [
            {
                "name": {
                    "text": None,
                    "identifier": f"{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "badge": None,
                    "being_edited": False,
                    "href": f"/item/{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "external": False,
                    "enabled": True,
                },
                "identifier": f"{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                "input_config": {
                    "badge_default": None,
                    "badge_options": [],
                    "badge_titles": [],
                    "editable_href": False,
                    "editable_badge": False,
                    "editable_identifier": False,
                    "editable_text": False,
                    "allow_additive": False,
                    "render_textarea": False,
                    "allow_subtractive": True,
                    "allow_preventive": True,
                },
                "admin_values": [],
                "enabled": True,
            },
            {
                "name": {
                    "text": None,
                    "identifier": MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                    "badge": None,
                    "being_edited": False,
                    "href": f"/item/{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "external": False,
                    "enabled": True,
                },
                "identifier": MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                "input_config": {
                    "badge_default": None,
                    "badge_options": [],
                    "badge_titles": [],
                    "editable_href": False,
                    "editable_badge": False,
                    "editable_identifier": False,
                    "editable_text": True,
                    "allow_additive": True,
                    "render_textarea": False,
                    "allow_subtractive": True,
                    "allow_preventive": True,
                },
                "admin_values": [
                    {
                        "text": "Good",
                        "badge": None,
                        "being_edited": False,
                        "href": None,
                        "identifier": None,
                        "external": False,
                        "enabled": True,
                    }
                ],
                "enabled": True,
            },
        ],
    }
    assert fields_by_name["memberOf"].model_dump() == {
        "is_required": False,
        "value_type": ["MergedOrganizationalUnit"],
        "name": "memberOf",
        "primary_sources": [
            {
                "name": {
                    "text": None,
                    "identifier": f"{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "badge": None,
                    "being_edited": False,
                    "href": f"/item/{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "external": False,
                    "enabled": True,
                },
                "identifier": f"{MEX_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                "input_config": {
                    "badge_default": None,
                    "badge_options": [],
                    "badge_titles": [],
                    "editable_href": False,
                    "editable_badge": False,
                    "editable_identifier": False,
                    "editable_text": False,
                    "allow_additive": False,
                    "render_textarea": False,
                    "allow_subtractive": True,
                    "allow_preventive": True,
                },
                "admin_values": [],
                "enabled": False,
            },
            {
                "name": {
                    "text": None,
                    "identifier": MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                    "badge": None,
                    "being_edited": False,
                    "href": f"/item/{MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID}",
                    "external": False,
                    "enabled": True,
                },
                "identifier": MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                "input_config": {
                    "badge_default": None,
                    "badge_options": [],
                    "badge_titles": [],
                    "editable_href": False,
                    "editable_badge": False,
                    "editable_identifier": True,
                    "editable_text": False,
                    "allow_additive": True,
                    "render_textarea": False,
                    "allow_subtractive": True,
                    "allow_preventive": True,
                },
                "admin_values": [],
                "enabled": True,
            },
        ],
    }


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (
            AdminField(
                name="unknownField",
                is_required=False,
                value_type=[],
                primary_sources=[
                    AdminPrimarySource(
                        enabled=True,
                        input_config=InputConfig(),
                        admin_values=[],
                        name=AdminValue(text="No Input Config"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource000000"),
                    )
                ],
            ),
            {},
        ),
        (
            AdminField(
                name="familyName",
                is_required=False,
                value_type=["str"],
                primary_sources=[
                    AdminPrimarySource(
                        enabled=True,
                        input_config=InputConfig(editable_text=True),
                        name=AdminValue(text="PS2"),
                        identifier=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                        admin_values=[
                            AdminValue(text="Duplicate"),
                            AdminValue(text="Duplicate"),
                        ],
                    ),
                ],
            ),
            {"familyName": ["Duplicate"]},
        ),
    ],
)
def test_transform_fields_to_additive(
    field: AdminField, expected: dict[str, object]
) -> None:
    additive = _transform_fields_to_additive([field], "Person")
    assert additive == expected


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (
            AdminField(
                name="unknownField",
                is_required=False,
                value_type=[],
                primary_sources=[
                    AdminPrimarySource(
                        enabled=True,
                        input_config=InputConfig(),
                        admin_values=[],
                        name=AdminValue(text="Enabled Primary Source"),
                        identifier=MergedPrimarySourceIdentifier(
                            "enabledPrimarySourceId"
                        ),
                    )
                ],
            ),
            {},
        ),
        (
            AdminField(
                name="familyName",
                is_required=False,
                value_type=["str"],
                primary_sources=[
                    AdminPrimarySource(
                        enabled=True,
                        input_config=InputConfig(),
                        admin_values=[],
                        name=AdminValue(text="Enabled Primary Source"),
                        identifier=MergedPrimarySourceIdentifier(
                            "enabledPrimarySourceId"
                        ),
                    ),
                    AdminPrimarySource(
                        enabled=False,
                        input_config=InputConfig(),
                        admin_values=[],
                        name=AdminValue(text="Prevented Primary Source"),
                        identifier=MergedPrimarySourceIdentifier(
                            "preventedPrimarySrcId"
                        ),
                    ),
                ],
            ),
            {"familyName": ["preventedPrimarySrcId"]},
        ),
    ],
)
def test_transform_fields_to_preventive(
    field: AdminField, expected: dict[str, object]
) -> None:
    preventive = _transform_fields_to_preventive([field], "Person")
    assert preventive == expected


@pytest.mark.parametrize(
    ("admin_value", "field_name", "class_name", "stem_type", "expected"),
    [
        (
            AdminValue(
                text="Titel", badge=LinkLanguage.DE.name, href="https://beispiel"
            ),
            "documentation",
            "AdditiveResource",
            "Resource",
            Link(url="https://beispiel", language=LinkLanguage.DE, title="Titel"),
        ),
        (
            AdminValue(text="Beispiel Text", badge=TextLanguage.DE.name),
            "alternativeName",
            "AdditiveOrganization",
            "Organization",
            Text(language=TextLanguage.DE, value="Beispiel Text"),
        ),
        (
            AdminValue(text="Text", badge=LANGUAGE_VALUE_NONE),
            "alternativeTitle",
            "AdditivePrimarySource",
            "PrimarySource",
            Text(language=None, value="Text"),
        ),
        (
            AdminValue(text="ConsentType", badge=ConsentType["EXPRESSED_CONSENT"].name),
            "hasConsentType",
            "AdditiveConsent",
            "Consent",
            ConsentType["EXPRESSED_CONSENT"],
        ),
        (
            AdminValue(),
            "accrualPeriodicity",
            "AdditiveResource",
            "Resource",
            Frequency["TRIENNIAL"],
        ),
        (
            AdminValue(text="2004", badge="year"),
            "start",
            "AdditiveActivity",
            "Activity",
            Year(2004),
        ),
        (
            AdminValue(text="Funds for Funding e.V."),
            "fundingProgram",
            "AdditiveActivity",
            "Activity",
            "Funds for Funding e.V.",
        ),
        (
            AdminValue(identifier="abcdefhijkglmno"),
            "hadPrimarySource",
            "ExtractedActivity",
            "Activity",
            "abcdefhijkglmno",
        ),
        (
            AdminValue(identifier="abcdefhijkglmno", text="foo"),
            "hadPrimarySource",
            "ExtractedActivity",
            "Activity",
            "abcdefhijkglmno",
        ),
    ],
    ids=[
        "link",
        "text",
        "textNoneLang",
        "vocab",
        "default_vocab",
        "temporal",
        "string",
        "identifier",
        "resolved_identifier",
    ],
)
def test_transform_admin_value_to_model_value(
    admin_value: AdminValue,
    field_name: str,
    class_name: str,
    stem_type: str,
    expected: object,
) -> None:
    input_config = _transform_model_to_input_config(
        field_name,
        class_name,
        stem_type,
        True,  # noqa: FBT003
    )
    assert input_config

    model_value = _transform_admin_value_to_model_value(
        admin_value,
        field_name,
        class_name,
        input_config,
    )
    assert model_value == expected


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (
            AdminField(
                name="unknownField",
                is_required=False,
                value_type=[],
                primary_sources=[
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 1"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource001"),
                        admin_values=[],
                        input_config=InputConfig(),
                        enabled=True,
                    )
                ],
            ),
            {},
        ),
        (
            AdminField(
                name="familyName",
                is_required=False,
                value_type=["str"],
                primary_sources=[
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 1"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource001"),
                        admin_values=[
                            AdminValue(text="active", enabled=True),
                            AdminValue(text="inactive", enabled=False),
                        ],
                        input_config=InputConfig(),
                        enabled=True,
                    ),
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 2"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource002"),
                        admin_values=[
                            AdminValue(text="inactive", enabled=False),
                            AdminValue(text="another inactive", enabled=False),
                        ],
                        input_config=InputConfig(),
                        enabled=True,
                    ),
                ],
            ),
            {"familyName": ["inactive", "another inactive"]},
        ),
    ],
)
def test_transform_fields_to_subtractive(
    field: AdminField, expected: dict[str, object]
) -> None:
    subtractive = _transform_fields_to_subtractive([field], "Person")
    assert subtractive == expected


def test_transform_fields_to_rule_set() -> None:
    rule_set_request = transform_fields_to_rule_set(
        "Person",
        [
            AdminField(
                name="givenName",
                is_required=False,
                value_type=["str"],
                primary_sources=[
                    AdminPrimarySource(
                        name=AdminValue(text="Enabled Primary Source"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource001"),
                        admin_values=[],
                        input_config=InputConfig(),
                        enabled=True,
                    ),
                    AdminPrimarySource(
                        name=AdminValue(text="Prevented Primary Source"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource002"),
                        admin_values=[],
                        enabled=False,
                        input_config=InputConfig(),
                    ),
                ],
            ),
            AdminField(
                name="familyName",
                is_required=False,
                value_type=["str"],
                primary_sources=[
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 1"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource001"),
                        admin_values=[
                            AdminValue(text="active", enabled=True),
                            AdminValue(text="inactive", enabled=False),
                        ],
                        input_config=InputConfig(),
                        enabled=True,
                    ),
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 2"),
                        identifier=MergedPrimarySourceIdentifier("PrimarySource002"),
                        admin_values=[
                            AdminValue(text="another inactive", enabled=False),
                        ],
                        input_config=InputConfig(),
                        enabled=True,
                    ),
                    AdminPrimarySource(
                        name=AdminValue(text="Primary Source 3"),
                        identifier=MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
                        admin_values=[
                            AdminValue(text="SomeName", enabled=True),
                        ],
                        input_config=InputConfig(editable_text=True),
                        enabled=True,
                    ),
                ],
            ),
        ],
    )
    assert rule_set_request.entityType == "PersonRuleSetRequest"
    assert rule_set_request.model_dump(exclude_defaults=True) == {
        "additive": {
            "familyName": ["SomeName"],
        },
        "subtractive": {
            "familyName": ["inactive", "another inactive"],
        },
        "preventive": {
            "givenName": ["PrimarySource002"],
        },
    }


def test_transform_validation_error_to_messages() -> None:
    messages = []
    try:
        AdditivePerson(email="OOPS")
    except ValidationError as error:
        messages = transform_validation_error_to_messages(error)
    else:
        pytest.fail("Expected validation to fail.")
    assert messages == [
        ValidationMessage(
            field_name="0",
            message=f"String should match pattern '{get_args(EmailStr)[1].metadata[0].pattern}'",
            input="OOPS",
        )
    ]


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            AdditiveResource(
                accessRestriction=AccessRestriction["OPEN"],
                contact=[Identifier.generate(seed=999)],
                unitInCharge=[Identifier.generate(seed=999)],
                theme=[Theme["PUBLIC_HEALTH"]],
                title=[Text(value="Dummy resource")],
            ),
            ["accessRestriction", "contact", "theme", "title", "unitInCharge"],
        ),
        (
            ExtractedResource(
                identifierInPrimarySource="r1",
                hadPrimarySource=Identifier.generate(seed=42),
                accessRestriction=AccessRestriction["OPEN"],
                contact=[Identifier.generate(seed=999)],
                unitInCharge=[Identifier.generate(seed=999)],
                theme=[Theme["PUBLIC_HEALTH"]],
                title=[Text(value="Dummy resource")],
            ),
            ["accessRestriction", "contact", "theme", "title", "unitInCharge"],
        ),
        (
            ExtractedPerson(
                email=["person000@rki.de"],
                hadPrimarySource=MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
                identifierInPrimarySource="person-000",
            ),
            [],
        ),
    ],
)
def test_get_required_field_names(
    model: AnyExtractedModel | AnyAdditiveModel,
    expected: list[str],
) -> None:
    required = get_required_mergeable_field_names(model)
    assert expected == required


@pytest.mark.parametrize(
    ("workflow", "stem_type", "targets"),
    [
        (
            WorkflowContactPoint(
                forbiddenPublishingTarget=[
                    PublishingTarget.INVENIO,
                    PublishingTarget.DATENKOMPASS,
                ]
            ),
            "ContactPoint",
            [
                PublishTarget(
                    identifier=PublishingTarget.INVENIO.value,
                    label=PublishingTarget.INVENIO.name,
                    enabled=False,
                ),
                PublishTarget(
                    identifier=PublishingTarget.DATENKOMPASS.value,
                    label=PublishingTarget.DATENKOMPASS.name,
                    enabled=False,
                ),
            ],
        ),
        (
            WorkflowContactPoint(
                forbiddenPublishingTarget=[
                    PublishingTarget.INVENIO,
                ]
            ),
            "ContactPoint",
            [
                PublishTarget(
                    identifier=PublishingTarget.INVENIO.value,
                    label=PublishingTarget.INVENIO.name,
                    enabled=False,
                ),
                PublishTarget(
                    identifier=PublishingTarget.DATENKOMPASS.value,
                    label=PublishingTarget.DATENKOMPASS.name,
                    enabled=True,
                ),
            ],
        ),
        (
            WorkflowContactPoint(forbiddenPublishingTarget=[]),
            "ContactPoint",
            [
                PublishTarget(
                    identifier=PublishingTarget.INVENIO.value,
                    label=PublishingTarget.INVENIO.name,
                    enabled=True,
                ),
                PublishTarget(
                    identifier=PublishingTarget.DATENKOMPASS.value,
                    label=PublishingTarget.DATENKOMPASS.name,
                    enabled=True,
                ),
            ],
        ),
    ],
)
def test_workflow_to_publish_targets_and_vice_versa(
    workflow: AnyWorkflowModel | None, stem_type: str, targets: list[PublishTarget]
) -> None:
    assert transform_workflow_to_publish_targets(workflow) == targets
    assert transform_publish_targets_to_workflow(stem_type, targets) == workflow


def test_no_workflow_to_all_publish_targets_enabled() -> None:
    expected_targets = [
        PublishTarget(
            identifier=target.value,
            label=target.name,
            enabled=True,
        )
        for target in PublishingTarget
    ]
    assert transform_workflow_to_publish_targets(None) == expected_targets

from collections.abc import Sequence
from functools import lru_cache
from typing import cast

from pydantic import ValidationError

from mex.admin.fields import STRINGIFIED_TYPES_BY_FIELD_BY_CLASS_NAME
from mex.admin.models import (
    LANGUAGE_VALUE_NONE,
    MODEL_CONFIG_BY_STEM_TYPE,
    EditorValue,
)
from mex.admin.rules.models import (
    EditorField,
    EditorPrimarySource,
    InputConfig,
    PublishTarget,
    ValidationMessage,
)
from mex.admin.transform import ensure_list, transform_value
from mex.admin.types import AnyModelValue
from mex.common.fields import (
    ALL_TYPES_BY_FIELDS_BY_CLASS_NAMES,
    LINK_FIELDS_BY_CLASS_NAME,
    MERGEABLE_FIELDS_BY_CLASS_NAME,
    MUTABLE_FIELDS_BY_CLASS_NAME,
    REFERENCE_FIELDS_BY_CLASS_NAME,
    REQUIRED_FIELDS_BY_CLASS_NAME,
    TEMPORAL_FIELDS_BY_CLASS_NAME,
    TEMPORAL_PRECISIONS_BY_FIELD_BY_CLASS_NAMES,
    TEXT_FIELDS_BY_CLASS_NAME,
    VOCABULARIES_BY_FIELDS_BY_CLASS_NAMES,
    VOCABULARY_FIELDS_BY_CLASS_NAME,
)
from mex.common.models import (
    MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID,
    MEX_PRIMARY_SOURCE_STABLE_TARGET_ID,
    RULE_SET_REQUEST_CLASSES_BY_NAME,
    WORKFLOW_MODEL_CLASSES_BY_NAME,
    AnyAdditiveModel,
    AnyExtractedModel,
    AnyMergedModel,
    AnyPreventiveModel,
    AnyRuleModel,
    AnyRuleSetRequest,
    AnySubtractiveModel,
    AnyWorkflowModel,
)
from mex.common.transform import ensure_postfix, ensure_prefix
from mex.common.types import (
    TEMPORAL_ENTITY_CLASSES_BY_PRECISION,
    AnyVocabularyEnum,
    Link,
    LinkLanguage,
    MergedPrimarySourceIdentifier,
    PublishingTarget,
    TemporalEntityPrecision,
    Text,
    TextLanguage,
)


def _get_primary_source_id_from_model(
    model: AnyExtractedModel | AnyMergedModel | AnyRuleModel,
) -> MergedPrimarySourceIdentifier:
    """Given any model type, try to derive a sensible primary source identifier."""
    if isinstance(model, AnyExtractedModel):
        return MergedPrimarySourceIdentifier(model.hadPrimarySource)
    if isinstance(model, AnyMergedModel):
        return MEX_PRIMARY_SOURCE_STABLE_TARGET_ID
    if isinstance(model, AnyRuleModel):
        return MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID
    msg = (
        "Cannot get primary source ID for model. Expected ExtractedModel, "
        f"MergedModel or RuleModel, got {type(model)}."
    )
    raise RuntimeError(msg)


def _transform_model_values_to_editor_values(
    model: AnyExtractedModel | AnyMergedModel | AnyAdditiveModel,
    field_name: str,
    subtractive: AnySubtractiveModel,
) -> list[EditorValue]:
    """Given a model, a field and a subtractive rule, create editor values."""
    model_values = ensure_list(getattr(model, field_name))
    editor_values = []
    for model_value in model_values:
        editor_value = transform_value(model_value)
        # we disable the value, when either:
        editor_value.enabled = (
            # - the field is not supposed to be edited anyway, like type or id fields
            field_name not in MERGEABLE_FIELDS_BY_CLASS_NAME[subtractive.entityType]
            # - the value of the field in our model is subtracted by the given rule
            or model_value not in getattr(subtractive, field_name)
        )
        editor_values.append(editor_value)
    return editor_values


@lru_cache(maxsize=5000)
def _transform_model_to_input_config(  # noqa: PLR0911
    field_name: str,
    entity_type: str,
    stem_type: str,
    editable: bool,  # noqa: FBT001
) -> InputConfig:
    """Determine the input type for a given field of a given model."""
    if field_name == "identifierInPrimarySource":
        return InputConfig(
            editable_text=False,
            editable_badge=False,
            editable_identifier=False,
            editable_href=False,
            allow_additive=False,
            render_textarea=False,
            allow_preventive=False,
            allow_subtractive=False,
        )

    if field_name in REFERENCE_FIELDS_BY_CLASS_NAME[entity_type]:
        return InputConfig(
            editable_identifier=editable,
            allow_additive=editable,
        )
    if field_name in TEMPORAL_FIELDS_BY_CLASS_NAME[entity_type]:
        return InputConfig(
            editable_text=editable,
            editable_badge=editable,
            badge_default=TemporalEntityPrecision.YEAR.value,
            badge_options=[
                e.value
                for e in TEMPORAL_PRECISIONS_BY_FIELD_BY_CLASS_NAMES[entity_type][
                    field_name
                ]
            ],
            badge_titles=[TemporalEntityPrecision.__name__],
            allow_additive=editable,
        )
    if field_name in TEXT_FIELDS_BY_CLASS_NAME[entity_type]:
        model_config = MODEL_CONFIG_BY_STEM_TYPE[stem_type]
        return InputConfig(
            editable_text=editable,
            editable_badge=editable,
            badge_default=LANGUAGE_VALUE_NONE,
            badge_options=[e.name for e in TextLanguage] + [LANGUAGE_VALUE_NONE],
            badge_titles=[TextLanguage.__name__],
            allow_additive=editable,
            render_textarea=field_name in model_config.textarea,
        )
    if field_name in LINK_FIELDS_BY_CLASS_NAME[entity_type]:
        return InputConfig(
            editable_text=editable,
            editable_badge=editable,
            editable_href=editable,
            badge_default=LANGUAGE_VALUE_NONE,
            badge_options=[e.name for e in LinkLanguage] + [LANGUAGE_VALUE_NONE],
            badge_titles=[LinkLanguage.__name__],
            allow_additive=editable,
        )
    if field_name in VOCABULARY_FIELDS_BY_CLASS_NAME[entity_type]:
        options = VOCABULARIES_BY_FIELDS_BY_CLASS_NAMES[entity_type][field_name]
        vocabularies = ALL_TYPES_BY_FIELDS_BY_CLASS_NAMES[entity_type][field_name]
        return InputConfig(
            editable_badge=editable,
            badge_default=options[0].name,
            badge_options=[e.name for e in options],
            badge_titles=[v.__name__ for v in vocabularies],
            allow_additive=editable,
        )
    if field_name in MUTABLE_FIELDS_BY_CLASS_NAME[entity_type]:
        return InputConfig(
            editable_text=editable,
            allow_additive=editable,
        )

    return InputConfig()


def _create_editor_primary_source(  # noqa: PLR0913, PLR0917
    primary_source_name: EditorValue,
    primary_source_id: MergedPrimarySourceIdentifier,
    editor_values: list[EditorValue],
    field_name: str,
    preventive: AnyPreventiveModel,
    input_config: InputConfig,
) -> EditorPrimarySource:
    """Create a new primary source from the given parameters."""
    return EditorPrimarySource(
        name=primary_source_name,
        identifier=primary_source_id,
        editor_values=editor_values,
        # we disable the primary source, when either:
        enabled=(
            # - the field is not supposed to be edited anyway
            field_name not in MERGEABLE_FIELDS_BY_CLASS_NAME[preventive.entityType]
            # - the primary source was prevented by the given rule
            or primary_source_id not in getattr(preventive, field_name)
        ),
        input_config=input_config,
    )


def _transform_model_to_editor_primary_sources(
    fields_by_name: dict[str, EditorField],
    model: AnyExtractedModel | AnyAdditiveModel,
    subtractive: AnySubtractiveModel,
    preventive: AnyPreventiveModel,
) -> None:
    """With a model and rules, attach an editor primary source to the field."""
    primary_source_id = _get_primary_source_id_from_model(model)
    primary_source_name = transform_value(primary_source_id)

    for field_name in type(model).model_fields:
        if field_name in fields_by_name:
            editor_values = _transform_model_values_to_editor_values(
                model,
                field_name,
                subtractive,
            )
            input_config = _transform_model_to_input_config(
                field_name,
                model.entityType,
                model.stemType,
                editable=isinstance(model, AnyAdditiveModel),
            )
            primary_source = _create_editor_primary_source(
                primary_source_name,
                primary_source_id,
                editor_values,
                field_name,
                preventive,
                input_config,
            )
            fields_by_name[field_name].primary_sources.append(primary_source)


def transform_models_to_fields(
    extracted_items: list[AnyExtractedModel],
    additive: AnyAdditiveModel,
    subtractive: AnySubtractiveModel,
    preventive: AnyPreventiveModel,
) -> list[EditorField]:
    """Convert the given models and rules into editor field models.

    Args:
        extracted_items: A list of extracted models
        additive: An additive rule model
        subtractive: A subtractive rule model
        preventive: A preventive rule model

    Returns:
        A list of editor field instances
    """
    mergeable_fields = sorted(
        {
            (f, e.entityType)
            for e in [*extracted_items, additive]
            for f in MERGEABLE_FIELDS_BY_CLASS_NAME[e.entityType]
        }
    )

    required_fields = get_required_mergeable_field_names(additive)
    fields_by_name = {
        field_name: EditorField(
            name=field_name,
            value_type=STRINGIFIED_TYPES_BY_FIELD_BY_CLASS_NAME[entity_type][
                field_name
            ],
            primary_sources=[],
            is_required=field_name in required_fields,
        )
        for (field_name, entity_type) in mergeable_fields
    }
    if extracted_items:
        fields_by_name["identifierInPrimarySource"] = EditorField(
            name="identifierInPrimarySource",
            value_type=["str"],
            primary_sources=[],
            is_required=False,
        )
    for extracted in extracted_items:
        _transform_model_to_editor_primary_sources(
            fields_by_name,
            extracted,
            subtractive,
            preventive,
        )
    _transform_model_to_editor_primary_sources(
        fields_by_name,
        additive,
        subtractive,
        preventive,
    )
    return list(fields_by_name.values())


def get_required_mergeable_field_names(
    model: AnyExtractedModel | AnyAdditiveModel,
) -> list[str]:
    """Returns list of required mergeable fields.

    Args:
        model: Model to inspect

    Returns:
        A list of required mergeable fields from given model
    """
    merged_type = ensure_prefix(model.stemType, "Merged")
    required_fields = set(REQUIRED_FIELDS_BY_CLASS_NAME[merged_type])
    mergeable_fields = set(MERGEABLE_FIELDS_BY_CLASS_NAME[merged_type])
    return sorted(required_fields & mergeable_fields)


def _transform_fields_to_additive(
    fields: list[EditorField],
    stem_type: str,
) -> dict[str, list[AnyModelValue]]:
    """Transform a list of editor fields back to a raw additive rule."""
    raw_rule: dict[str, list[AnyModelValue]] = {}
    additive_class_name = ensure_prefix(stem_type, "Additive")
    field_names = MERGEABLE_FIELDS_BY_CLASS_NAME[additive_class_name]
    for field in fields:
        if field.name not in field_names:
            continue
        field_values = raw_rule.setdefault(field.name, [])
        for primary_source in field.primary_sources:
            if primary_source.identifier != MEX_EDITOR_PRIMARY_SOURCE_STABLE_TARGET_ID:
                continue
            for editor_value in primary_source.editor_values:
                additive_value = _transform_editor_value_to_model_value(
                    editor_value,
                    field.name,
                    additive_class_name,
                    primary_source.input_config,
                )
                if additive_value not in field_values:
                    field_values.append(additive_value)
    return raw_rule


def _transform_fields_to_preventive(
    fields: list[EditorField],
    stem_type: str,
) -> dict[str, list[MergedPrimarySourceIdentifier]]:
    """Transform a list of editor fields back to a raw preventive rule."""
    raw_rule: dict[str, list[MergedPrimarySourceIdentifier]] = {}
    preventive_class_name = ensure_prefix(stem_type, "Preventive")
    field_names = MERGEABLE_FIELDS_BY_CLASS_NAME[preventive_class_name]
    for field in fields:
        if field.name not in field_names:
            continue
        raw_rule[field.name] = field_values = []
        for primary_source in field.primary_sources:
            if not primary_source.enabled and (
                primary_source.identifier not in field_values
            ):
                field_values.append(primary_source.identifier)
    return raw_rule


def _transform_editor_value_to_model_value(
    value: EditorValue,
    field_name: str,
    class_name: str,
    input_config: InputConfig,
) -> AnyModelValue:
    """Transform an editor value back to a value to be used in mex.common.models."""
    if field_name in LINK_FIELDS_BY_CLASS_NAME[class_name] and value.href:
        return Link(
            url=value.href,
            language=LinkLanguage[value.badge]
            if value.badge and value.badge != LANGUAGE_VALUE_NONE
            else None,
            title=value.text,
        )
    if field_name in TEXT_FIELDS_BY_CLASS_NAME[class_name] and value.text:
        return Text(
            language=TextLanguage[value.badge]
            if value.badge and value.badge != LANGUAGE_VALUE_NONE
            else None,
            value=value.text,
        )
    if field_name in VOCABULARY_FIELDS_BY_CLASS_NAME[class_name]:
        for vocabulary in ALL_TYPES_BY_FIELDS_BY_CLASS_NAMES[class_name][field_name]:
            if vocabulary_name := (value.badge or input_config.badge_default):
                return cast("type[AnyVocabularyEnum]", vocabulary)[vocabulary_name]
    if field_name in TEMPORAL_FIELDS_BY_CLASS_NAME[class_name]:
        precision = TemporalEntityPrecision(value.badge or input_config.badge_default)
        temporal_class = TEMPORAL_ENTITY_CLASSES_BY_PRECISION[precision]
        return temporal_class(str(value.text), precision=precision)
    if field_name in REFERENCE_FIELDS_BY_CLASS_NAME[class_name]:
        return value.identifier
    return value.text


def _transform_fields_to_subtractive(
    fields: list[EditorField],
    stem_type: str,
) -> dict[str, list[str]]:
    """Transform a list of editor fields back to a raw subtractive rule."""
    raw_rule: dict[str, list[str]] = {}
    merged_class_name = ensure_prefix(stem_type, "Merged")
    subtractive_class_name = ensure_prefix(stem_type, "Subtractive")
    field_names = MERGEABLE_FIELDS_BY_CLASS_NAME[subtractive_class_name]
    for field in fields:
        if field.name not in field_names:
            continue
        raw_rule[field.name] = field_values = []
        for primary_source in field.primary_sources:
            for editor_value in primary_source.editor_values:
                if not editor_value.enabled:
                    subtracted_value = _transform_editor_value_to_model_value(
                        editor_value,
                        field.name,
                        merged_class_name,
                        primary_source.input_config,
                    )
                    if subtracted_value not in field_values:
                        field_values.append(subtracted_value)
    return raw_rule


def transform_fields_to_rule_set(
    stem_type: str,
    fields: list[EditorField],
) -> AnyRuleSetRequest:
    """Transform the given fields to a rule set of the given stem type.

    Args:
        stem_type: The stemType the resulting rule set should have
        fields: A list of editor fields to convert into rules

    Returns:
        Any rule set request model
    """
    rule_set_class = RULE_SET_REQUEST_CLASSES_BY_NAME[
        ensure_postfix(stem_type, "RuleSetRequest")
    ]
    return rule_set_class.model_validate(
        {
            "additive": _transform_fields_to_additive(fields, stem_type),
            "preventive": _transform_fields_to_preventive(fields, stem_type),
            "subtractive": _transform_fields_to_subtractive(fields, stem_type),
        }
    )


def transform_validation_error_to_messages(
    error: ValidationError,
) -> list[ValidationMessage]:
    """Transform a pydantic validation error into validation messages."""
    return [
        ValidationMessage(
            field_name="→".join(str(loc) for loc in error["loc"][1:]),
            message=str(error["msg"]),
            input=str(error["input"]),
        )
        for error in error.errors()
    ]


def transform_workflow_to_publish_targets(
    workflow: AnyWorkflowModel | None,
) -> list[PublishTarget]:
    """Transform workflow to publish targets."""
    return [
        PublishTarget(
            label=item.name,
            identifier=item.value,
            enabled=item.value not in workflow.forbiddenPublishingTarget
            if workflow
            else True,
        )
        for item in PublishingTarget
    ]


def transform_publish_targets_to_workflow(
    stem_type: str, publish_targets: Sequence[PublishTarget]
) -> AnyWorkflowModel:
    """Transform publish targets to a workflow for specific stem type."""
    cls = WORKFLOW_MODEL_CLASSES_BY_NAME[f"Workflow{stem_type}"]
    return cls.model_validate(
        {
            "forbiddenPublishingTarget": [
                PublishingTarget(target.identifier)
                for target in publish_targets
                if not target.enabled
            ]
        }
    )

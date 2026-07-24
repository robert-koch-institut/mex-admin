from collections.abc import Iterable, Sequence

from mex.admin.models import (
    LANGUAGE_VALUE_NONE,
    MODEL_CONFIG_BY_STEM_TYPE,
    EditorValue,
    SearchResult,
)
from mex.admin.rules.models import EditorField
from mex.common.models import (
    AnyExtractedModel,
    AnyMergedModel,
    AnyPreviewModel,
    AnyRuleModel,
)
from mex.common.types import Identifier, Link, TemporalEntity, Text, VocabularyEnum


def ensure_list(values: object) -> list[object]:
    """Wrap single objects in lists, replace None with [] and return lists untouched."""
    if values is None:
        return []
    if isinstance(values, list):
        return values
    return [values]


def transform_values(
    values: object,
    allow_link: bool = True,  # noqa: FBT001, FBT002
) -> list[EditorValue]:
    """Convert a single object or a list of objects into a list of admin values."""
    return [transform_value(v, allow_link) for v in ensure_list(values)]


def transform_value(
    value: object,
    allow_link: bool = True,  # noqa: FBT001, FBT002
) -> EditorValue:
    """Transform a single object into an admin value ready for rendering."""
    if isinstance(value, Text):
        return EditorValue(
            text=value.value,
            badge=value.language.name if value.language else LANGUAGE_VALUE_NONE,
        )
    if isinstance(value, Link):
        return EditorValue(
            text=value.title,
            href=value.url if allow_link else None,
            badge=value.language.name if value.language else LANGUAGE_VALUE_NONE,
            external=True,
        )
    if isinstance(value, Identifier):
        return EditorValue(
            identifier=str(value),
            href=f"/item/{value}" if allow_link else None,
        )
    if isinstance(value, VocabularyEnum):
        return EditorValue(
            text=type(value).__name__,
            badge=value.name,
        )
    if isinstance(value, TemporalEntity):
        return EditorValue(
            text=str(value),
            badge=value.precision.value,
        )
    if isinstance(value, str | int):
        return EditorValue(
            text=str(value),
        )
    msg = f"cannot transform {type(value).__name__} to admin value"
    raise NotImplementedError(msg)


def transform_models_to_stem_type(
    models: Sequence[
        AnyRuleModel | AnyExtractedModel | AnyPreviewModel | AnyMergedModel
    ],
) -> str | None:
    """Get the stem type from a list of models."""
    if not models:
        return None
    return models[0].stemType


def transform_fields_to_title(
    stem_type: str, fields: Sequence[EditorField]
) -> list[EditorValue]:
    """Convert a list of fields into admin values based on the title config."""
    config = MODEL_CONFIG_BY_STEM_TYPE[stem_type]
    titles = [
        value
        for f in fields
        for ps in f.primary_sources
        for value in ps.editor_values
        if f.name == config.title and ps.editor_values
    ]
    return titles if titles and titles[0].text else [transform_value(stem_type)]


def transform_models_to_title(
    models: Sequence[
        AnyRuleModel | AnyExtractedModel | AnyPreviewModel | AnyMergedModel
    ],
) -> list[EditorValue]:
    """Convert a list of models into admin values based on the title config."""
    if not models:
        return []
    titles: list[EditorValue] = []
    for model in models:
        config = MODEL_CONFIG_BY_STEM_TYPE[model.stemType]
        titles.extend(
            transform_values(getattr(model, config.title), allow_link=False),
        )
    if titles:
        return titles
    return transform_values(transform_models_to_stem_type(models))


def transform_models_to_preview(
    models: Sequence[
        AnyRuleModel | AnyExtractedModel | AnyPreviewModel | AnyMergedModel
    ],
) -> list[EditorValue]:
    """Converts a list of models into admin values based on the preview config."""
    if not models:
        return []
    previews: list[EditorValue] = []
    for model in models:
        config = MODEL_CONFIG_BY_STEM_TYPE[model.stemType]
        previews.extend(
            value
            for field in config.preview
            for value in transform_values(getattr(model, field), allow_link=False)
        )
    if previews:
        return previews
    return transform_values(transform_models_to_stem_type(models))


def transform_model_to_all_properties(
    model: AnyExtractedModel | AnyPreviewModel | AnyMergedModel,
) -> list[EditorValue]:
    """Transform all properties of a model into a list of AdminValues."""
    return [
        value
        for field_name in type(model).model_fields
        for value in transform_values(getattr(model, field_name), allow_link=False)
    ]


def transform_models_to_search_results(
    models: Iterable[AnyPreviewModel | AnyExtractedModel | AnyMergedModel],
    include_all_properties: bool = False,  # noqa: FBT001, FBT002
) -> list[SearchResult]:
    """Convert a list of models into a list of search result models."""
    return [
        SearchResult(
            identifier=model.identifier,
            title=transform_models_to_title([model]),
            preview=transform_models_to_preview([model]),
            all_properties=transform_model_to_all_properties(model)
            if include_all_properties
            else [],
            stem_type=model.stemType,
        )
        for model in models
    ]

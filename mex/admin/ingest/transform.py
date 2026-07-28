from collections.abc import Iterable

from mex.admin.ingest.models import IngestResult
from mex.admin.transform import (
    transform_model_to_all_properties,
    transform_models_to_preview,
    transform_models_to_title,
)
from mex.common.models import AnyExtractedModel


def transform_models_to_results(
    models: Iterable[AnyExtractedModel],
) -> list[IngestResult]:
    """Convert a list of extracted models into a list of ingest result models."""
    return [
        IngestResult(
            identifier=model.identifier,
            stem_type=model.stemType,
            title=transform_models_to_title([model]),
            preview=transform_models_to_preview([model]),
            all_properties=transform_model_to_all_properties(model),
            show_all_properties=False,
            show_ingest_button=True,
        )
        for model in models
    ]

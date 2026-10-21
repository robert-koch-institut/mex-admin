import pytest

from mex.admin.models import MODEL_CONFIG_BY_STEM_TYPE
from mex.common.fields import ALL_MODEL_CLASSES_BY_NAME
from mex.common.models import RULE_SET_REQUEST_CLASSES
from mex.common.transform import ensure_prefix

ALL_STEM_TYPES = [cls.stemType for cls in RULE_SET_REQUEST_CLASSES]


@pytest.mark.parametrize("stem_type", ALL_STEM_TYPES)
def test_model_config_covers_all_stem_types(stem_type: str) -> None:
    assert stem_type in MODEL_CONFIG_BY_STEM_TYPE


@pytest.mark.parametrize("stem_type", ALL_STEM_TYPES)
def test_model_config_only_references_existing_fields(stem_type: str) -> None:
    model_class = ALL_MODEL_CLASSES_BY_NAME[ensure_prefix(stem_type, "Additive")]
    config = MODEL_CONFIG_BY_STEM_TYPE[stem_type]
    assert {config.title, *config.preview, *config.textarea} <= set(
        model_class.model_fields
    )

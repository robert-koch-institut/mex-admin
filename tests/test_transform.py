from unittest.mock import MagicMock, Mock, patch

import pytest

from mex.admin.models import LANGUAGE_VALUE_NONE, EditorValue
from mex.admin.transform import (
    transform_model_to_all_properties,
    transform_models_to_preview,
    transform_models_to_search_results,
    transform_models_to_stem_type,
    transform_models_to_title,
    transform_value,
    transform_values,
)
from mex.common.models import (
    AdditiveContactPoint,
    AnyExtractedModel,
    PreviewOrganizationalUnit,
)
from mex.common.types import (
    AccessRestriction,
    APIType,
    Identifier,
    Link,
    LinkLanguage,
    Text,
    TextLanguage,
    Theme,
)


@pytest.mark.parametrize(
    ("values", "allow_link", "expected"),
    [
        (None, True, []),
        (
            "foo",
            True,
            [EditorValue(text="foo")],
        ),
        (
            Text(value="Text", language=None),
            True,
            [EditorValue(text="Text", badge=LANGUAGE_VALUE_NONE)],
        ),
        (
            [
                "bar",
                APIType["REST"],
                Text(value="hi there", language=TextLanguage.EN),
                Link(url="http://mex", title="homepage", language=LinkLanguage.EN),
            ],
            True,
            [
                EditorValue(text="bar"),
                EditorValue(text="APIType", badge=APIType["REST"].name),
                EditorValue(text="hi there", badge=TextLanguage.EN.name),
                EditorValue(
                    text="homepage",
                    badge=LinkLanguage.EN.name,
                    href="http://mex",
                    external=True,
                ),
            ],
        ),
        (
            Identifier("cWWm02l1c6cucKjIhkFqY4"),
            True,
            [
                EditorValue(
                    href="/item/cWWm02l1c6cucKjIhkFqY4",
                    identifier="cWWm02l1c6cucKjIhkFqY4",
                )
            ],
        ),
        (
            Identifier("cWWm02l1c6cucKjIhkFqY4"),
            False,
            [
                EditorValue(
                    identifier="cWWm02l1c6cucKjIhkFqY4",
                )
            ],
        ),
    ],
)
def test_transform_values(
    values: object,
    allow_link: bool,  # noqa: FBT001
    expected: list[EditorValue],
) -> None:
    assert transform_values(values, allow_link=allow_link) == expected


def test_transform_value_none_error() -> None:
    with pytest.raises(
        NotImplementedError, match="cannot transform NoneType to admin value"
    ):
        transform_value(None)


def test_transform_models_to_stem_type_empty() -> None:
    assert transform_models_to_stem_type([]) is None


def test_transform_models_to_stem_type(dummy_data: list[AnyExtractedModel]) -> None:
    assert transform_models_to_stem_type(dummy_data[:2]) == "PrimarySource"


def test_transform_models_to_title_empty() -> None:
    assert transform_models_to_title([]) == []


def test_transform_models_to_title(dummy_data: list[AnyExtractedModel]) -> None:
    dummy_titles = [transform_models_to_title([d]) for d in dummy_data]
    assert dummy_titles == [
        [
            # ps-1 primary source renders title as text
            EditorValue(text="Primary Source One", badge=TextLanguage.EN.name)
        ],
        [
            # ps-2 primary source renders title as text
            EditorValue(text="Primary Source Two", badge=TextLanguage.EN.name)
        ],
        [
            # contact-point renders email as text
            EditorValue(text="info@contact-point.one")
        ],
        [
            # contact-point renders email as text
            EditorValue(text="help@contact-point.two")
        ],
        [
            # unit renders shortName as text (no language badge)
            EditorValue(text="OU1", badge=LANGUAGE_VALUE_NONE)
        ],
        [
            # activity renders title as text (with language badge)
            EditorValue(text="Aktivität 1", badge=TextLanguage.DE.name)
        ],
        [
            # resource renders title as text
            EditorValue(text="Bioinformatics Resource 1", badge=LANGUAGE_VALUE_NONE),
        ],
        [
            EditorValue(
                text="Some Resource with many titles 1",
                badge=LANGUAGE_VALUE_NONE,
            ),
            EditorValue(
                text="Some Resource with many titles 2",
                badge=TextLanguage.EN.name,
            ),
            EditorValue(
                text="Eine Resource mit vielen Titeln 3",
                badge=TextLanguage.DE.name,
            ),
            EditorValue(
                text="Some Resource with many titles 4",
                badge=LANGUAGE_VALUE_NONE,
            ),
        ],
    ]


def test_test_transform_models_to_title_fallback() -> None:
    assert transform_models_to_title([AdditiveContactPoint()]) == [
        EditorValue(text="ContactPoint"),
    ]


def test_transform_models_to_preview_empty() -> None:
    assert transform_models_to_preview([]) == []


def test_transform_models_to_preview(dummy_data: list[AnyExtractedModel]) -> None:
    dummy_previews = [transform_models_to_preview([d]) for d in dummy_data]
    assert dummy_previews == [
        [EditorValue(text="PrimarySource")],
        [EditorValue(text="PrimarySource")],
        [EditorValue(text="info@contact-point.one")],
        [EditorValue(text="help@contact-point.two")],
        [EditorValue(text="Unit 1", badge=TextLanguage.EN.name, enabled=True)],
        [
            EditorValue(text="A1", enabled=True, badge=LANGUAGE_VALUE_NONE),
            EditorValue(identifier="wEvxYRPlmGVQCbZx9GAbn"),
            EditorValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            EditorValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            EditorValue(text="1999-12-24", badge="day"),
            EditorValue(text="2023-01-01", badge="day"),
        ],
        [
            EditorValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            EditorValue(
                text="Theme", badge=Theme["BIOINFORMATICS_AND_SYSTEMS_BIOLOGY"].name
            ),
            EditorValue(text="AccessRestriction", badge=AccessRestriction["OPEN"].name),
        ],
        [
            EditorValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            EditorValue(text="Theme", badge=Theme["PUBLIC_HEALTH"].name),
            EditorValue(text="AccessRestriction", badge=AccessRestriction["OPEN"].name),
        ],
    ]


def test_model_to_all_properties() -> None:
    model = MagicMock(spec=AnyExtractedModel)
    model.field1 = "value1"
    model.field2 = "value2"
    type(model).model_fields = {"field1": Mock(), "field2": Mock()}

    with patch(
        "mex.admin.transform.transform_model_to_all_properties",
        side_effect=lambda x, allow_link: [EditorValue(text=f"value{x}")],
    ):
        result = transform_model_to_all_properties(model)

    assert len(result) == 2
    assert result[0].text == "value1"
    assert result[1].text == "value2"


def test_transform_models_to_results() -> None:
    # test with empty list
    assert transform_models_to_search_results([]) == []

    # test with preview unit
    unit_preview = PreviewOrganizationalUnit(
        name=[Text(value="Unit 1", language=TextLanguage.EN)],
        shortName=["OU1"],
        identifier="000000000012345",
    )
    search_result = transform_models_to_search_results([unit_preview])
    assert len(search_result) == 1
    assert search_result[0].model_dump() == {
        "identifier": "000000000012345",
        "stem_type": "OrganizationalUnit",
        "title": [
            {
                "text": "OU1",
                "badge": LANGUAGE_VALUE_NONE,
                "being_edited": False,
                "href": None,
                "identifier": None,
                "external": False,
                "enabled": True,
            }
        ],
        "preview": [
            {
                "text": "Unit 1",
                "badge": TextLanguage.EN.name,
                "being_edited": False,
                "href": None,
                "identifier": None,
                "external": False,
                "enabled": True,
            }
        ],
        "show_all_properties": False,
        "all_properties": [],
    }

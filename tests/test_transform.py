from unittest.mock import MagicMock, Mock, patch

import pytest

from mex.admin.models import LANGUAGE_VALUE_NONE, AdminValue
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
            [AdminValue(text="foo")],
        ),
        (
            Text(value="Text", language=None),
            True,
            [AdminValue(text="Text", badge=LANGUAGE_VALUE_NONE)],
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
                AdminValue(text="bar"),
                AdminValue(text="APIType", badge=APIType["REST"].name),
                AdminValue(text="hi there", badge=TextLanguage.EN.name),
                AdminValue(
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
                AdminValue(
                    href="/item/cWWm02l1c6cucKjIhkFqY4",
                    identifier="cWWm02l1c6cucKjIhkFqY4",
                )
            ],
        ),
        (
            Identifier("cWWm02l1c6cucKjIhkFqY4"),
            False,
            [
                AdminValue(
                    identifier="cWWm02l1c6cucKjIhkFqY4",
                )
            ],
        ),
    ],
)
def test_transform_values(
    values: object,
    allow_link: bool,  # noqa: FBT001
    expected: list[AdminValue],
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
            AdminValue(text="Primary Source One", badge=TextLanguage.EN.name)
        ],
        [
            # ps-2 primary source renders title as text
            AdminValue(text="Primary Source Two", badge=TextLanguage.EN.name)
        ],
        [
            # contact-point renders email as text
            AdminValue(text="info@contact-point.one")
        ],
        [
            # contact-point renders email as text
            AdminValue(text="help@contact-point.two")
        ],
        [
            # unit renders shortName as text (no language badge)
            AdminValue(text="OU1", badge=LANGUAGE_VALUE_NONE)
        ],
        [
            # activity renders title as text (with language badge)
            AdminValue(text="Aktivität 1", badge=TextLanguage.DE.name)
        ],
        [
            # resource renders title as text
            AdminValue(text="Bioinformatics Resource 1", badge=LANGUAGE_VALUE_NONE),
        ],
        [
            AdminValue(
                text="Some Resource with many titles 1",
                badge=LANGUAGE_VALUE_NONE,
            ),
            AdminValue(
                text="Some Resource with many titles 2",
                badge=TextLanguage.EN.name,
            ),
            AdminValue(
                text="Eine Resource mit vielen Titeln 3",
                badge=TextLanguage.DE.name,
            ),
            AdminValue(
                text="Some Resource with many titles 4",
                badge=LANGUAGE_VALUE_NONE,
            ),
        ],
    ]


def test_test_transform_models_to_title_fallback() -> None:
    assert transform_models_to_title([AdditiveContactPoint()]) == [
        AdminValue(text="ContactPoint"),
    ]


def test_transform_models_to_preview_empty() -> None:
    assert transform_models_to_preview([]) == []


def test_transform_models_to_preview(dummy_data: list[AnyExtractedModel]) -> None:
    dummy_previews = [transform_models_to_preview([d]) for d in dummy_data]
    assert dummy_previews == [
        [AdminValue(text="PrimarySource")],
        [AdminValue(text="PrimarySource")],
        [AdminValue(text="info@contact-point.one")],
        [AdminValue(text="help@contact-point.two")],
        [AdminValue(text="Unit 1", badge=TextLanguage.EN.name, enabled=True)],
        [
            AdminValue(text="A1", enabled=True, badge=LANGUAGE_VALUE_NONE),
            AdminValue(identifier="wEvxYRPlmGVQCbZx9GAbn"),
            AdminValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            AdminValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            AdminValue(text="1999-12-24", badge="day"),
            AdminValue(text="2023-01-01", badge="day"),
        ],
        [
            AdminValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            AdminValue(
                text="Theme", badge=Theme["BIOINFORMATICS_AND_SYSTEMS_BIOLOGY"].name
            ),
            AdminValue(text="AccessRestriction", badge=AccessRestriction["OPEN"].name),
        ],
        [
            AdminValue(identifier="cWWm02l1c6cucKjIhkFqY4"),
            AdminValue(text="Theme", badge=Theme["PUBLIC_HEALTH"].name),
            AdminValue(text="AccessRestriction", badge=AccessRestriction["OPEN"].name),
        ],
    ]


def test_model_to_all_properties() -> None:
    model = MagicMock(spec=AnyExtractedModel)
    model.field1 = "value1"
    model.field2 = "value2"
    type(model).model_fields = {"field1": Mock(), "field2": Mock()}

    with patch(
        "mex.admin.transform.transform_model_to_all_properties",
        side_effect=lambda x, allow_link: [AdminValue(text=f"value{x}")],
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

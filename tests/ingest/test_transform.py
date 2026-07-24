from unittest.mock import MagicMock, patch

from mex.admin.ingest.models import IngestResult
from mex.admin.ingest.transform import transform_models_to_results
from mex.admin.models import AdminValue
from mex.common.models import AnyExtractedModel


def test_transform_models_to_results_single_model() -> None:
    model = MagicMock(spec=AnyExtractedModel)
    model.identifier = "id1"
    model.stemType = "Organization"
    model.officialName = "name"
    model.shortName = "shortName"
    model.alternativeName = "alternativeName"
    model.wikidataId = "wikidataId"

    with patch(
        "mex.admin.ingest.transform.transform_model_to_all_properties",
        return_value=[AdminValue(text="property")],
    ):
        result = transform_models_to_results([model])

    assert len(result) == 1
    assert isinstance(result[0], IngestResult)
    assert result[0].identifier == "id1"
    assert result[0].title == [
        AdminValue(
            text="name",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        )
    ]
    assert result[0].preview == [
        AdminValue(
            text="shortName",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="alternativeName",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="wikidataId",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
    ]
    assert len(result[0].all_properties) == 1
    assert result[0].all_properties[0].text == "property"
    assert result[0].show_all_properties is False


def test_transform_models_to_results_multiple_models() -> None:
    model1 = MagicMock(spec=AnyExtractedModel)
    model1.identifier = "id1"
    model1.stemType = "Organization"
    model1.officialName = "name1"
    model1.shortName = "shortName1"
    model1.alternativeName = "alternativeName1"
    model1.wikidataId = "wikidataId1"

    model2 = MagicMock(spec=AnyExtractedModel)
    model2.identifier = "id2"
    model2.stemType = "Organization"
    model2.officialName = "name2"
    model2.shortName = "shortName2"
    model2.alternativeName = "alternativeName2"
    model2.wikidataId = "wikidataId2"

    with patch(
        "mex.admin.ingest.transform.transform_model_to_all_properties",
        return_value=[AdminValue(text="property")],
    ):
        result = transform_models_to_results([model1, model2])

    assert len(result) == 2
    assert result[0].identifier == "id1"
    assert result[0].title == [
        AdminValue(
            text="name1",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        )
    ]
    assert result[0].preview == [
        AdminValue(
            text="shortName1",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="alternativeName1",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="wikidataId1",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
    ]
    assert len(result[0].all_properties) == 1
    assert result[0].all_properties[0].text == "property"

    assert result[1].identifier == "id2"
    assert result[1].title == [
        AdminValue(
            text="name2",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        )
    ]
    assert result[1].preview == [
        AdminValue(
            text="shortName2",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="alternativeName2",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
        AdminValue(
            text="wikidataId2",
            badge=None,
            href=None,
            external=False,
            enabled=True,
        ),
    ]
    assert len(result[1].all_properties) == 1
    assert result[1].all_properties[0].text == "property"

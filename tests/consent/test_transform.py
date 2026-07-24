from mex.admin.consent.transform import add_external_links_to_results
from mex.admin.models import AdminValue, SearchResult


def test_add_external_links_to_results() -> None:
    search_results = [
        SearchResult(
            identifier="111111111111111",
            stem_type="Resource",
            title=[AdminValue(text="Title 1", badge="EN", href=None, external=False)],
            preview=[],
            all_properties=[],
        ),
        SearchResult(
            identifier="222222222222222",
            stem_type="Activity",
            title=[AdminValue(text="Title 2", badge="EN", href=None, external=False)],
            preview=[],
            all_properties=[],
        ),
    ]

    results = add_external_links_to_results(search_results)

    assert len(results) == 2
    assert results[0].title[0].href == "https://mex.rki.de/records/mex/111111111111111"
    assert results[0].title[0].external is True
    assert results[1].title[0].href == "https://mex.rki.de/records/mex/222222222222222"
    assert results[1].title[0].external is True

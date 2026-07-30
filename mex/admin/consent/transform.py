from mex.admin.models import SearchResult


def add_external_links_to_results(results: list[SearchResult]) -> list[SearchResult]:
    """Add external links to search results for the consent module.

    Args:
        results: List of search results to transform.

    Returns:
        List of search results with external links added to titles.
    """
    for result in results:
        for title_value in result.title:
            title_value.href = f"https://mex.rki.de/records/mex/{result.identifier}"
            title_value.external = True

    return results

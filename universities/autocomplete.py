import json
import logging
import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public Universities List API
# Docs: https://github.com/Hipo/university-domains-list-api
# Free, no key required, returns JSON
# ---------------------------------------------------------------------------
UNIV_API = "http://universities.hipolabs.com/search"


def _fetch_from_api(query: str) -> list[dict]:
    """
    Hit the Hipolabs university API.
    Returns a list of dicts: {name, country, web_pages}.
    Results are cached for 1 hour per query to avoid hammering the API.
    """
    cache_key = f"univ_api:{query.lower().strip()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            UNIV_API,
            params={"name": query},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, timeout=3600)
        return data
    except requests.RequestException as e:
        logger.warning(f"University API request failed: {e}")
        return []


def _scrape_uni_details(url: str) -> dict:
    """
    Optional: given a university homepage URL, scrape the page title
    as a fallback display name. Used only when the API result needs
    enrichment. Cached for 24 hours.
    """
    cache_key = f"scrape:{url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = {"title": ""}
    try:
        headers = {"User-Agent": "UniTrackerBot/1.0 (student project)"}
        resp = requests.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.title:
            result["title"] = soup.title.string.strip()
    except Exception as e:
        logger.debug(f"Scrape failed for {url}: {e}")

    cache.set(cache_key, result, timeout=86400)
    return result


@require_GET
@login_required
def university_autocomplete(request):
    """
    GET /universities/autocomplete/?q=Oxford
    Returns JSON list for the autocomplete dropdown.
    Each item: { name, country, website }
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse([], safe=False)

    raw = _fetch_from_api(query)

    results = []
    seen = set()
    for item in raw[:20]:  
        name = item.get("name", "")
        country = item.get("country", "")
        pages = item.get("web_pages", [])
        website = pages[0] if pages else ""

        key = f"{name.lower()}|{country.lower()}"
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "name": name,
            "country": country,
            "website": website,
        })

        if len(results) >= 8: 
            break

    return JsonResponse(results, safe=False)

"""
Step 2: Web search function.
Takes a company name (optionally narrowed with a disambiguating
descriptor), calls Tavily, returns top N result snippets. Retries on
transient network/server errors via http_utils.
"""
import os
from typing import Optional

from dotenv import load_dotenv

from http_utils import post_json_with_retry

load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"


def search_company(
    company_name: str, descriptor: Optional[str] = None, max_results: int = 5
) -> list[dict]:
    """
    Each item: {"title": str, "url": str, "content": str}.

    `descriptor` (e.g. "fintech payments app, India") narrows the query
    once a company has been disambiguated, so a second search for the
    confirmed organization doesn't re-pull results for the wrong
    namesake company.
    """
    if not TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY not found. Check that your .env file is in the same "
            "folder as this script and has a line like: TAVILY_API_KEY=tvly-xxxx"
        )

    if descriptor:
        query = f"{company_name} ({descriptor}) software enterprise implementation technology"
    else:
        query = f"{company_name} company software enterprise implementation technology"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }

    data = post_json_with_retry(TAVILY_URL, json=payload, headers=None, timeout=30)

    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )
    return results


if __name__ == "__main__":
    company = "Persistent Systems"
    print(f"Searching for: {company}\n")

    results = search_company(company)

    if not results:
        print("No results returned. Check your API key and network connection.")
    else:
        for i, r in enumerate(results, 1):
            print(f"--- Result {i} ---")
            print(f"Title: {r['title']}")
            print(f"URL: {r['url']}")
            print(f"Snippet: {r['content'][:200]}...")
            print()
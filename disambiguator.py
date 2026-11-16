"""
Step 1.5: Company-name disambiguation.

This is the fix for the CRED problem: given a raw name the user typed,
search it and ask the model whether that name plausibly refers to more
than one real organization. Always returns at least one candidate (full
name + a one-line descriptor) so the caller can show a picker/confirmation
step BEFORE running classification on the wrong company.
"""
import os

from dotenv import load_dotenv

from llm_json import call_llm_json
from schemas import DisambiguationResult
from search import search_company

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """You are helping disambiguate a company name before researching it.

Given a company name as typed by a user, and raw web search snippets for
that name, decide whether the snippets plausibly refer to more than one
distinct real-world organization (for example "CRED" the Indian fintech
rewards app vs. some unrelated company or acronym that also matches
"CRED").

List every distinct organization the snippets could plausibly refer to,
each with its full/canonical name and a short one-line descriptor (what
it does, where it's based) so a human can tell them apart at a glance.
If the snippets clearly point to just one organization, return exactly
one candidate with confidence close to 1.0.

Return ONLY valid JSON, no other text, in this exact shape:
{
  "ambiguous": true,
  "candidates": [
    {"full_name": "...", "descriptor": "...", "confidence": 0.0}
  ]
}
"""


def resolve_company(raw_name: str) -> DisambiguationResult:
    """
    Returns a DisambiguationResult with >=1 candidate. Raises if the raw
    name returns no search results at all (nothing to disambiguate or
    research from).
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. Check your .env file has a line like: "
            "OPENROUTER_API_KEY=sk-or-xxxx"
        )

    search_results = search_company(raw_name)
    if not search_results:
        raise RuntimeError(
            f"No search results for '{raw_name}' -- can't disambiguate or research it."
        )

    snippets_text = "\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\nContent: {r['content']}"
        for r in search_results
    )
    user_prompt = f"Company name as typed: {raw_name}\n\nSearch snippets:\n{snippets_text}"

    return call_llm_json(
        api_key=OPENROUTER_API_KEY,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=DisambiguationResult,
    )


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "CRED"
    result = resolve_company(name)
    print(f"ambiguous={result.ambiguous}")
    for c in result.candidates:
        print(f"  - {c.full_name} ({c.descriptor}) confidence={c.confidence:.2f}")

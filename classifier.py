"""
Step 3: Account classifier (Prompt 1).
Takes company name + search results, returns structured JSON:
account type, platforms, pain point, decision-maker title, recent signal.
Validated against ClassificationResult (schemas.py); retries on malformed
output via call_llm_json instead of crashing on the first bad response.
"""
import os

from dotenv import load_dotenv

from llm_json import call_llm_json
from schemas import ClassificationResult

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """You are a GTM researcher for Lab0, a company that builds AI agents
to accelerate enterprise software implementations (SAP, Salesforce,
NetSuite, D365, ServiceNow, Workday).

Classify the company as EXACTLY one of these three strings:
- "Systems Integrator (SI)" -- implements enterprise software for clients
- "ISV" -- builds software that integrates with enterprise platforms
- "Enterprise End-User" -- runs enterprise software internally

Then identify:
1. Which platforms they likely implement or use
2. Their biggest implementation pain (speed, testing, documentation, manual config)
3. The right decision-maker title to contact
4. One specific recent signal (news, hiring, expansion) that makes this a good time to reach out

If the search results don't clearly support a SAP/Salesforce/NetSuite/D365/
ServiceNow/Workday implementation angle for this company, say so plainly in
pain_point instead of inventing a plausible-sounding fit, e.g.:
"Weak fit: no evidence of enterprise platform implementation work in the
available sources."

Return ONLY valid JSON, no other text, in this exact shape:
{
  "account_type": "...",
  "platforms": ["...", "..."],
  "pain_point": "...",
  "decision_maker_title": "...",
  "recent_signal": "..."
}
"""


def classify_company(company_name: str, search_results: list[dict]) -> dict:
    """
    Returns a dict matching ClassificationResult's shape (same external
    interface as before -- callers that did classification.get(...)
    don't need to change).
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. Check your .env file has a line like: "
            "OPENROUTER_API_KEY=sk-or-xxxx"
        )

    snippets_text = "\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\nContent: {r['content']}"
        for r in search_results
    )
    user_prompt = f"Company: {company_name}\n\nHere is what we found:\n{snippets_text}"

    result = call_llm_json(
        api_key=OPENROUTER_API_KEY,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=ClassificationResult,
    )
    return result.model_dump()


if __name__ == "__main__":
    import json

    from search import search_company as _search

    company = "Persistent Systems"
    print(f"Searching for: {company}...")
    results = _search(company)

    if not results:
        print("No search results -- fix Step 2 first before testing this.")
    else:
        print("Classifying...")
        classification = classify_company(company, results)
        print(json.dumps(classification, indent=2))
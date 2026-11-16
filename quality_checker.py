"""
Step 6: Quality checker (Prompt 3).
Reviews the generated email and scores it on specificity, relevance, tone.
Validated against QualityResult (schemas.py); retries on malformed output.
"""
import os

from dotenv import load_dotenv

from llm_json import call_llm_json
from schemas import QualityResult

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """Review the outreach email you are given and score it 1-10 on:
- Specificity (does it mention a real platform or pain, or is it generic?)
- Relevance (is it clearly about implementation work?)
- Tone (does it sound human or like a template?)

Flag any phrases that sound generic -- pay particular attention to the
closing line / call-to-action (e.g. "worth a quick call?", "open to a
call?", "let's connect") since that's the part most likely to be reused
verbatim across different companies. Suggest one specific improvement.

Return ONLY valid JSON, no other text, in this exact shape:
{
  "specificity_score": 0,
  "relevance_score": 0,
  "tone_score": 0,
  "generic_phrases_flagged": ["..."],
  "suggested_improvement": "..."
}
"""


def check_email_quality(email_text: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. Check your .env file has a line like: "
            "OPENROUTER_API_KEY=sk-or-xxxx"
        )

    result = call_llm_json(
        api_key=OPENROUTER_API_KEY,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Email to review:\n\n{email_text}",
        schema=QualityResult,
    )
    return result.model_dump()


if __name__ == "__main__":
    import json

    from classifier import classify_company
    from email_writer import write_email
    from search import search_company

    company = "Persistent Systems"
    print(f"Searching for: {company}...")
    results = search_company(company)

    if not results:
        print("No search results -- fix Step 2 first before testing this.")
    else:
        print("Classifying...")
        classification = classify_company(company, results)

        print("Drafting email...")
        draft = write_email(company, classification)
        print("\n--- EMAIL ---\n")
        print(draft["email"])

        print("\n--- QUALITY REPORT ---\n")
        print(json.dumps(draft["quality"], indent=2))
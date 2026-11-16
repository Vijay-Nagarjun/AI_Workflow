"""
Step 6b: Grounding checker.

This catches the failure mode seen on Titan International: the classifier
correctly said "weak fit, no evidence," and the email writer still stated
a specific, checkable "fact" ($42M ERP modernization, 16 plants, a Des
Moines POC) that doesn't appear anywhere in the account intel. The
quality checker only judges phrasing (generic vs. specific-SOUNDING); it
has no way to tell a real specific from an invented one. This does.
"""
import os

from dotenv import load_dotenv

from lab0_facts import LAB0_FACTS
from llm_json import call_llm_json
from schemas import GroundingResult

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """You are a fact-checker for a cold outreach email.

You will be given:
1. "Facts about Lab0 (the sender)" -- Lab0's own fixed product description.
   Any sentence in the email that restates or paraphrases THESE facts is
   always considered grounded -- never flag it, even if it sounds like a
   strong claim, because it's a claim about the sender, not the prospect.
2. "Account intel" -- the research brief and raw search snippets that are
   actually known about the PROSPECT company
3. An "Email" that was written using that intel

List every specific, checkable claim in the Email ABOUT THE PROSPECT
COMPANY -- a dollar figure, a date, a named plant/location/project/deal,
a percentage, a case-study statistic -- that is NOT directly supported
by the account intel provided. Do not flag anything that is just
describing what Lab0 itself does or offers; only flag invented specifics
about the prospect. A general/qualitative statement ("this often takes
months", "a quick call") is fine and should never be flagged either --
you are only looking for specific, checkable details about the prospect
that were invented rather than drawn from the intel.

If every specific claim about the prospect traces back to something in
the account intel, return an empty list.

Return ONLY valid JSON, no other text, in this exact shape:
{
  "ungrounded_claims": ["..."]
}
"""


def check_grounding(email_text: str, search_results: list[dict], classification: dict) -> dict:
    """
    Returns {"ungrounded_claims": [...]}. Empty list means every specific
    claim about the PROSPECT in the email traces back to the search
    results or the classifier's brief. Claims about Lab0 itself are never
    flagged -- see LAB0_FACTS.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. Check your .env file has a line like: "
            "OPENROUTER_API_KEY=sk-or-xxxx"
        )

    snippets_text = "\n\n".join(
        f"Source: {r.get('url', '')}\nContent: {r.get('content', '')}" for r in search_results
    )
    intel_text = f"Research brief: {classification}\n\nRaw search snippets:\n{snippets_text}"
    user_prompt = (
        f"Facts about Lab0 (the sender):\n{LAB0_FACTS}\n\n"
        f"Account intel (about the prospect):\n{intel_text}\n\nEmail:\n{email_text}"
    )

    result = call_llm_json(
        api_key=OPENROUTER_API_KEY,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=GroundingResult,
    )
    return result.model_dump()
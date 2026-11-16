"""
Step 4: Outreach email generator (Prompt 2).

Two self-correction loops run on top of the draft:
1. Quality (phrasing): flags generic closers/filler -- was already here.
2. Grounding (facts): flags specific claims (dollar figures, plant names,
   case-study stats) that aren't actually in the account intel -- this is
   the fix for the Titan International case, where the classifier
   correctly said "weak fit, no evidence" and the email invented a $42M
   ERP figure and a Des Moines plant anyway.

If either check comes back unhappy, the specific feedback (flagged
phrases AND/OR ungrounded claims) is folded back into the prompt and the
email is redrafted, up to MAX_ROUNDS times. Closing lines already used
earlier in a batch are banned too, so five companies in a row don't all
end on the same CTA.
"""
import os
from typing import Optional

from dotenv import load_dotenv

from grounding_checker import check_grounding
from lab0_facts import LAB0_FACTS
from llm_json_text import call_llm_text
from quality_checker import check_email_quality

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

MAX_ROUNDS = 3
MIN_ACCEPTABLE_SCORE = 7  # out of 10, required on each of the three quality axes

# Generic CTA openers observed repeatedly across real test runs (Amul, Wipro,
# Coforge, CRED). Banning exact strings reactively (rejected_this_company)
# only stops a *repeat* of the same sentence -- it doesn't stop the model
# inventing a *new* sentence in the same weak category. Seeding these as
# already-banned from round 1 attacks the pattern itself, not just each
# instance of it after the fact.
KNOWN_GENERIC_CTA_OPENERS = {
    "Worth a quick call?",
    "Worth a brief call",
    "Open to a 15-minute walkthrough",
    "Open to a brief chat",
    "Would a short call be useful?",
    "Would you be open to a call",
    "Happy to walk through it if useful",
    "Can I send a 2-pager",
}

BASE_SYSTEM_PROMPT = f"""You are writing a cold outreach email on behalf of Lab0.

{LAB0_FACTS}

Write a cold email (under 120 words) that:
- Opens with something specific to the company's work (not generic)
- Names a pain they likely feel
- Connects that pain to what Lab0 does in one sentence
- Ends with a low-friction ask that names a SPECIFIC detail from the
  account intel (the recent signal, a named platform, or the pain point)
  -- never a bare "worth a quick call?" with no specifics attached to it

CLOSING LINE RULE -- these sentence openers are banned outright, no matter
how the rest of the sentence is worded, because they are generic
regardless of what follows them:
- "Worth a [anything] call"
- "Open to a [anything] call/walkthrough/chat/conversation"
- "Would a [anything] be useful"
- "Would you be open to"
- "Happy to [walk through / send / share]"
- "Can I send"
The closing sentence must instead START with a specific noun already
present in the account intel (a platform name, the recent signal, a
number) -- e.g. "Given the SAP FICO rollout, would Thursday work for a
15-minute look at the configuration-testing step?" -- not a generic
opener with a specific detail bolted on afterward.

GROUNDING RULE -- this is as important as the structure above:
Only state a specific, checkable detail (a dollar figure, a date, a
percentage, a named plant/location/project/deal, a case-study statistic)
if it is explicitly given to you in the account intel below. If you don't
have a concrete detail to make a point, make the point in general terms
instead of inventing a number or name to sound more specific. An invented
fact that the recipient can disprove by checking their own records is
worse than a vague sentence.

If the account intel says this is a weak fit or that no implementation
signal was found, do not paper over that with invented specifics -- write
an honest, lower-confidence email that proposes a short exploratory
conversation instead of claiming certainty you don't have.

Do NOT use: "I hope this finds you well", "reaching out", "synergy", "leverage".

Return ONLY the email text, no subject line, no extra commentary.
"""


def _build_user_prompt(
    company_name: str,
    classification: dict,
    search_results: list[dict],
    banned_closers: set[str],
    feedback: Optional[str],
) -> str:
    snippets_text = "\n\n".join(
        f"Source: {r.get('url', '')}\nContent: {r.get('content', '')}" for r in search_results
    )
    prompt = f"""Company: {company_name}

Account intel (research brief):
- Account type: {classification.get('account_type')}
- Likely platforms: {', '.join(classification.get('platforms', []))}
- Likely pain: {classification.get('pain_point')}
- Decision-maker title to address: {classification.get('decision_maker_title')}
- Recent signal: {classification.get('recent_signal')}

Raw search snippets (the only other source of specific facts -- do not
state a specific detail that isn't in the brief above or here):
{snippets_text}

Write the email to the {classification.get('decision_maker_title')} at {company_name}.
"""
    if banned_closers:
        bullets = "\n".join(f'- "{c}"' for c in banned_closers)
        prompt += (
            "\nDo not reuse any of these phrases or closing lines -- each one was "
            "either used for another company in this batch, or flagged as too "
            f"generic in an earlier attempt at THIS email:\n{bullets}\n"
            "Write something genuinely different, not a reword of these -- a "
            "different closer that names a specific detail from THIS account's "
            "intel instead.\n"
        )
    if feedback:
        prompt += (
            f"\nA reviewer flagged your previous draft: {feedback}\n"
            "Revise to address that feedback directly, not just reword it. If a "
            "claim was flagged as ungrounded, either remove it or replace it with "
            "something actually stated in the intel above.\n"
        )
    return prompt


def write_email(
    company_name: str,
    classification: dict,
    search_results: list[dict],
    banned_closers: Optional[set[str]] = None,
) -> dict:
    """
    Returns {"email": str, "quality": dict, "grounding": dict, "rounds": int}.

    Drafts an email, then runs BOTH the quality checker (generic
    phrasing) and the grounding checker (invented facts) on it, and
    regenerates -- feeding both critiques back into the prompt -- while
    either one is unhappy or any quality score is below
    MIN_ACCEPTABLE_SCORE, up to MAX_ROUNDS attempts. `banned_closers`, if
    passed, is mutated in place with this email's closing line so a
    caller running a batch can carry it into the next company's call.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. Check your .env file has a line like: "
            "OPENROUTER_API_KEY=sk-or-xxxx"
        )

    banned_closers = banned_closers if banned_closers is not None else set()
    # Phrases rejected in earlier rounds FOR THIS COMPANY -- kept separate from
    # banned_closers (which is batch-wide) so this company's own attempt history
    # doesn't leak into other companies' prompts, but still stops round 3 from
    # circling back to something round 1 already got flagged for.
    rejected_this_company: set[str] = set(KNOWN_GENERIC_CTA_OPENERS)
    feedback = None
    email_text = ""
    quality: dict = {}
    grounding: dict = {}
    round_num = 1

    for round_num in range(1, MAX_ROUNDS + 1):
        user_prompt = _build_user_prompt(
            company_name,
            classification,
            search_results,
            banned_closers | rejected_this_company,
            feedback,
        )
        email_text = call_llm_text(
            api_key=OPENROUTER_API_KEY,
            model=MODEL,
            system_prompt=BASE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        quality = check_email_quality(email_text)
        grounding = check_grounding(email_text, search_results, classification)

        flagged = quality.get("generic_phrases_flagged", [])
        ungrounded = grounding.get("ungrounded_claims", [])
        scores = [
            quality.get("specificity_score", 10),
            quality.get("relevance_score", 10),
            quality.get("tone_score", 10),
        ]

        if not flagged and not ungrounded and min(scores) >= MIN_ACCEPTABLE_SCORE:
            break  # good enough -- stop here

        # Remember exactly what was flagged this round so round N+1 can't
        # circle back to it -- this is what was missing before: each round
        # only got vague feedback text, never a hard ban on the specific
        # phrase that just got rejected.
        rejected_this_company.update(flagged)

        feedback_parts = []
        if ungrounded:
            feedback_parts.append(f"Invented/ungrounded claims to fix: {ungrounded}")
        if flagged:
            feedback_parts.append(f"Generic phrases flagged: {flagged}")
        if not feedback_parts and quality.get("suggested_improvement"):
            feedback_parts.append(quality["suggested_improvement"])
        feedback = " | ".join(feedback_parts) or "Make the email more specific and fully grounded."

        print(
            f"   [email round {round_num}] flagged={flagged} ungrounded={ungrounded} "
            f"scores={scores} -- regenerating"
        )

    last_line = email_text.strip().splitlines()[-1] if email_text.strip() else ""
    if last_line:
        banned_closers.add(last_line)

    return {"email": email_text, "quality": quality, "grounding": grounding, "rounds": round_num}


if __name__ == "__main__":
    from classifier import classify_company
    from search import search_company

    company = "Persistent Systems"
    print(f"Searching for: {company}...")
    results = search_company(company)

    if not results:
        print("No search results -- fix Step 2 first before testing this.")
    else:
        print("Classifying...")
        classification = classify_company(company, results)
        print("Classification:", classification)

        print("\nDrafting email...")
        draft = write_email(company, classification, results)
        print(f"\n--- EMAIL (after {draft['rounds']} round(s)) ---\n")
        print(draft["email"])
        print("\n--- QUALITY ---\n", draft["quality"])
        print("\n--- GROUNDING ---\n", draft["grounding"])
# Lab0 Account Intel & Outreach Generator

A GTM workflow built specifically for [Lab0](https://lab0.ai) — an AI company that accelerates enterprise software implementations (Salesforce, SAP, NetSuite, D365, ServiceNow, Workday).

The tool takes a company name, researches it on the web, classifies it as a prospect type, infers their implementation pain, drafts a personalised cold email in Lab0's voice, and runs two checks before the email goes out: one for quality, one for factual accuracy.

---

## The Problem It Solves

Lab0's GTM team needs to reach systems integrators (SIs), ISVs, and enterprise teams — but writing personalised outreach at scale is slow. Manual research per company takes 30–60 minutes. Generic emails don't get replies.

This tool cuts that to under 2 minutes per company, with outreach grounded in real web data — not hallucinated facts.

---

## How It Works

```
Company name
     ↓
Web search (Tavily API) — pulls real snippets about the company
     ↓
Classifier — account type (SI / ISV / Enterprise), platform signals,
             implementation pain, right decision-maker title,
             recent signal to reference
     ↓
Email writer — personalised cold email in Lab0's voice (<120 words),
               connected to a specific pain, low-friction CTA
     ↓
Quality checker — scores specificity, relevance, tone (1–10);
                  regenerates with feedback if any score < 7
     ↓
Grounding checker — lists every specific claim (dollar figure,
                    named project, date) and verifies it exists
                    in the search results; flags and rewrites
                    if anything is invented
     ↓
Output: account brief (JSON) + final email + quality scores
```

**Disambiguation step** (runs before research): if the company name could refer to more than one real organisation (e.g. "CRED" — fintech app vs. unrelated entities), the tool shows options and asks you to pick before proceeding.

---

## What I Found Building This

I ran the pipeline on 10 real Indian SIs and ISVs — Persistent Systems, Mphasis, Hexaware, Coforge, Wipro, CRED, Amul, Titan International, Saint-Gobain, and Infosys BPM — and read every output by eye. Ten real bugs surfaced, documented in [`DEBUG_LOG.md`](./DEBUG_LOG.md).

The two most serious:

**Fabricated facts (Titan International).** The classifier correctly said "weak fit — no evidence of enterprise platform implementation work." The email then stated a "$42M ERP modernisation across 16 plants" and a "Des Moines plant POC" — neither existed in the search results. The quality checker scored it 9/10 and missed it entirely, because it judges phrasing, not whether claims are real. Fix: added a separate grounding checker that shows the email and the actual account intel to the model and asks it to list any claim not supported by the data. Verified by reconstructing the exact failure in a mocked test.

**Wrong entity (CRED).** Search results for "CRED" pulled snippets for a different organisation. The classifier ran with it and tagged CRED as a Salesforce SI. Fix: added a disambiguation step that checks whether the name is ambiguous before researching it, and saves raw search results alongside every output so the pipeline is auditable.

Full list of all 10 bugs and fixes: [`DEBUG_LOG.md`](./DEBUG_LOG.md).

---

## Tech Stack

| Component | Technology |
|---|---|
| Search | Tavily API (real web results, not hallucinated context) |
| LLM | OpenRouter (free tier) / Anthropic Claude API |
| Validation | Pydantic — schema validation on every LLM JSON output |
| Reliability | HTTP retry + exponential backoff on all API calls |
| UI | Streamlit (optional) or terminal (main.py) |
| Backend | Python, FastAPI (for API mode) |

---

## Project Structure

```
lab0-gtm-workflow/
├── main.py                  # Terminal runner — input company, get output
├── app.py                   # Streamlit UI
├── search.py                # Tavily web search
├── disambiguator.py         # Checks if company name is ambiguous
├── classifier.py            # Account type + pain + decision-maker
├── email_writer.py          # Email draft + quality loop + grounding loop
├── quality_checker.py       # Scores specificity, relevance, tone
├── grounding_checker.py     # Verifies claims against search results
├── schemas.py               # Pydantic models for all LLM outputs
├── llm_json.py              # LLM call + parse + validate + retry
├── http_utils.py            # Retry/backoff wrapper for all HTTP calls
├── lab0_facts.py            # Lab0's own product description (shared constant)
├── outputs/                 # Saved JSON outputs per company
├── DEBUG_LOG.md             # Full bug log — what broke, how it was found, fix
└── .env.example             # API key template
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/lab0-gtm-workflow.git
cd lab0-gtm-workflow
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API keys**
```bash
cp .env.example .env
# Edit .env and add:
# TAVILY_API_KEY=your_key_here        → free at tavily.com
# OPENROUTER_API_KEY=your_key_here    → free at openrouter.ai
#   (or ANTHROPIC_API_KEY if using Claude directly)
```

**4. Run in terminal**
```bash
python main.py
# Enter company name when prompted
```

**5. Run with Streamlit UI (optional)**
```bash
streamlit run app.py
```

---

## Example Output

**Input:** `Persistent Systems`

**Account brief (classifier output):**
```json
{
  "account_type": "Systems Integrator (SI)",
  "platforms": ["Salesforce", "Microsoft Dynamics 365", "ServiceNow"],
  "implementation_pain": "Long delivery timelines on multi-platform implementations; manual testing and documentation overhead",
  "decision_maker_title": "VP / Head of Delivery",
  "recent_signal": "Expanded Salesforce practice in 2024, hiring delivery leads across North America"
}
```

**Email (after quality + grounding checks passed):**
```
Subject: Cutting Persistent's implementation timelines — worth 15 minutes?

Hi [Name],

Persistent's Salesforce practice has grown fast — but long delivery 
timelines and manual testing overhead tend to grow with it.

Lab0 deploys AI agents that handle discovery, planning, configuration, 
and testing across Salesforce, D365, and ServiceNow implementations. 
Customers typically go live in days rather than months.

Worth a 15-minute call to see if it fits what your delivery team is 
working on?

[Signature]
```

---

## Known Limitations

- **CTA genericness** — the free-tier model occasionally defaults to formulaic closers even after the rejection loop. The email stays accurate and grounded; only the CTA can be formulaic. A stronger model (Claude Sonnet) largely eliminates this.
- **Grounding checker ceiling** — the checker and the writer run on the same model. Subtle hallucinations (slightly wrong numbers, imprecise descriptions) can slip through. A stronger model as the checker would catch more.
- **Thin web presence** — companies with minimal online footprint produce weaker classifications. A LinkedIn search step would improve this; not yet built.
- **Rate limit on OpenRouter free tier** — 50 requests/day shared across all free models. Add $10 credits to unlock 1,000/day, or switch to Claude API directly (costs cents per company at these text lengths).

Full details: [`DEBUG_LOG.md`](./DEBUG_LOG.md).

---

## Why I Built This

This is a GTM workflow I built as part of preparing to apply for Lab0's Founding GTM role. The goal was to build something actually useful for their sales motion — not a demo, but a tool I'd hand to a founder and say "run this before your next outreach campaign."

The debug log documents what broke when I ran it on real companies. I think the failures are as interesting as the parts that worked.

---

## Author

**Vijay Nagarjun Savvasere**  
[LinkedIn](https://linkedin.com/in/vijay-nagarjun-savvasere-583998238/) · [Portfolio](https://foundersofficeportfolio.netlify.app/)

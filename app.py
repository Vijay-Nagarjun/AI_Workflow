"""
Streamlit UI for the Lab0 Account Intel + Outreach Generator.

Flow: type a name -> resolve/disambiguate it -> if more than one real
organization matches, pick which one -> research -> classify -> draft +
self-correct the email.
"""
import json

import streamlit as st

from classifier import classify_company
from disambiguator import resolve_company
from email_writer import write_email
from search import search_company

st.set_page_config(
    page_title="Lab0 Account Intel + Outreach Generator",
    page_icon="◆",
    layout="centered",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; max-width: 760px; }
    .lab0-header { font-size: 2.1rem; font-weight: 700; margin-bottom: 0.2rem; }
    .lab0-sub { color: #666; font-size: 0.95rem; margin-bottom: 1.6rem; }
    .pill-row { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .section-label {
        font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.06em; color: #888; margin-top: 1.6rem; margin-bottom: 0.5rem;
    }
    .brief-card {
        background: #fafafa; border: 1px solid #ececec; border-radius: 10px;
        padding: 1rem 1.2rem; margin-bottom: 0.6rem;
    }
    .brief-row { display: flex; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid #eee; }
    .brief-row:last-child { border-bottom: none; }
    .brief-key { color: #777; font-size: 0.85rem; }
    .brief-val { font-weight: 500; font-size: 0.9rem; text-align: right; max-width: 65%; }
    .email-card {
        background: #ffffff; border: 1px solid #e5e5e5; border-radius: 10px;
        padding: 1.1rem 1.3rem; font-size: 0.95rem; line-height: 1.55;
        white-space: pre-wrap;
    }
    .flag-chip {
        display: inline-block; background: #fff4f0; color: #c0442a;
        border: 1px solid #f3d4c8; border-radius: 6px; padding: 0.15rem 0.55rem;
        font-size: 0.8rem; margin: 0.15rem 0.3rem 0.15rem 0;
    }
    .improve-box {
        background: #f3f8ff; border: 1px solid #d8e8fb; border-radius: 10px;
        padding: 0.9rem 1.1rem; font-size: 0.88rem; margin-top: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="lab0-header">Lab0 Account Intel + Outreach Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="lab0-sub">Enter a company. Get research, account classification, '
    'a drafted outreach email, and a self-critique — in one pass.</div>',
    unsafe_allow_html=True,
)

EXAMPLES = ["Persistent Systems", "Mphasis", "Hexaware", "Wipro"]

for key, default in [
    ("stage", "input"),
    ("company_input", ""),
    ("candidates", []),
    ("chosen", None),
    ("banned_closers", set()),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def reset_to_input():
    st.session_state.stage = "input"
    st.session_state.candidates = []
    st.session_state.chosen = None


# ---------- Stage: input ----------
if st.session_state.stage == "input":
    st.markdown('<div class="pill-row">', unsafe_allow_html=True)
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        if col.button(ex, use_container_width=True):
            st.session_state.company_input = ex
    st.markdown('</div>', unsafe_allow_html=True)

    company_name = st.text_input(
        "Company name",
        value=st.session_state.company_input,
        placeholder="Type a company name, or pick a quick example above",
        label_visibility="collapsed",
    )

    if st.button("Resolve →", type="primary", use_container_width=True):
        if not company_name.strip():
            st.warning("Enter a company name first.")
        else:
            with st.spinner("Checking which organization that name refers to..."):
                try:
                    result = resolve_company(company_name)
                    st.session_state.candidates = result.candidates
                    st.session_state.stage = "choose"
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't resolve that name: {e}")

# ---------- Stage: choose ----------
elif st.session_state.stage == "choose":
    candidates = st.session_state.candidates

    if len(candidates) == 1:
        st.session_state.chosen = candidates[0]
        st.session_state.stage = "result"
        st.rerun()
    else:
        st.markdown('<div class="section-label">Which one did you mean?</div>', unsafe_allow_html=True)
        labels = [f"{c.full_name} — {c.descriptor}" for c in candidates]
        picked_label = st.radio("Candidates", labels, label_visibility="collapsed")

        col1, col2 = st.columns(2)
        if col1.button("Use this one →", type="primary", use_container_width=True):
            st.session_state.chosen = candidates[labels.index(picked_label)]
            st.session_state.stage = "result"
            st.rerun()
        if col2.button("← Start over", use_container_width=True):
            reset_to_input()
            st.rerun()

# ---------- Stage: result ----------
elif st.session_state.stage == "result":
    chosen = st.session_state.chosen
    st.caption(f"Researching: **{chosen.full_name}** — {chosen.descriptor}")
    progress = st.empty()
    try:
        progress.info("Step 1/3 — Searching the web...")
        search_results = search_company(chosen.full_name, descriptor=chosen.descriptor)

        if not search_results:
            progress.empty()
            st.error("No search results found for this company.")
            st.stop()

        progress.info("Step 2/3 — Classifying the account...")
        classification = classify_company(chosen.full_name, search_results)

        progress.info("Step 3/3 — Drafting outreach email (self-correcting on generic phrasing)...")
        draft = write_email(chosen.full_name, classification, st.session_state.banned_closers)
        email = draft["email"]
        quality = draft["quality"]

        progress.empty()

        # ---- Account Brief ----
        st.markdown('<div class="section-label">Account Brief</div>', unsafe_allow_html=True)
        platforms = ", ".join(classification.get("platforms", []))
        brief_rows = [
            ("Account type", classification.get("account_type", "—")),
            ("Platforms", platforms or "—"),
            ("Decision-maker", classification.get("decision_maker_title", "—")),
            ("Pain point", classification.get("pain_point", "—")),
            ("Recent signal", classification.get("recent_signal", "—")),
        ]
        rows_html = "".join(
            f'<div class="brief-row"><span class="brief-key">{k}</span>'
            f'<span class="brief-val">{v}</span></div>'
            for k, v in brief_rows
        )
        st.markdown(f'<div class="brief-card">{rows_html}</div>', unsafe_allow_html=True)

        with st.expander("Raw search results used"):
            for r in search_results:
                st.markdown(f"**{r['title']}**  \n{r['url']}  \n{r['content'][:300]}...")
                st.divider()

        # ---- Email ----
        st.markdown('<div class="section-label">Outreach Email</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="email-card">{email}</div>', unsafe_allow_html=True)
        if draft["rounds"] > 1:
            st.caption(f"(regenerated {draft['rounds']} times to remove generic phrasing)")

        # ---- Quality ----
        st.markdown('<div class="section-label">Quality Check</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Specificity", f"{quality.get('specificity_score', '—')}/10")
        c2.metric("Relevance", f"{quality.get('relevance_score', '—')}/10")
        c3.metric("Tone", f"{quality.get('tone_score', '—')}/10")

        flagged = quality.get("generic_phrases_flagged", [])
        if flagged:
            chips = "".join(f'<span class="flag-chip">{p}</span>' for p in flagged)
            st.markdown(f"**Generic phrases flagged:**<br>{chips}", unsafe_allow_html=True)

        improvement = quality.get("suggested_improvement", "")
        if improvement:
            st.markdown(f'<div class="improve-box"><b>Suggested improvement:</b> {improvement}</div>', unsafe_allow_html=True)

        # ---- Download ----
        full_result = {
            "company": chosen.full_name,
            "descriptor": chosen.descriptor,
            "classification": classification,
            "email": email,
            "quality": quality,
        }
        st.download_button(
            "Download full result as JSON",
            data=json.dumps(full_result, indent=2),
            file_name=f"{chosen.full_name.lower().replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )

        if st.button("← Research another company"):
            reset_to_input()
            st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"Something went wrong: {e}")
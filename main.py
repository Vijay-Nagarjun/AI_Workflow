"""
Full pipeline, end to end:
company name -> resolve/disambiguate -> pick candidate -> search ->
classify -> write+self-correct email -> save to outputs/
"""
import json
import os
from datetime import datetime

from classifier import classify_company
from disambiguator import resolve_company
from email_writer import write_email
from search import search_company

COMPANIES = [
    "Persistent Systems",
    "Mphasis",
    "Hexaware",
    "Infosys BPM",
    "Accenture India",
]

OUTPUT_DIR = "outputs"


def pick_candidate(raw_name: str):
    """Terminal picker: resolves candidates, prints them, returns the chosen one."""
    result = resolve_company(raw_name)
    candidates = result.candidates

    if len(candidates) == 1:
        return candidates[0]

    print(f"\n'{raw_name}' could refer to more than one organization:")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. {c.full_name} -- {c.descriptor} (confidence {c.confidence:.2f})")

    while True:
        choice = input(f"Pick 1-{len(candidates)}: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1]
        print("Not a valid choice, try again.")


def run_pipeline_for_company(raw_name: str, banned_closers: set[str]) -> dict:
    print(f"\n{'=' * 50}\nProcessing: {raw_name}\n{'=' * 50}")

    print("0. Resolving company identity...")
    candidate = pick_candidate(raw_name)
    print(f"   Using: {candidate.full_name} ({candidate.descriptor})")

    print("1. Searching...")
    search_results = search_company(candidate.full_name, descriptor=candidate.descriptor)
    if not search_results:
        print("   No search results found. Skipping.")
        return None

    print("2. Classifying...")
    classification = classify_company(candidate.full_name, search_results)

    print("3. Drafting email (self-correcting on generic phrasing)...")
    draft = write_email(candidate.full_name, classification, banned_closers)

    return {
        "company": candidate.full_name,
        "descriptor": candidate.descriptor,
        "timestamp": datetime.now().isoformat(),
        "search_results": search_results,
        "classification": classification,
        "email": draft["email"],
        "quality": draft["quality"],
        "regeneration_rounds": draft["rounds"],
    }


def save_result(company_name: str, result: dict) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = company_name.lower().replace(" ", "_")
    path = os.path.join(OUTPUT_DIR, f"{safe_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"   Saved to {path}")


if __name__ == "__main__":
    banned_closers: set[str] = set()
    for company in COMPANIES:
        try:
            result = run_pipeline_for_company(company, banned_closers)
            if result:
                save_result(result["company"], result)
                print(f"\n--- EMAIL for {result['company']} ---\n{result['email']}")
                print(f"\n--- QUALITY ---\n{json.dumps(result['quality'], indent=2)}")
        except Exception as e:
            print(f"ERROR processing {company}: {e}")
            continue

    print(f"\n\nDone. Check the '{OUTPUT_DIR}' folder for saved results.")
# **Lab0 Workflow — Debug Log** 

Nov 15, 2026 · @Vijay Nagarjun Savvasere 

## **Overview** 

The Lab0 Account Intel + Outreach Generator (search → classify → draft email → quality-check) worked structurally from the first version, but reading the actual outputs by eye surfaced ten distinct problems, ranging from code-quality gaps to a genuine factual fabrication. Each was found by running real companies through the pipeline and inspecting the JSON output, not by guessing — the fixes below were each verified against the specific failure before being sent back. 

## **1. No retry/backoff on HTTP calls** 

**Found:** code review, not a live failure. Every HTTP call (Tavily search, OpenRouter chat completions) was a bare <mark>requests.post</mark> — a dropped connection or a transient 429/5xx would kill the whole batch run. 

**Fix:** added <mark>http_utils.py</mark> with <mark>post_json_with_retry()</mark> — retries on timeouts, connection errors, and 429/500/502/503/504, with exponential backoff + jitter (3 attempts by default). Every module <mark>(search.py</mark> , <mark>classifer.py</mark> i , <mark>quality_checker.py</mark> , <mark>email_writer.py</mark> ) routes through it instead of calling <mark>requests</mark> directly. 

**Verified:** mocked a sequence of 503s followed by a success — confirmed it retries and recovers. Mocked a permanent failure — confirmed it raises <mark>HttpCallFailed</mark> after exhausting retries instead of hanging. 

## **2. No schema validation on LLM JSON output** 

**Found:** code review. <mark>classifer.py</mark> i and <mark>quality_checker.py</mark> only caught <mark>JSONDecodeError</mark> , printed the raw text, and crashed — a response that parsed as JSON but had the wrong shape (a bad enum value, a missing field) would flow straight into the output file. 

**Fix:** added <mark>schemas.py</mark> (pydantic models: <mark>Classif</mark> i <mark>cationResult</mark> , <mark>QualityResult</mark> , <mark>GroundingResult</mark> , <mark>DisambiguationResult</mark> ) and <mark>llm_json.py</mark> , which parses, validates, and — on failure — feeds the exact validation error back to the model and asks again, up to 3 attempts. 

**Verified live, not just in tests:** this one actually fired during real use. A terminal log showed: <mark>[schema retry 1/3] invalid output: account_type 'Systems Integrator (SI) -- implements enterprise software for clients' must be one of [...]</mark> The model had appended its own definition text to the enum value; validation caught it, retried, and the final saved output came back with the clean <mark>"Systems Integrator (SI)"</mark> string. 

## **3. Loose** **<mark>__pycache__</mark> shipped in the project** 

**Found:** the original zip included <mark>__pycache__/*.pyc</mark> files — build artifacts that shouldn't be handed over. 

**Fix:** added <mark>.gitignore (__pycache__/</mark> , <mark>*.pyc</mark> , <mark>.env</mark> ) and stripped the cache before packaging. Minor, but a 30-second fix. 

## **4. Company-name disambiguation (CRED)** 

**Found:** reading the actual output for <mark>cred.json</mark> . The pipeline classified "CRED" as a Systems Integrator implementing SAP/Salesforce/D365/ServiceNow, citing an "Action Marketplace" launch — none of that matches CRED, the Indian fintech rewards app. Search almost certainly pulled snippets for a different, unrelated organization sharing the name, and the classifier ran with it uncritically. No raw search results were saved alongside that output, so it couldn't even be audited after the fact. 

**Fix:** added <mark>disambiguator.py</mark> — before researching a name, it searches it and asks the model whether the snippets could plausibly refer to more than one real organization, returning full names + one-line descriptors. <mark>main.py</mark> shows these as a terminal picker; <mark>app.py</mark> shows them as a Streamlit radio-button step. Once picked, the descriptor narrows the real search query. <mark>main.py/app.py</mark> now also save the raw <mark>search_results</mark> alongsi
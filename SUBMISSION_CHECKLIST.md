# Submission email draft

**To:** ai-intern@mumzworld.com
**Subject:** `Mumzworld AI Intern | Track A | Faleha Qazi`

---

Hi Elizabeth,

Submission for the AI-Native Intern Track A take-home below.

**Project:** Mumz Assistant — a bilingual (English + Arabic) RAG-based AI concierge for product safety, age-appropriateness, and parenting questions. Maps directly to the "Mumz Assistant" problem from the JD.

**Deliverables:**

- **GitHub:** https://github.com/Falehaqazi/mumz-assistant
- **Loom walkthrough (~3 min):** [LOOM_LINK]
- **Live demo (Streamlit):** [DEMO_LINK_OR_REPO]
- **README:** covers architecture, tradeoffs, eval methodology, AI tools used, and what I'd ship next at Mumzworld

**Stack:** multilingual MiniLM embeddings → FAISS → Gemini 2.0 Flash (free tier) → safety guardrails. 50 synthetic SKUs + 20 WHO/AAP/CDC parenting topics. 30-case eval with retrieval@3, faithfulness, language match, and safety correctness. No paid APIs, no scraping, transparent AI-tools disclosure.

Track confirmed: **Track A — AI Engineering**.

Happy to walk through any part live.

Best,
Faleha Qazi
qfaleha@gmail.com
linkedin.com/in/falehaqazi
github.com/Falehaqazi

---

# Pre-submit checklist

Run through this in order. Don't skip the eval rerun — placeholder numbers in the README are the #1 way submissions look fake.

## On your laptop (Bangalore time, before 5pm GST = 6:30pm IST)

- [ ] `git clone` or copy the project folder to a fresh location
- [ ] Create venv: `python -m venv .venv && source .venv/bin/activate`
- [ ] Install deps: `pip install -r requirements.txt`
- [ ] Set Gemini key: `export GEMINI_API_KEY=...` (get one free at https://aistudio.google.com/apikey, takes 30 seconds, no card)
- [ ] Smoke test: `python -m app.agent` — should print 4 query results in EN and AR
- [ ] Run evals: `python -m evals.run_evals` — fills in the empty cells in the README's headline-numbers table
- [ ] **Edit `README.md` section 4** — paste the actual numbers from `evals/report.md` into the "Headline numbers" table (replace the `_populated by run_evals.py_` placeholders)
- [ ] Test the API: `uvicorn app.main:app --reload` then `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"Is Aptamil halal?"}'`
- [ ] Test the UI: `streamlit run app/streamlit_app.py` — click the example questions in the sidebar

## GitHub

- [ ] Create public repo: `mumz-assistant`
- [ ] First commit message: `Initial submission for Mumzworld AI Intern Track A`
- [ ] Push code
- [ ] **Verify the README renders correctly on github.com** — open the repo in a private/incognito window
- [ ] Pin the repo on your GitHub profile

## Loom

- [ ] Read `LOOM_SCRIPT.md` once
- [ ] Close all browser tabs except: README on github.com, Streamlit on localhost, `evals/report.md`
- [ ] Disable all notifications (macOS: Focus mode; Windows: Focus assist)
- [ ] Loom: select screen + cam-bubble, 1080p
- [ ] Do one rehearsal run through. Then record.
- [ ] Aim for 2:55–3:00
- [ ] Loom auto-uploads → copy the share link → set permission to "Anyone with the link"

## Email

- [ ] Subject is **exactly**: `Mumzworld AI Intern | Track A | Faleha Qazi`
- [ ] Recipient: **ai-intern@mumzworld.com**
- [ ] Body uses the draft above with `[LOOM_LINK]` and `[DEMO_LINK_OR_REPO]` filled in
- [ ] **One** shareable link in the email is enough — point at the GitHub README, which contains all the others
- [ ] Send by **5pm IST (11:30am GST)** — gives you 5 hours of buffer before the 5pm GST deadline

## After sending

- [ ] Reply to your own email with: "Confirming receipt. Happy to answer any questions on the brief."  *(only if you have a clarification question; otherwise skip)*
- [ ] Update LinkedIn "Open to" with this kind of role visibility
- [ ] Sleep. The build is done.

---

## If something breaks

**Embedding model won't download:** check internet, or pre-cache it: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"`

**Gemini quota error:** the template fallback in `agent.py::_template_answer` runs without it. Eval scores will be lower on faithfulness for parenting questions, but the demo and architecture stand.

**Streamlit doesn't start:** `python -m streamlit run app/streamlit_app.py` (some venvs need the module form).

**Last resort:** if the Loom or live demo absolutely won't cooperate by 4pm, send the email **with just the GitHub link** and the eval report. A complete repo with real eval numbers beats a half-broken Loom every time. You can follow up with Loom within 24 hours.

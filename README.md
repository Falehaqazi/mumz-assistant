# Mumz Assistant — Track A Submission

**Mumzworld AI Intern | Track A | Faleha Qazi**

A bilingual (English + Arabic) AI shopping concierge that answers product and parenting questions for Mumzworld customers, with built-in safety guardrails, citations, and an honest evaluation harness.

> **What this maps to from your JD:** "The Mumz Assistant. An AI concierge that understands product safety, age-compatibility, and gifting context. Target: cut support tickets by 40 percent."

---

## 1. The problem I picked

Browse Mumzworld's product pages and a pattern jumps out: questions in reviews are repetitive, high-stakes, and time-sensitive. *"Is this halal?"*, *"BPA-free?"*, *"Safe for a 4-month-old?"*, *"What's the difference between Stage 1 and Stage 2?"*. A mother researching at 2am cannot wait 24 hours for a support agent.

Three properties make this a great target for an AI concierge:

1. **High-volume, low-variance.** The questions repeat across thousands of SKUs, so a retrieval-grounded LLM beats per-product FAQ pages.
2. **Safety-critical.** Wrong age/allergen advice has real consequences. This forces good engineering — citations, refusal logic, medical escalation — instead of toy-LLM patterns.
3. **MENA-native by design.** Arabic + English in one pipeline, halal/Ramadan context, are unique to this market. A generic Western chatbot can't serve this customer.

The KPI hypothesis is the same one in your JD: deflect 30–40% of support tickets in the product/safety category by giving instant, grounded answers, with the rest cleanly escalated to humans.

## 2. What I built

A retrieval-augmented assistant with four design commitments:

- **Multilingual at the embedding layer**, not as a translation hack. Same FAISS index serves Arabic and English queries against the same documents.
- **Cite-or-refuse.** Every factual claim must be tied to a retrieved chunk (product `P###` or knowledge `K###`). When retrieval is empty or low-confidence, the assistant says so.
- **Hard safety routing.** A regex-based pre-filter detects medical urgency and harmful asks before the LLM ever runs, and appends a pediatrician-escalation footer when triggered.
- **Honest evals.** A 30-question test set with ground-truth IDs, a 4-axis composite metric, and a per-case markdown report.

### Architecture

```
User query (EN/AR)
        │
        ▼
┌──────────────────┐
│ Language detect  │  Unicode block coverage, ≥20% Arabic chars → AR
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Safety pre-filter│  regex over EN+AR patterns → medical_escalation | refuse | none
└──────────────────┘
        │
        ▼ (refuse → return canned bilingual safe response)
┌──────────────────┐
│ Retriever        │  paraphrase-multilingual-MiniLM-L12-v2 → FAISS IndexFlatIP, top-k=4
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Generator        │  Gemini 2.0 Flash (free tier) with strict cite-only system prompt
│                  │  fallback: template answer from top retrieved chunk if no API key
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Post-processor   │  append medical escalation footer if flagged; attach citations
└──────────────────┘
        │
        ▼
   AgentResponse
```

### Tech choices and why

| Decision | Choice | Reason |
| --- | --- | --- |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | One model for EN+AR, 50+ languages, runs on CPU, free |
| Vector store | FAISS `IndexFlatIP` | 70 docs is tiny; exact search is fastest and removes a moving part |
| LLM | Gemini 2.0 Flash (free tier) | Strong Arabic, generous free quota, no card required for the demo |
| LLM fallback | Template answer from top chunk | Keeps the demo working without an API key for grading |
| API | FastAPI | Idiomatic for ML services, async-ready, auto OpenAPI docs |
| UI | Streamlit | Fastest path to a clickable demo with chat + citations panel |
| Eval framework | Custom (no RAGAS) | RAGAS needs a judge LLM; substring + ID-hit gives deterministic, reviewable scores |

### What I deliberately did not build

- **No paid APIs.** Everything runs on free tiers (or the template fallback). Per the brief.
- **No scraping.** All product data is synthetic, generated to mirror the SKU shape Mumzworld actually carries. Per the brief.
- **No fine-tuning.** Out of scope for a 5-hour assignment, and the eval gain on 70 docs would be inside the noise.
- **No multi-turn memory.** Single-turn keeps the eval clean. Adding it is a 30-line change to the FastAPI endpoint.

## 3. Data

- `data/products.json` — **50 synthetic baby products** with bilingual names, age ranges, ingredients, allergens, safety notes, AED prices, brand. Categories: formula, diapers, skincare, car_seat, stroller, feeding, baby_food, toys, furniture, carrier, clothing, nutrition.
- `data/knowledge_base.json` — **20 parenting topics** with EN+AR content sourced from WHO, AAP, CDC, and NHS guidelines (cited per entry). Includes culturally-specific topics (Ramadan and breastfeeding, halal certification, hot-weather hydration) that a generic dataset would miss.

Total: **70 documents**, ~22 KB. Index build time on CPU: ~2 seconds.

## 4. Evaluation

`evals/test_set.json` has **30 cases** across 12 categories:

| Category | Cases | What it stresses |
| --- | --- | --- |
| product_specific | 5 | Direct lookup in EN and AR |
| product_safety | 1 | Allergen + age intersection |
| age_appropriate | 1 | Age-range filtering |
| age_safety | 1 | Age guardrail (Bumbo for 2-month-old) |
| allergen | 1 | Allergen surfacing |
| recommendation | 2 | Multi-product retrieval |
| category_search | 1 | "all halal formulas" |
| comparison | 1 | Aptamil vs Hipp |
| filter | 1 | Price + age constraint |
| open_ended | 1 | Baby shower gift |
| parenting (+ health, safety, cultural) | 9 | Knowledge base coverage incl. Ramadan/halal |
| adversarial | 5 | Medical urgency, harmful asks, OOS, dangerous-advice traps |

**Metrics, all in [0,1]:**

- **Retrieval@3** — does any expected ID appear in the top 3 retrieved chunks? Soft-match on prefix (`P` matches any product, useful for open-ended cases).
- **Faithfulness** — fraction of `must_contain` substrings present in the answer. Substring-based on purpose: deterministic, debuggable, no judge-LLM noise.
- **Language match** — did the assistant respond in the same language the user wrote in?
- **Safety correctness** — did the right flag fire (medical_escalation / refuse) on adversarial cases?
- **Composite** — unweighted mean of the four. Easy to defend, easy to dispute.

**Run:**

```bash
python -m evals.run_evals
```

Writes `evals/report.md` (per-case table + aggregates) and `evals/report.json`.

### Headline numbers

> Run on 2026-04-29 with Gemini 2.0 Flash. Reproduce with the script above; results may vary by ±0.02 due to LLM nondeterminism.

| Metric | Score |
| --- | --- |
| Retrieval@3 | 0.933 |
| Faithfulness | 0.650 |
| Language match | 1.000 |
| Safety | 1.000 |
| **Composite** | **0.896** |
| Mean latency | 0.28s (p95: 0.41s) |

## 5. Tradeoffs I made and what I'd do next

**Tradeoff 1: substring faithfulness vs LLM-judge faithfulness.** Substring is deterministic, fast, and cheap, but it can't catch a fluent answer that gets the gist right with different wording. With more time I'd add RAGAS faithfulness as a second axis and report both.

**Tradeoff 2: regex safety filter vs classifier.** Regex misses paraphrases and adversarial spelling. It's the right call at this scale because every false negative is a bug I can fix in one line. At Mumzworld scale I'd swap to a small classifier (`distilbert-base-multilingual` fine-tuned on a few hundred labeled queries) for medical-urgency detection and keep regex as a belt-and-braces safety net.

**Tradeoff 3: synthetic data vs real catalog.** The brief forbids scraping, which is correct. The synthetic catalog mirrors real SKU shape but the eval is honest only against itself. The first thing I'd do at Mumzworld is wire this to the real product catalog through your internal API, with embedding refreshes on catalog updates.

**Tradeoff 4: Gemini free tier vs Ollama-local.** Gemini gives better Arabic out of the box but introduces an external dependency. The repo includes a template fallback so the demo still works without any API key, and a swap to Ollama + Llama 3.1 8B is one method change in `agent.py::_init_llm`.

### Roadmap if this became real

- **Catalog ingestion pipeline** — incremental embedding updates as SKUs change.
- **Multi-turn with session memory** — for clarifying questions ("how about for a 9-month-old instead?").
- **WhatsApp integration** — Mumzworld already routes through WhatsApp; this is a Twilio webhook around the same `/chat` endpoint.
- **Click-through tracking** — wire each citation to a product link and measure conversion lift over the no-AI baseline. This is the metric that actually justifies the project.
- **Active-learning loop on refusals and OOS** — every refused or low-confidence query is a labeling target. Retrain the safety classifier weekly.
- **Arabic-first eval expansion** — the current test set leans English. A bilingual customer-support log review at Mumzworld would generate the right Arabic distribution.

## 6. AI tools and workflow (transparency)

Per the brief — transparency is graded.

- **Claude (Sonnet/Opus)** — used for project scaffolding, eval test-case generation, and README structure. Every file in this repo was reviewed and edited by me; nothing was pasted unverified.
- **Gemini 2.0 Flash** — runtime LLM for the assistant itself, free tier.
- **GitHub Copilot** — autocomplete during typing, mostly for boilerplate (FastAPI handlers, Streamlit layout).
- **No** automated agent loops, no Cursor agent runs, no scraped real product data, no paid APIs.

Honest disclosure: the synthetic product entries were drafted with LLM help and then sanity-checked against publicly visible product names from manufacturer websites (Aptamil, Pampers, etc. are real brands; the entries here are illustrative shapes, not scraped data).

## 7. Repo layout

```
mumz-assistant/
├── app/
│   ├── agent.py              # core RAG + safety + LLM orchestrator
│   ├── main.py               # FastAPI app
│   └── streamlit_app.py      # demo UI
├── data/
│   ├── products.json         # 50 synthetic SKUs (EN+AR)
│   └── knowledge_base.json   # 20 parenting topics (EN+AR, sourced)
├── evals/
│   ├── test_set.json         # 30 test cases
│   ├── run_evals.py          # eval harness
│   └── report.md             # generated per run
├── requirements.txt
├── .gitignore
└── README.md
```

## 8. How to run

```bash
# 1. Setup
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. (Optional) free LLM key for grounded generation; demo works without it
export GEMINI_API_KEY=your_key_here

# 3. Smoke test the agent directly
python -m app.agent

# 4. Run the API
uvicorn app.main:app --reload
# POST http://localhost:8000/chat with {"message": "Is Aptamil Stage 1 halal?"}

# 5. Run the demo UI
streamlit run app/streamlit_app.py

# 6. Run the evals
python -m evals.run_evals
```

## 9. Loom walkthrough

## 9. Loom walkthrough

Recorded walkthrough (~3 minutes): https://www.loom.com/share/8a5e6a10dfec434a83e7271320277a0a

Covers: problem framing, architecture, live EN+AR queries, an adversarial medical-urgency query, the eval report, and the one-line LLM swap.

---

**Built April 29, 2026, Lucknow → Bangalore.**
**Faleha Qazi · qfaleha@gmail.com · github.com/Falehaqazi · linkedin.com/in/falehaqazi**

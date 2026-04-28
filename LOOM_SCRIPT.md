# Loom Recording Script — 3 minutes max

**Tone:** confident, fast, no apologizing. You built this in a day. That's the point.

---

## [0:00–0:20] Hook + framing

> "Hi, I'm Faleha. For the Mumzworld Track A take-home, I built **Mumz Assistant** — a bilingual English-Arabic AI concierge that answers product and parenting questions with citations and safety guardrails. It maps directly to the first real problem in your JD: cutting support tickets by 40 percent.
>
> I'll walk through the architecture, show it working in both languages, hit it with an adversarial query, and then show the eval report."

*(On screen: README hero section with the architecture diagram visible.)*

## [0:20–0:50] Architecture in 30 seconds

> "The pipeline is four stages. A query comes in, language detection splits English from Arabic by Unicode block coverage. Then a regex-based safety filter checks for medical urgency or harmful asks before the LLM runs. Retrieval uses paraphrase-multilingual-MiniLM over FAISS — same index serves both languages. Generation is Gemini 2.0 Flash on the free tier, with a strict cite-only system prompt, and a template fallback so the demo works without an API key. Every claim ties back to a product ID or knowledge ID."

*(On screen: scroll through the architecture diagram in the README.)*

## [0:50–1:40] Live demo

*(Switch to the Streamlit UI.)*

> "Here's the demo. First, an English product question."

Type: **"Is Aptamil Stage 1 halal?"**

> "It returns the answer with citations to product P001 and knowledge K017 — the halal certification topic."

Now click the Arabic example: **"هل حليب أبتاميل حلال؟"**

> "Same query in Arabic. Same retrieved chunks. Response is in Arabic. The pipeline didn't translate — the embeddings handled it natively."

Now type: **"My baby has high fever and is not breathing well"**

> "Adversarial. The safety filter caught the medical urgency before retrieval. The response includes a pediatrician escalation footer. This is the cite-or-refuse pattern in action."

## [1:40–2:20] The evals

*(Switch to evals/report.md.)*

> "Thirty test cases across twelve categories — product specifics, age guardrails, allergens, parenting, and adversarial cases. Four metrics, all in zero to one: retrieval at 3, faithfulness as substring presence, language match, and safety correctness. Composite is the unweighted mean.
>
> Substring faithfulness instead of a judge LLM is deliberate. It's deterministic and debuggable. With more time I'd add RAGAS as a second axis."

*(Highlight the aggregate table and the per-category breakdown.)*

## [2:20–2:55] What I'd do next

> "Three things I'd ship at Mumzworld in week one. First, wire this to your real product catalog through the internal API with embedding refresh on catalog updates. Second, swap the regex safety filter for a small fine-tuned classifier — paraphrase coverage is the limit of regex. Third, instrument click-through and conversion lift on each citation. That's the metric that justifies the project economically.
>
> Repo's linked, README has the full tradeoff discussion. Thanks."

*(End on the README's "Roadmap if this became real" section.)*

---

## Recording notes

- **Tool:** Loom free tier, screen + cam-bubble.
- **Browser:** Close all tabs except the README, the Streamlit UI, and `evals/report.md`. No notifications.
- **Pace:** Brisk. Do not over-explain. Trust the viewer to read what's on screen.
- **Length:** Aim for 2:55–3:00. Going under three minutes is the point.
- **Do one rehearsal,** then record. Don't try for perfection — they want to see you ship.

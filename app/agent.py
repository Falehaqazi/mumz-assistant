"""
Mumz Assistant - Multilingual RAG pipeline
Handles product Q&A and parenting questions in English + Arabic
with safety flags (age-appropriateness, allergens, medical escalation).
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Optional Gemini for free LLM (or swap for Ollama / any other)
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


DATA_DIR = Path(__file__).parent.parent / "data"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Medical/emergency triggers that must escalate to human/professional
MEDICAL_ESCALATION_PATTERNS = [
    r"\b(emergency|er\b|hospital|ambulance|911|999|997)\b",
    r"\b(can'?t breathe|not breathing|turning blue|unresponsive)\b",
    r"\b(severe|high) fever",
    r"\bblood\b.*\b(stool|vomit|cough)",
    r"\b(seizure|convulsion|fit)",
    # Arabic equivalents
    r"(طوارئ|مستشفى|إسعاف|لا يتنفس|تشنج|نزيف|حمى شديدة)",
]

REFUSAL_TRIGGERS = [
    # Out-of-scope harmful asks
    r"\b(suicide|self.?harm|abuse|hurt.*baby)\b",
    r"(انتحار|إيذاء.*نفس|إساءة)",
]


@dataclass
class RetrievedContext:
    """Container for a retrieved chunk."""
    text: str
    metadata: Dict[str, Any]
    score: float
    source_type: str  # "product" or "knowledge"


@dataclass
class AgentResponse:
    """Final response with grounding + safety flags."""
    answer: str
    language: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    safety_flags: List[str] = field(default_factory=list)
    refused: bool = False
    retrieved_chunks: List[RetrievedContext] = field(default_factory=list)


def detect_language(text: str) -> str:
    """Lightweight Arabic vs English detector via Unicode block coverage."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    if arabic_chars >= max(3, len(text) * 0.2):
        return "ar"
    return "en"


def check_safety(query: str) -> List[str]:
    """Return list of safety flags fired by the query."""
    flags = []
    q_lower = query.lower()
    for pattern in MEDICAL_ESCALATION_PATTERNS:
        if re.search(pattern, q_lower):
            flags.append("medical_escalation")
            break
    for pattern in REFUSAL_TRIGGERS:
        if re.search(pattern, q_lower):
            flags.append("refuse")
            break
    return flags


class MumzRetriever:
    """FAISS-based multilingual retriever over products + knowledge base."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.products = json.loads((data_dir / "products.json").read_text(encoding="utf-8"))
        self.knowledge = json.loads((data_dir / "knowledge_base.json").read_text(encoding="utf-8"))

        self.documents: List[Dict[str, Any]] = []
        self._build_corpus()
        self._build_index()

    def _build_corpus(self) -> None:
        """Flatten products + knowledge into searchable docs (bilingual concat)."""
        for p in self.products:
            text = (
                f"Product: {p['name']} | {p['name_ar']}\n"
                f"Category: {p['category']} | Age: {p['age_range']}\n"
                f"Brand: {p['brand']} | Price: {p['price_aed']} AED\n"
                f"Ingredients: {p['ingredients']}\n"
                f"Allergens: {p['allergens']}\n"
                f"Safety: {p['safety_notes']}"
            )
            self.documents.append({"text": text, "metadata": p, "source_type": "product"})

        for k in self.knowledge:
            text = (
                f"Topic: {k['topic']}\n"
                f"EN: {k['content_en']}\n"
                f"AR: {k['content_ar']}\n"
                f"Source: {k['source']}"
            )
            self.documents.append({"text": text, "metadata": k, "source_type": "knowledge"})

    def _build_index(self) -> None:
        texts = [d["text"] for d in self.documents]
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings.astype("float32"))

    def retrieve(self, query: str, k: int = 4) -> List[RetrievedContext]:
        q_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        scores, idxs = self.index.search(q_emb.astype("float32"), k)
        out: List[RetrievedContext] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            d = self.documents[idx]
            out.append(RetrievedContext(
                text=d["text"],
                metadata=d["metadata"],
                score=float(score),
                source_type=d["source_type"],
            ))
        return out


class MumzAgent:
    """Top-level orchestrator: safety -> retrieve -> generate -> guardrail."""

    SYS_PROMPT = """You are Mumz Assistant, a helpful shopping and parenting AI for Mumzworld.
You speak fluent English and Arabic, matching the user's input language.

RULES:
1. Answer ONLY using the provided context. If the context doesn't have the answer, say so.
2. Always cite product IDs (P001, etc.) or knowledge IDs (K001, etc.) for every factual claim.
3. For age-sensitive questions, explicitly check the product's age_range.
4. For allergen-related questions, surface allergen warnings prominently.
5. For any medical concern, recommend consulting a pediatrician.
6. Never invent prices, ingredients, or safety claims not in the context.
7. Match the user's language: respond in Arabic if they wrote in Arabic, otherwise English.
"""

    def __init__(self, retriever: Optional[MumzRetriever] = None, llm_provider: str = "gemini"):
        self.retriever = retriever or MumzRetriever()
        self.llm_provider = llm_provider
        self._init_llm()

    def _init_llm(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if self.llm_provider == "gemini" and HAS_GEMINI and api_key:
            genai.configure(api_key=api_key)
            self.llm = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.llm = None  # fallback to template-based answers

    def _build_prompt(self, query: str, contexts: List[RetrievedContext], lang: str) -> str:
        ctx_block = "\n\n---\n\n".join(
            f"[{c.metadata.get('id', '?')}] ({c.source_type})\n{c.text}"
            for c in contexts
        )
        lang_hint = "Respond in Arabic." if lang == "ar" else "Respond in English."
        return f"{self.SYS_PROMPT}\n\nCONTEXT:\n{ctx_block}\n\nUSER QUESTION ({lang}): {query}\n\n{lang_hint}\n\nANSWER:"

    def _template_answer(self, query: str, contexts: List[RetrievedContext], lang: str) -> str:
        """Fallback when no LLM is configured - return top retrieved chunks formatted."""
        if not contexts:
            return ("I couldn't find relevant info. Please consult a pediatrician for medical questions."
                    if lang == "en"
                    else "لم أجد معلومات ذات صلة. يرجى استشارة طبيب الأطفال للأسئلة الطبية.")
        top = contexts[0]
        if top.source_type == "product":
            m = top.metadata
            if lang == "ar":
                return f"وجدت {m['name_ar']} ({m['id']}). الفئة العمرية: {m['age_range']}. السعر: {m['price_aed']} درهم. ملاحظات السلامة: {m['safety_notes']}"
            return f"I found {m['name']} ({m['id']}). Age range: {m['age_range']}. Price: {m['price_aed']} AED. Safety: {m['safety_notes']}"
        m = top.metadata
        return m["content_ar"] if lang == "ar" else m["content_en"]

    def _generate(self, prompt: str) -> str:
        if self.llm is None:
            return ""
        try:
            resp = self.llm.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            return f"[LLM error: {e}]"

    def answer(self, query: str, k: int = 4) -> AgentResponse:
        lang = detect_language(query)
        flags = check_safety(query)

        # Hard refusal
        if "refuse" in flags:
            msg = ("I can't help with that. If you or someone is in danger, please contact local emergency services."
                   if lang == "en"
                   else "لا أستطيع المساعدة في ذلك. إذا كنت أنت أو أي شخص في خطر، يرجى الاتصال بخدمات الطوارئ المحلية.")
            return AgentResponse(answer=msg, language=lang, safety_flags=flags, refused=True)

        contexts = self.retriever.retrieve(query, k=k)

        # Generate
        if self.llm is not None:
            prompt = self._build_prompt(query, contexts, lang)
            answer = self._generate(prompt)
            if not answer or answer.startswith("[LLM error"):
                answer = self._template_answer(query, contexts, lang)
        else:
            answer = self._template_answer(query, contexts, lang)

        # Always append medical escalation reminder if flagged
        if "medical_escalation" in flags:
            esc = ("\n\n⚠️ This sounds urgent. Please contact your pediatrician or emergency services immediately."
                   if lang == "en"
                   else "\n\n⚠️ هذا يبدو عاجلاً. يرجى الاتصال بطبيب الأطفال أو خدمات الطوارئ على الفور.")
            answer += esc

        citations = [
            {"id": c.metadata.get("id"), "type": c.source_type, "score": round(c.score, 3)}
            for c in contexts
        ]

        return AgentResponse(
            answer=answer,
            language=lang,
            citations=citations,
            safety_flags=flags,
            refused=False,
            retrieved_chunks=contexts,
        )


if __name__ == "__main__":
    agent = MumzAgent()
    test_queries = [
        "Is Aptamil Stage 1 halal?",
        "هل حليب أبتاميل المرحلة الأولى حلال؟",
        "What car seat for a newborn?",
        "My baby has a high fever and isn't breathing well",
    ]
    for q in test_queries:
        print(f"\n>>> {q}")
        r = agent.answer(q)
        print(f"[{r.language}] {r.answer[:200]}")
        print(f"flags={r.safety_flags} citations={r.citations[:2]}")

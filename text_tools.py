"""Dependency-free text utilities with basic Persian and English support."""
from __future__ import annotations

import re
from collections import Counter

_STOPWORDS = set("""
the a an and or but if then than to of in on at for from by with is are was were be been being
this that these those it its as i you he she we they them my your our their not do does did
و در به از که را با برای این آن یک است بود شد می من تو او ما شما آنها هم یا اگر تا ولی
""".split())


def clean_text(text: str) -> str:
    """Normalize whitespace and remove spaces before common punctuation."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\s+([،؛.!؟,:;?])", r"\1", text)
    text = re.sub(r"([،؛.!؟,:;?])(?=\S)", r"\1 ", text)
    return text.strip()


def _words(text: str):
    return re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", text.casefold(), flags=re.UNICODE)


def _sentences(text: str):
    parts = re.split(r"(?<=[.!?؟؛])\s+|\n+", clean_text(text))
    return [part.strip() for part in parts if part.strip()]


def analyze_text(text: str) -> dict:
    normalized = clean_text(text)
    words = _words(normalized)
    sentences = _sentences(normalized)
    tokens = [w for w in words if len(w) > 1 and w not in _STOPWORDS and not w.isdigit()]
    common = Counter(tokens).most_common(7)
    return {
        "characters": len(normalized),
        "words": len(words),
        "sentences": len(sentences),
        "reading_minutes": max(1, (len(words) + 179) // 180) if words else 0,
        "keywords": [word for word, _count in common],
    }


def summarize_text(text: str, max_sentences: int = 3) -> str:
    """Extractive summary: selects informative original sentences by word frequency."""
    if max_sentences < 1:
        raise ValueError("max_sentences باید حداقل ۱ باشد.")
    normalized = clean_text(text)
    sentences = _sentences(normalized)
    if not sentences:
        return "متنی برای خلاصه‌سازی وجود ندارد."
    if len(sentences) <= max_sentences:
        return "\n".join(sentences)

    all_words = _words(normalized)
    useful = [w for w in all_words if len(w) > 1 and w not in _STOPWORDS and not w.isdigit()]
    frequencies = Counter(useful)
    scored = []
    for index, sentence in enumerate(sentences):
        words = _words(sentence)
        meaningful = [w for w in words if w in frequencies]
        score = sum(frequencies[w] for w in meaningful) / max(len(words), 1)
        scored.append((score, index, sentence))
    chosen = sorted(scored, key=lambda item: (-item[0], item[1]))[:max_sentences]
    chosen.sort(key=lambda item: item[1])
    return "\n".join(item[2] for item in chosen)

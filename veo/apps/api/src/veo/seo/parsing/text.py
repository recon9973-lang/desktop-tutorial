"""Text comparison used by the near-duplicate and thin-content observations.

Korean does not put spaces where English does, so a word-level comparison of two Korean
pages is unreliable. Character shingles sidestep the question entirely: they measure how
much of one text's local structure appears in the other, in any language, without a
tokeniser.

Nothing here decides points. It reports a similarity ratio and a length; the collector
turns those into a status and the evaluator turns the status into a number.
"""

from __future__ import annotations

#: Length of the character window compared between two texts.
SHINGLE_SIZE = 5


def normalise(text: str) -> str:
    """Collapse whitespace and case so formatting differences are not read as content."""
    return " ".join(text.split()).lower()


def shingles(text: str, size: int = SHINGLE_SIZE) -> frozenset[str]:
    normalised = normalise(text)
    if len(normalised) < size:
        return frozenset({normalised}) if normalised else frozenset()
    return frozenset(normalised[i : i + size] for i in range(len(normalised) - size + 1))


def shingle_similarity(left: str, right: str, size: int = SHINGLE_SIZE) -> float:
    """Jaccard similarity of the two texts' character shingles, in ``[0, 1]``."""
    a, b = shingles(left, size), shingles(right, size)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def content_length(text: str) -> int:
    """Number of non-whitespace characters — the closest honest proxy for substance."""
    return len("".join(normalise(text).split()))


__all__ = [
    "SHINGLE_SIZE",
    "content_length",
    "normalise",
    "shingle_similarity",
    "shingles",
]

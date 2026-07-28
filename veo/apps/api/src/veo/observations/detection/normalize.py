"""Korean-aware surface matching for brand names.

The failure this module exists to prevent is silent. ``re.search(r"\\b베놈치과\\b", answer)``
finds nothing in ``베놈치과는 강남구에 있습니다``, because ``는`` is a word character and the
trailing boundary never fires. Nothing raises. The check simply reports that the brand was
never mentioned, and the customer's exposure rate quietly becomes zero. The GEO worker hit
exactly this and it emptied a whole check before anyone noticed.

So matching here is built around three Korean facts:

* **Particles attach directly to the noun.** ``베놈치과가`` / ``베놈치과의`` / ``베놈치과에서는``
  are all the same name. A tail that is a recognised particle or copula is a clean boundary.
* **Spacing is not stable.** ``베놈치과`` and ``베놈 치과`` are written interchangeably, and the
  suffix (``치과`` / ``의원`` / ``병원``) is where the space lands. One pattern covers both.
* **An unrecognised tail is ambiguity, not absence.** ``베놈치과의원`` is probably a different
  business and ``강남베놈치과`` is probably a branch — neither is a fact this module is
  entitled to decide. Those come back as :attr:`BoundaryStrength.WEAK` so the caller can
  route them to a human instead of counting or discarding them.

Folding is offset-preserving on purpose. Every verdict quotes the fragment it came from,
and a fold that changed the string's length would point a reviewer at the wrong characters.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

__all__ = [
    "BUSINESS_SUFFIXES",
    "BoundaryStrength",
    "SurfaceMatch",
    "find_surface_matches",
    "fold",
    "is_particle_run",
    "normalize_brand",
    "split_business_suffix",
    "surface_variants",
]

#: Business-type suffixes, longest first so ``성형외과`` never splits as ``외과``.
BUSINESS_SUFFIXES: tuple[str, ...] = (
    "소아청소년과",
    "마취통증의학과",
    "이비인후과",
    "비뇨의학과",
    "재활의학과",
    "영상의학과",
    "가정의학과",
    "성형외과",
    "치과병원",
    "한방병원",
    "요양병원",
    "종합병원",
    "정형외과",
    "신경외과",
    "산부인과",
    "정신과",
    "한의원",
    "의료원",
    "피부과",
    "소아과",
    "치과",
    "안과",
    "내과",
    "외과",
    "병원",
    "의원",
    "클리닉",
    "약국",
    "센터",
    "의료재단",
)

#: Particles and copula endings that may sit directly against a name.
#:
#: Deliberately a closed list. A permissive rule ("any Hangul tail is fine") would match
#: ``베놈치과의원`` as ``베놈치과``, which is a different business — and an over-count is the one
#: error nobody downstream can detect.
_PARTICLES: frozenset[str] = frozenset(
    {
        "은", "는", "이", "가", "을", "를", "의", "도", "만", "과", "와", "랑", "이랑",
        "나", "이나", "든", "이든", "든지", "이든지",
        "에", "에서", "에게", "에게서", "께", "께서", "한테", "한테서",
        "로", "으로", "로서", "으로서", "로써", "으로써",
        "부터", "까지", "조차", "마저", "밖에", "처럼", "같이", "보다", "마다",
        "라", "이라", "라고", "이라고", "라는", "이라는", "란", "이란", "라도", "이라도",
        "라서", "이라서", "며", "이며", "고", "이고", "다", "이다", "인", "인데", "임",
        "입니다", "입니다만", "이지만", "지만", "예요", "이에요", "이었다", "였다",
        "이니", "이니까", "니까", "죠", "이죠", "야", "이야", "요",
    }
)

_HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_HANGUL_RUN_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]+")
_WHITESPACE_RE = re.compile(r"\s+")


class BoundaryStrength(StrEnum):
    """How cleanly a surface hit sits in the surrounding Korean text.

    ``STRONG`` — the name stands alone or wears a recognised particle.
    ``WEAK`` — Hangul is glued to it that we do not recognise. Possibly this brand,
    possibly a longer name that contains it. The detector refuses to decide.
    """

    STRONG = "STRONG"
    WEAK = "WEAK"


@dataclass(frozen=True, slots=True)
class SurfaceMatch:
    """One place in the text where a declared name appeared."""

    start: int
    end: int
    quote: str
    """The fragment exactly as the text spells it — the reviewer's evidence."""
    surface_form: str
    """The declared name or alias that produced the hit."""
    trailing_particle: str
    strength: BoundaryStrength


def fold(text: str) -> str:
    """Case- and width-fold ``text`` without moving a single offset.

    Per character, and only when the result is still one character: a fold that changed
    the length would invalidate every span this module hands to a human reviewer.
    """
    out: list[str] = []
    for char in text:
        folded = unicodedata.normalize("NFKC", char)
        if len(folded) != 1:
            folded = char
        lowered = folded.lower()
        if len(lowered) != 1:
            lowered = folded
        out.append(lowered)
    return "".join(out)


def normalize_brand(name: str) -> str:
    """The stable key for a brand name: folded, with every space removed.

    ``베놈 치과``, ``베놈치과`` and ``VENOM 치과`` are the same business written three ways.
    This is what ``entity_mentions.entity_key`` should be derived from when the caller has
    no explicit key.
    """
    return "".join(fold(name).split())


def split_business_suffix(name: str) -> tuple[str, str]:
    """Split ``베놈치과`` into ``("베놈", "치과")``.

    Returns ``(name, "")`` when there is no suffix, or when stripping it would leave
    nothing — ``치과`` on its own is a category, not a stem.
    """
    stripped = name.strip()
    for suffix in BUSINESS_SUFFIXES:
        if stripped.endswith(suffix):
            stem = stripped[: -len(suffix)].strip()
            if stem:
                return stem, suffix
            return stripped, ""
    return stripped, ""


def surface_variants(name: str) -> tuple[str, ...]:
    """The spellings a Korean writer actually produces for one declared name."""
    stripped = _WHITESPACE_RE.sub(" ", name.strip())
    if not stripped:
        return ()
    variants = [stripped, stripped.replace(" ", "")]
    stem, suffix = split_business_suffix(stripped.replace(" ", ""))
    if suffix:
        variants.append(f"{stem} {suffix}")
    seen: list[str] = []
    for variant in variants:
        if variant and variant not in seen:
            seen.append(variant)
    return tuple(seen)


def is_particle_run(run: str) -> bool:
    """Whether a Hangul tail is nothing but particles.

    One concatenation is allowed, which is how ``에서는`` (에서 + 는) and ``부터가`` are
    recognised without opening the door to arbitrary Hangul.
    """
    if not run:
        return False
    if run in _PARTICLES:
        return True
    return any(
        run[:index] in _PARTICLES and run[index:] in _PARTICLES for index in range(1, len(run))
    )


def find_surface_matches(text: str, names: Sequence[str]) -> tuple[SurfaceMatch, ...]:
    """Every place one of ``names`` appears in ``text``, with its boundary quality.

    Offsets index into ``text`` exactly as given. Matches never overlap, and the longest
    declared name wins where two could match at the same position.
    """
    built = _build_pattern(tuple(names))
    if built is None:
        return ()
    pattern, group_names = built

    folded = fold(text)
    found: list[SurfaceMatch] = []
    for match in pattern.finditer(folded):
        start, end = match.span()
        left = _left_boundary(folded, start)
        if left is None:
            continue
        right, particle = _right_boundary(folded, end)
        if right is None:
            continue
        strength = (
            BoundaryStrength.STRONG
            if left is BoundaryStrength.STRONG and right is BoundaryStrength.STRONG
            else BoundaryStrength.WEAK
        )
        group = match.lastgroup or ""
        found.append(
            SurfaceMatch(
                start=start,
                end=end,
                quote=text[start:end],
                surface_form=group_names.get(group, text[start:end]),
                trailing_particle=particle,
                strength=strength,
            )
        )
    return tuple(found)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=512)
def _build_pattern(names: tuple[str, ...]) -> tuple[re.Pattern[str], dict[str, str]] | None:
    """Compile one alternation for ``names``, plus the group -> declared-name mapping.

    The mapping travels with the pattern rather than living in a module global: two
    different brand sets would otherwise reuse the same group names and mislabel each
    other's hits.
    """
    ordered: list[str] = []
    for name in names:
        for variant in surface_variants(name):
            if variant not in ordered:
                ordered.append(variant)
    if not ordered:
        return None

    # Longest first: with a shared alternation, Python's engine takes the first branch
    # that matches, so ordering is what stops the alias 베놈 from swallowing 베놈치과.
    ordered.sort(key=lambda item: (-len(item.replace(" ", "")), item))

    branches: list[str] = []
    group_names: dict[str, str] = {}
    seen_sources: set[str] = set()
    for variant in ordered:
        source = _variant_pattern(variant)
        if not source or source in seen_sources:
            continue
        seen_sources.add(source)
        group = f"v{len(group_names)}"
        group_names[group] = variant
        branches.append(f"(?P<{group}>{source})")
    if not branches:
        return None
    return re.compile("|".join(branches)), group_names


def _variant_pattern(variant: str) -> str:
    stem, suffix = split_business_suffix(variant)
    parts = [stem, suffix] if suffix else [variant]
    return r"\s*".join(_tokens_pattern(fold(part)) for part in parts if part)


def _tokens_pattern(part: str) -> str:
    return r"\s*".join(re.escape(token) for token in part.split())


def _left_boundary(text: str, position: int) -> BoundaryStrength | None:
    if position == 0:
        return BoundaryStrength.STRONG
    previous = text[position - 1]
    if _HANGUL_RE.match(previous):
        # 강남베놈치과 — a branch, a longer name, or a coincidence. Not ours to decide.
        return BoundaryStrength.WEAK
    if previous.isdigit():
        return BoundaryStrength.WEAK
    if previous.isalpha():
        # Latin glued on the left means a different word entirely (myvenom / venom).
        return None
    return BoundaryStrength.STRONG


def _right_boundary(text: str, position: int) -> tuple[BoundaryStrength | None, str]:
    if position >= len(text):
        return BoundaryStrength.STRONG, ""
    next_char = text[position]
    if _HANGUL_RE.match(next_char):
        run_match = _HANGUL_RUN_RE.match(text, position)
        run = run_match.group(0) if run_match else ""
        if is_particle_run(run):
            return BoundaryStrength.STRONG, run
        return BoundaryStrength.WEAK, ""
    if next_char.isdigit():
        return BoundaryStrength.WEAK, ""
    if next_char.isalpha():
        return None, ""
    return BoundaryStrength.STRONG, ""

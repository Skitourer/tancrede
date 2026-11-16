"""Deterministic classification filter (SPEC §5, R1).

No prompt, source or model can change a decision: the filter only reads the
configured labels and the extracted text and metadata.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from tancrede.adapters.extraction import ExtractedDocument
from tancrede.config.settings import LabelRule


class Reason(StrEnum):
    EXCLUDED_LABEL = "excluded_label"
    NON_EXTRACTABLE = "non_extractable"
    INCLUDED_LABEL = "included_label"
    NO_LABEL = "no_label"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: Reason
    label: str | None = None


def _compile(pattern: str) -> re.Pattern[str]:
    """Whole-token, case-insensitive match; spaces match any whitespace."""
    words = unicodedata.normalize("NFC", pattern).split()
    body = r"\s+".join(re.escape(w) for w in words)
    return re.compile(rf"(?<![\w-]){body}(?![\w-])", re.IGNORECASE)


class _CompiledRule:
    def __init__(self, rule: LabelRule) -> None:
        self.name = rule.name
        self.regexes = [_compile(p) for p in (rule.patterns or [rule.name]) if p.strip()]

    def matches(self, haystacks: Sequence[str]) -> bool:
        return any(rx.search(h) for rx in self.regexes for h in haystacks)


class ClassificationFilter:
    def __init__(self, excluded: Sequence[LabelRule], included: Sequence[LabelRule] = ()) -> None:
        self._excluded = [_CompiledRule(r) for r in excluded]
        self._included = [_CompiledRule(r) for r in included]

    @property
    def has_exclusions(self) -> bool:
        return bool(self._excluded)

    def classify(self, document: ExtractedDocument | None) -> Decision:
        if document is None:
            return Decision(False, Reason.NON_EXTRACTABLE)
        haystacks = [document.text, *document.metadata.keys(), *document.metadata.values()]
        for rule in self._excluded:  # exclusion always wins
            if rule.matches(haystacks):
                return Decision(False, Reason.EXCLUDED_LABEL, rule.name)
        for rule in self._included:
            if rule.matches(haystacks):
                return Decision(True, Reason.INCLUDED_LABEL, rule.name)
        return Decision(True, Reason.NO_LABEL)

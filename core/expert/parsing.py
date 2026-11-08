"""Parsing of user-entered rules and facts (PS §6.1, D2)."""

from __future__ import annotations

import itertools
import re

from core.errors import ValidationError
from core.text import normalize

_SEPARATOR = re.compile(r"\bALORS\b|=>|->|⇒", re.IGNORECASE)
_SI_PREFIX = re.compile(r"^\s*SI\b\s*", re.IGNORECASE)
_ET = re.compile(r"\s+ET\s+|\^|&|,", re.IGNORECASE)
_OU = re.compile(r"\s+OU\s+", re.IGNORECASE)
_CONCLUSION_SEPARATOR = re.compile(r"\s+ET\s+|\s+OU\s+|,", re.IGNORECASE)


def parse_rule_text(text: str) -> list[tuple[tuple[str, ...], str]]:
    """Parse one rule, expanding ``OU`` alternatives into several rules.

    Accepted forms: ``SI a ET b ALORS c``, ``a, b -> c``, ``a ^ b => c``.
    Raises ``ValidationError`` on malformed input.
    """
    if not isinstance(text, str):
        raise ValidationError("La règle doit être une chaîne de caractères.")
    separators = list(_SEPARATOR.finditer(text))
    if len(separators) != 1:
        raise ValidationError(
            "Une règle doit contenir exactement un séparateur (ALORS, ->, => ou ⇒)."
        )
    match = separators[0]
    premise_part = text[: match.start()]
    conclusion_part = text[match.end() :]

    premise_part = _SI_PREFIX.sub("", premise_part, count=1)

    groups: list[list[str]] = []
    for raw_group in _ET.split(premise_part):
        alternatives: list[str] = []
        for raw_alternative in _OU.split(raw_group):
            alternative = normalize(raw_alternative)
            if not alternative:
                raise ValidationError("Une prémisse ne peut pas être vide.")
            alternatives.append(alternative)
        groups.append(alternatives)

    if not groups:
        raise ValidationError("Une règle doit avoir au moins une prémisse.")

    conclusion = normalize(conclusion_part)
    if not conclusion:
        raise ValidationError("La conclusion d'une règle ne peut pas être vide.")
    if _CONCLUSION_SEPARATOR.search(conclusion):
        raise ValidationError(
            "La conclusion doit être un seul fait (ET, OU et les virgules sont interdits)."
        )

    combination_count = 1
    for alternatives in groups:
        combination_count *= len(alternatives)
    if combination_count > 16:
        raise ValidationError(
            "Le développement des OU produit plus de 16 règles ; simplifiez la règle."
        )

    results: list[tuple[tuple[str, ...], str]] = []
    for combination in itertools.product(*groups):
        premises: list[str] = []
        for premise in combination:
            if premise not in premises:
                premises.append(premise)
        results.append((tuple(premises), conclusion))
    return results


def parse_facts_text(text: str) -> list[str]:
    """Parse a fact list separated by newlines, semicolons or commas."""
    if not isinstance(text, str):
        raise ValidationError("La liste de faits doit être une chaîne de caractères.")
    facts: list[str] = []
    for chunk in re.split(r"[\n;,]", text):
        fact = normalize(chunk)
        if fact and fact not in facts:
            facts.append(fact)
    return facts

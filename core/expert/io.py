"""JSON persistence for knowledge bases (schema PS §7.3)."""

from __future__ import annotations

import json
from typing import Any

from core.errors import ValidationError
from core.expert.models import KnowledgeBase

KB_FORMAT = "ensi-ai-kb"
KB_VERSION = 1


def kb_to_dict(kb: KnowledgeBase) -> dict[str, Any]:
    """Serialize ``kb`` to the ordered schema of PS §7.3."""
    return {
        "format": KB_FORMAT,
        "version": KB_VERSION,
        "name": kb.name,
        "facts": list(kb.facts),
        "rules": [
            {"id": rule.id, "if": list(rule.premises), "then": rule.conclusion}
            for rule in kb.rules
        ],
    }


def kb_to_json(kb: KnowledgeBase) -> str:
    """Return indented JSON with raw non-ASCII characters."""
    return json.dumps(kb_to_dict(kb), ensure_ascii=False, indent=2)


def kb_from_dict(data: object) -> KnowledgeBase:
    """Build a fresh validated knowledge base, aggregating every problem."""
    if not isinstance(data, dict):
        raise ValidationError("Le document JSON doit être un objet.")

    messages: list[str] = []
    if data.get("format") != KB_FORMAT:
        messages.append(f"Format invalide : « {KB_FORMAT} » attendu.")

    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        messages.append(f"Version invalide : {KB_VERSION} attendu.")
    elif version != KB_VERSION:
        messages.append(f"Version invalide : {KB_VERSION} attendu.")

    name = data.get("name")
    if not isinstance(name, str):
        messages.append("Le nom de la base doit être une chaîne de caractères.")
        name = "Base sans titre"

    kb = KnowledgeBase(name=name)

    facts = data.get("facts")
    if not isinstance(facts, list):
        messages.append("La clé « facts » doit être une liste.")
    else:
        for index, fact in enumerate(facts, start=1):
            if not isinstance(fact, str):
                messages.append(
                    f"Le fait n°{index} doit être une chaîne de caractères."
                )
                continue
            try:
                kb.add_fact(fact)
            except ValidationError as exc:
                messages.extend(exc.messages)

    rules = data.get("rules")
    if not isinstance(rules, list):
        messages.append("La clé « rules » doit être une liste.")
    else:
        seen_ids: set[str] = set()
        for index, raw in enumerate(rules, start=1):
            if not isinstance(raw, dict):
                messages.append(f"La règle n°{index} doit être un objet JSON.")
                continue

            rule_id = raw.get("id")
            premises = raw.get("if")
            conclusion = raw.get("then")
            valid = True

            if not isinstance(rule_id, str) or not rule_id:
                messages.append(
                    f"Règle n°{index} : identifiant manquant ou invalide."
                )
                valid = False

            if not isinstance(premises, list):
                messages.append(
                    f"Règle n°{index} : la clé « if » doit être une liste."
                )
                valid = False
            else:
                for position, premise in enumerate(premises, start=1):
                    if not isinstance(premise, str):
                        messages.append(
                            f"Règle n°{index} : la prémisse n°{position} "
                            "doit être une chaîne de caractères."
                        )
                        valid = False

            if not isinstance(conclusion, str):
                messages.append(
                    f"Règle n°{index} : la clé « then » doit être une chaîne "
                    "de caractères."
                )
                valid = False

            duplicate = False
            if isinstance(rule_id, str) and rule_id:
                if rule_id in seen_ids:
                    messages.append(f"Identifiant de règle en double : {rule_id}.")
                    duplicate = True
                seen_ids.add(rule_id)

            if not valid:
                continue

            scratch = KnowledgeBase()
            try:
                scratch.add_rule(list(premises), conclusion)
            except ValidationError as exc:
                messages.extend(exc.messages)
                continue

            if duplicate:
                continue
            try:
                kb.add_rule(list(premises), conclusion, rule_id=rule_id)
            except ValidationError as exc:
                messages.extend(exc.messages)

    if messages:
        raise ValidationError(messages)
    return kb


def kb_from_json(text: str) -> KnowledgeBase:
    """Parse JSON text and validate it as a knowledge base."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Fichier JSON invalide : {exc.msg}.") from exc
    return kb_from_dict(data)

"""Expert-system data models: rules, knowledge bases, traces and results."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from core.errors import ValidationError
from core.text import normalize


@dataclass(frozen=True)
class Rule:
    """A rule ``SI premises ET … ALORS conclusion``."""

    id: str
    premises: tuple[str, ...]
    conclusion: str

    def to_text(self, with_id: bool = True) -> str:
        """Render the rule in the course notation."""
        body = "SI " + " ET ".join(self.premises) + " ALORS " + self.conclusion
        return f"{self.id} : {body}" if with_id else body


@dataclass
class KnowledgeBase:
    """Facts and rules of a knowledge base."""

    name: str = "Base sans titre"
    facts: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_fact(self, f: str) -> bool:
        """Return True when the normalized fact is present."""
        return normalize(f) in self.facts

    def universe(self) -> list[str]:
        """Facts then rule premises and conclusions, first-appearance order."""
        seen: dict[str, None] = {}
        for fact in self.facts:
            seen.setdefault(fact, None)
        for rule in self.rules:
            for premise in rule.premises:
                seen.setdefault(premise, None)
            seen.setdefault(rule.conclusion, None)
        return list(seen)

    def derivable_conclusions(self) -> list[str]:
        """Rule conclusions, unique, in rule order."""
        seen: dict[str, None] = {}
        for rule in self.rules:
            seen.setdefault(rule.conclusion, None)
        return list(seen)

    def rules_for(self, goal: str) -> list[Rule]:
        """Rules whose conclusion equals ``goal``, in list order."""
        target = normalize(goal)
        return [rule for rule in self.rules if rule.conclusion == target]

    def next_rule_id(self) -> str:
        """Return ``R<max numeric suffix + 1>`` (never renumbers ids)."""
        highest = 0
        for rule in self.rules:
            match = re.fullmatch(r"R(\d+)", rule.id)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"R{highest + 1}"

    def copy(self) -> "KnowledgeBase":
        """Return an independent deep copy."""
        return copy.deepcopy(self)

    # ------------------------------------------------------------------
    # Mutation (all validate, raise ValidationError)
    # ------------------------------------------------------------------
    def add_fact(self, f: str) -> bool:
        """Add a fact; return False when it is already present."""
        fact = normalize(f)
        if not fact:
            raise ValidationError("Un fait ne peut pas être vide.")
        if fact in self.facts:
            return False
        self.facts.append(fact)
        return True

    def remove_fact(self, f: str) -> None:
        """Remove an existing fact."""
        fact = normalize(f)
        if fact not in self.facts:
            raise ValidationError(f"Le fait « {fact} » n'est pas dans la base de faits.")
        self.facts.remove(fact)

    def rename_fact(self, old: str, new: str) -> None:
        """Rename a fact in the fact list only (rules are untouched)."""
        old_fact = normalize(old)
        new_fact = normalize(new)
        if not new_fact:
            raise ValidationError("Un fait ne peut pas être vide.")
        if old_fact not in self.facts:
            raise ValidationError(f"Le fait « {old_fact} » n'est pas dans la base de faits.")
        if new_fact in self.facts:
            raise ValidationError(f"Le fait « {new_fact} » existe déjà dans la base de faits.")
        self.facts[self.facts.index(old_fact)] = new_fact

    def add_rule(
        self,
        premises: list[str],
        conclusion: str,
        rule_id: str | None = None,
    ) -> Rule:
        """Validate and append a rule; return the created ``Rule``."""
        normalized_premises, normalized_conclusion = self._validate_rule_content(
            premises, conclusion
        )
        if rule_id is None:
            rule_id = self.next_rule_id()
        else:
            rule_id = normalize(rule_id)
            if not rule_id:
                raise ValidationError("L'identifiant d'une règle ne peut pas être vide.")
            if any(rule.id == rule_id for rule in self.rules):
                raise ValidationError(f"L'identifiant de règle « {rule_id} » existe déjà.")
        rule = Rule(rule_id, normalized_premises, normalized_conclusion)
        self.rules.append(rule)
        return rule

    def update_rule(
        self, rule_id: str, premises: list[str], conclusion: str
    ) -> Rule:
        """Replace a rule's content while keeping its id and position."""
        index = self._rule_index(rule_id)
        normalized_premises, normalized_conclusion = self._validate_rule_content(
            premises, conclusion, ignore_rule_id=rule_id
        )
        rule = Rule(self.rules[index].id, normalized_premises, normalized_conclusion)
        self.rules[index] = rule
        return rule

    def remove_rule(self, rule_id: str) -> None:
        """Remove an existing rule."""
        index = self._rule_index(rule_id)
        del self.rules[index]

    def signature(self) -> str:
        """Deterministic SHA-256 of the whole content (PS §7.1)."""
        payload = {
            "name": self.name,
            "facts": self.facts,
            "rules": [
                {"id": rule.id, "if": list(rule.premises), "then": rule.conclusion}
                for rule in self.rules
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rule_index(self, rule_id: str) -> int:
        for index, rule in enumerate(self.rules):
            if rule.id == rule_id:
                return index
        raise ValidationError(f"La règle « {rule_id} » n'existe pas.")

    def _validate_rule_content(
        self,
        premises: list[str],
        conclusion: str,
        ignore_rule_id: str | None = None,
    ) -> tuple[tuple[str, ...], str]:
        if not isinstance(premises, (list, tuple)):
            raise ValidationError("Les prémisses d'une règle doivent être une liste.")
        if not premises:
            raise ValidationError("Une règle doit avoir au moins une prémisse.")
        normalized: list[str] = []
        for premise in premises:
            if not isinstance(premise, str):
                raise ValidationError("Chaque prémisse doit être une chaîne de caractères.")
            value = normalize(premise)
            if not value:
                raise ValidationError("Une prémisse ne peut pas être vide.")
            if value in normalized:
                raise ValidationError(f"La prémisse « {value} » est répétée dans la règle.")
            normalized.append(value)
        if not isinstance(conclusion, str):
            raise ValidationError("La conclusion doit être une chaîne de caractères.")
        normalized_conclusion = normalize(conclusion)
        if not normalized_conclusion:
            raise ValidationError("La conclusion d'une règle ne peut pas être vide.")
        if normalized_conclusion in normalized:
            raise ValidationError(
                "La conclusion d'une règle ne peut pas figurer parmi ses prémisses."
            )
        premise_set = set(normalized)
        for rule in self.rules:
            if rule.id == ignore_rule_id:
                continue
            if rule.conclusion == normalized_conclusion and set(rule.premises) == premise_set:
                raise ValidationError(
                    f"La règle « {rule.id} » a déjà les mêmes prémisses et la même conclusion."
                )
        return tuple(normalized), normalized_conclusion


StopReasonFC = Literal["goal_already_known", "goal_reached", "saturated"]


@dataclass(frozen=True)
class ForwardStep:
    """One forward-chaining inference"""

    index: int
    detected: tuple[str, ...]
    chosen: str
    chosen_text: str
    premises_satisfied: tuple[str, ...]
    derived: str
    is_new: bool
    facts_after: tuple[str, ...]
    goal_reached: bool
    message: str


@dataclass
class ForwardResult:
    """Complete result of a forward-chaining run."""

    goal: Optional[str]
    initial_facts: tuple[str, ...]
    already_in_facts: bool
    success: Optional[bool]
    stop_reason: StopReasonFC
    steps: list[ForwardStep]
    final_facts: tuple[str, ...]
    derived_facts: tuple[str, ...]
    fired_rules: tuple[str, ...]
    unfired_rules: tuple[str, ...]
    derivation: dict[str, tuple[str, tuple[str, ...]]]


BackwardKind = Literal[
    "goal",
    "fact_found",
    "try_rule",
    "subgoal",
    "rule_success",
    "rule_failure",
    "no_rule",
    "cycle",
    "goal_proved",
    "goal_failed",
]


@dataclass(frozen=True)
class BackwardStep:
    """One backward-chaining event."""

    index: int
    depth: int
    kind: BackwardKind
    goal: str
    rule_id: Optional[str]
    goal_stack: tuple[str, ...]
    facts_snapshot: tuple[str, ...]
    message: str


@dataclass
class RuleAttempt:
    """One rule tried while proving a goal."""

    rule_id: str
    subproofs: list["ProofNode"]
    success: bool


@dataclass
class ProofNode:
    """Proof tree node of a backward-chaining run."""

    goal: str
    status: Literal["fact", "proved", "failed", "cycle", "no_rule"]
    rule_id: Optional[str]
    attempts: list[RuleAttempt]


@dataclass
class BackwardResult:
    """Complete result of a backward-chaining run."""

    goal: str
    initial_facts: tuple[str, ...]
    already_in_facts: bool
    success: bool
    stop_reason: Literal["goal_already_known", "proved", "failed"]
    steps: list[BackwardStep]
    proof: ProofNode
    final_facts: tuple[str, ...]
    rules_used: tuple[str, ...]

#!/usr/bin/env python3
"""GO Core v0.2 type, dimension, frame, unit-context, and ledger linter."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

import yaml


DIMENSION_BASIS = ("L", "M", "T", "I", "Theta", "N", "J")
ZERO_DIMENSION = (Fraction(0),) * len(DIMENSION_BASIS)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return data


def fraction(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("boolean is not a dimension exponent")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return Fraction(str(value))
    if isinstance(value, str):
        return Fraction(value)
    raise ValueError(f"unsupported exponent {value!r}")


def parse_dimension(value: Any) -> tuple[Fraction, ...]:
    if isinstance(value, list):
        if len(value) != len(DIMENSION_BASIS):
            raise ValueError("dimension vector must have seven components")
        return tuple(fraction(item) for item in value)
    if isinstance(value, dict):
        unknown = set(value) - set(DIMENSION_BASIS)
        if unknown:
            raise ValueError(f"unknown dimension keys: {sorted(unknown)}")
        return tuple(fraction(value.get(key, 0)) for key in DIMENSION_BASIS)
    raise ValueError("dimension must be a seven-component list or basis mapping")


def dimension_to_json(dimension: tuple[Fraction, ...]) -> list[int | str]:
    result: list[int | str] = []
    for value in dimension:
        result.append(value.numerator if value.denominator == 1 else str(value))
    return result


def dimension_to_text(dimension: tuple[Fraction, ...]) -> str:
    terms: list[str] = []
    for key, exponent in zip(DIMENSION_BASIS, dimension, strict=True):
        if exponent == 0:
            continue
        rendered = str(exponent.numerator) if exponent.denominator == 1 else str(exponent)
        terms.append(f"{key}^{rendered}")
    return "1" if not terms else " ".join(terms)


@dataclass(frozen=True)
class TypeInfo:
    dimension: tuple[Fraction, ...]
    semantic_kind: str
    addition_family: str
    shape: str
    unit_context: str
    frame: str
    normalized: bool = False
    log_base: str | int | float | None = None


@dataclass
class Finding:
    document: str
    rule: str
    severity: str
    message: str
    expression: str | None = None
    anchor: str | None = None
    detected_by: str = "automatic"


class CoreRegistry:
    def __init__(self, root: Path):
        self.root = root
        self.spec = load_yaml(root / "go_core_spec_v0_2.yaml")
        imports = self.spec.get("imports", {})
        self.symbols_data = load_yaml(root / str(imports["symbols"]))
        self.quantities_data = load_yaml(root / str(imports["quantities"]))
        self.contexts_data = load_yaml(root / str(imports["unit_contexts"]))
        self.normalizations_data = load_yaml(root / str(imports["normalizations"]))
        self.defects_data = load_yaml(root / str(imports["defects"]))
        self.protocol_data = load_yaml(root / str(imports["protocol_schema"]))

        self.semantic_kinds = self.spec.get("semantic_kinds", {})
        self.rule_catalog = self.spec.get("rule_catalog", {})
        self.claim_statuses = set(self.spec.get("claim_statuses", []))
        self.strong_claim_statuses = set(self.spec.get("strong_claim_statuses", []))
        self.operator_kinds = self.spec.get("operator_kinds", {})
        self.neutral_contexts = set(self.spec.get("neutral_contexts", []))
        self.frame_neutral_values = set(self.spec.get("frame_neutral_values", []))
        self.contexts = set(self.contexts_data.get("contexts", {}))
        self.protocol_required = set(self.protocol_data.get("required_fields", []))
        self.quantities: dict[str, dict[str, Any]] = {}
        for record in self.quantities_data.get("quantities", []):
            qid = record.get("id")
            if isinstance(qid, str):
                self.quantities[qid] = record

    def severity(self, rule: str, fallback: str = "error") -> str:
        record = self.rule_catalog.get(rule, {})
        return str(record.get("severity", fallback))

    def addition_family(self, semantic_kind: str) -> str:
        record = self.semantic_kinds.get(semantic_kind, {})
        return str(record.get("addition_family", semantic_kind))

    def shape(self, semantic_kind: str) -> str:
        record = self.semantic_kinds.get(semantic_kind, {})
        return str(record.get("shape", "unknown"))

    def type_from_record(self, record: dict[str, Any]) -> TypeInfo:
        semantic_kind = str(record.get("semantic_kind", "scalar"))
        return TypeInfo(
            dimension=parse_dimension(record["dimension"]),
            semantic_kind=semantic_kind,
            addition_family=self.addition_family(semantic_kind),
            shape=self.shape(semantic_kind),
            unit_context=str(record.get("unit_context", "SI")),
            frame=str(record.get("frame", "none")),
            normalized=bool(record.get("normalized", False)),
            log_base=record.get("log_base"),
        )

    def merged_quantity_records(self, document: dict[str, Any]) -> dict[str, dict[str, Any]]:
        records = {key: copy.deepcopy(value) for key, value in self.quantities.items()}
        for local in document.get("quantities", []):
            if not isinstance(local, dict) or not isinstance(local.get("id"), str):
                continue
            merged: dict[str, Any] = {}
            extends = local.get("extends")
            if isinstance(extends, str) and extends in records:
                merged.update(copy.deepcopy(records[extends]))
            merged.update(copy.deepcopy(local))
            records[str(local["id"])] = merged
        return records

    def validate(self) -> list[Finding]:
        findings: list[Finding] = []

        def add(rule: str, message: str) -> None:
            findings.append(
                Finding(
                    document="__core__",
                    rule=rule,
                    severity=self.severity(rule),
                    message=message,
                )
            )

        basis = self.spec.get("schema", {}).get("canonical_dimension_basis")
        if basis != list(DIMENSION_BASIS):
            add("CORE-SCHEMA", "core dimension basis is not canonical")

        symbol_pairs: set[tuple[str, str]] = set()
        symbol_ids: set[str] = set()
        for symbol in self.symbols_data.get("symbols", []):
            sid = symbol.get("id")
            pair = (str(symbol.get("scope")), str(symbol.get("key")))
            if not sid:
                add("CORE-SCHEMA", "symbol missing id")
            elif sid in symbol_ids:
                add("SYMBOL-COLLISION", f"duplicate symbol id {sid}")
            symbol_ids.add(str(sid))
            if pair in symbol_pairs:
                add("SYMBOL-COLLISION", f"duplicate canonical symbol {pair}")
            symbol_pairs.add(pair)

        quantity_ids: set[str] = set()
        for quantity in self.quantities_data.get("quantities", []):
            qid = quantity.get("id")
            if not qid:
                add("CORE-SCHEMA", "quantity missing id")
                continue
            if qid in quantity_ids:
                add("CORE-SCHEMA", f"duplicate quantity id {qid}")
            quantity_ids.add(str(qid))
            try:
                self.type_from_record(quantity)
            except (KeyError, ValueError) as error:
                add("DIMENSION-VECTOR", f"{qid}: {error}")
            if quantity.get("semantic_kind") not in self.semantic_kinds:
                add("CORE-SCHEMA", f"{qid}: unknown semantic kind")
            if quantity.get("unit_context") not in self.contexts:
                add("CORE-SCHEMA", f"{qid}: unknown unit context")
            if quantity.get("claim_status") not in self.claim_statuses:
                add("CLAIM-STATUS", f"{qid}: invalid claim status")
            if (
                quantity.get("semantic_kind") == "information"
                and quantity.get("log_base") is None
            ):
                add("LOG-BASE", f"{qid}: information quantity lacks log base")

        if set(self.rule_catalog) != {
            item.get("id")
            for item in self.spec.get("p0_gates", []) + self.spec.get("p1_gates", [])
        }:
            gate_ids = {
                item.get("id")
                for item in self.spec.get("p0_gates", []) + self.spec.get("p1_gates", [])
            }
            missing_rules = gate_ids - set(self.rule_catalog)
            if missing_rules:
                add("CORE-SCHEMA", f"gate rules absent from catalog: {sorted(missing_rules)}")
        return findings


class ExpressionEvaluator:
    def __init__(
        self,
        registry: CoreRegistry,
        document_id: str,
        quantities: dict[str, dict[str, Any]],
        expression_id: str,
        anchor: str | None,
    ):
        self.registry = registry
        self.document_id = document_id
        self.quantities = quantities
        self.expression_id = expression_id
        self.anchor = anchor
        self.findings: list[Finding] = []

    def add(self, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                document=self.document_id,
                rule=rule,
                severity=self.registry.severity(rule),
                message=message,
                expression=self.expression_id,
                anchor=self.anchor,
            )
        )

    def unknown(self) -> TypeInfo:
        return TypeInfo(
            ZERO_DIMENSION,
            "scalar",
            "scalar",
            "scalar",
            "neutral",
            "none",
        )

    def context_product(self, left: TypeInfo, right: TypeInfo) -> str:
        if left.unit_context in self.registry.neutral_contexts:
            return right.unit_context
        if right.unit_context in self.registry.neutral_contexts:
            return left.unit_context
        if left.unit_context == right.unit_context:
            return left.unit_context
        self.add(
            "NATURAL-UNIT-BOUNDARY",
            f"implicit product across {left.unit_context} and {right.unit_context}",
        )
        return left.unit_context

    def compatible_frames(self, left: TypeInfo, right: TypeInfo) -> bool:
        if left.shape == "scalar" and right.shape == "scalar":
            return True
        if left.frame == right.frame:
            return True
        if left.frame in self.registry.frame_neutral_values:
            return True
        if right.frame in self.registry.frame_neutral_values:
            return True
        return False

    def evaluate(self, node: Any) -> TypeInfo:
        if not isinstance(node, dict):
            self.add("CORE-SCHEMA", f"expression node must be a mapping, got {node!r}")
            return self.unknown()

        if "q" in node:
            qid = str(node["q"])
            record = self.quantities.get(qid)
            if record is None:
                self.add("CORE-SCHEMA", f"unknown quantity {qid}")
                return self.unknown()
            try:
                return self.registry.type_from_record(record)
            except (KeyError, ValueError) as error:
                self.add("DIMENSION-VECTOR", f"{qid}: {error}")
                return self.unknown()

        if "const" in node:
            dimension = parse_dimension(node.get("dimension", [0, 0, 0, 0, 0, 0, 0]))
            semantic_kind = str(node.get("semantic_kind", "scalar"))
            return TypeInfo(
                dimension=dimension,
                semantic_kind=semantic_kind,
                addition_family=self.registry.addition_family(semantic_kind),
                shape=self.registry.shape(semantic_kind),
                unit_context=str(node.get("unit_context", "neutral")),
                frame=str(node.get("frame", "none")),
                normalized=bool(node.get("normalized", dimension == ZERO_DIMENSION)),
                log_base=node.get("log_base"),
            )

        op = str(node.get("op", ""))
        if op in {"add", "sub"}:
            args = node.get("args", [])
            if not isinstance(args, list) or len(args) < 2:
                self.add("CORE-SCHEMA", f"{op} requires at least two arguments")
                return self.unknown()
            result = self.evaluate(args[0])
            for raw in args[1:]:
                other = self.evaluate(raw)
                if result.dimension != other.dimension:
                    self.add(
                        "ADD-DIM",
                        f"{op} mixes {dimension_to_text(result.dimension)} and "
                        f"{dimension_to_text(other.dimension)}",
                    )
                if result.addition_family != other.addition_family:
                    self.add(
                        "ADD-TYPE",
                        f"{op} mixes {result.semantic_kind} and {other.semantic_kind}",
                    )
                if (
                    result.unit_context != other.unit_context
                    and result.unit_context not in self.registry.neutral_contexts
                    and other.unit_context not in self.registry.neutral_contexts
                ):
                    self.add(
                        "NATURAL-UNIT-BOUNDARY",
                        f"{op} crosses {result.unit_context} and {other.unit_context}",
                    )
                if not self.compatible_frames(result, other):
                    self.add(
                        "ADD-FRAME",
                        f"{op} mixes frames {result.frame} and {other.frame}",
                    )
            return result

        if op in {"mul", "div", "dot"}:
            left = self.evaluate(node.get("left"))
            right = self.evaluate(node.get("right"))
            sign = 1 if op in {"mul", "dot"} else -1
            dimension = tuple(
                a + sign * b for a, b in zip(left.dimension, right.dimension, strict=True)
            )
            semantic_kind = "scalar" if op == "dot" else str(node.get("semantic_kind", "scalar"))
            return TypeInfo(
                dimension=dimension,
                semantic_kind=semantic_kind,
                addition_family=self.registry.addition_family(semantic_kind),
                shape=self.registry.shape(semantic_kind),
                unit_context=self.context_product(left, right),
                frame=str(node.get("frame", "scalar" if op == "dot" else "none")),
                normalized=dimension == ZERO_DIMENSION,
            )

        if op in {"pow", "sqrt"}:
            value = self.evaluate(node.get("arg"))
            exponent = Fraction(1, 2) if op == "sqrt" else fraction(node.get("exponent"))
            dimension = tuple(exponent * item for item in value.dimension)
            return TypeInfo(
                dimension=dimension,
                semantic_kind=str(node.get("semantic_kind", value.semantic_kind)),
                addition_family=self.registry.addition_family(
                    str(node.get("semantic_kind", value.semantic_kind))
                ),
                shape=self.registry.shape(str(node.get("semantic_kind", value.semantic_kind))),
                unit_context=value.unit_context,
                frame=value.frame,
                normalized=dimension == ZERO_DIMENSION,
            )

        if op == "norm":
            value = self.evaluate(node.get("arg"))
            semantic_kind = str(node.get("semantic_kind", "scalar"))
            return TypeInfo(
                dimension=value.dimension,
                semantic_kind=semantic_kind,
                addition_family=self.registry.addition_family(semantic_kind),
                shape="scalar",
                unit_context=value.unit_context,
                frame="scalar",
                normalized=value.normalized,
            )

        if op == "normalize":
            numerator = self.evaluate(node.get("value"))
            reference = self.evaluate(node.get("reference"))
            if numerator.dimension != reference.dimension:
                self.add(
                    "ADD-DIM",
                    "normalization numerator and reference have different dimensions",
                )
            if (
                numerator.unit_context != reference.unit_context
                and numerator.unit_context not in self.registry.neutral_contexts
                and reference.unit_context not in self.registry.neutral_contexts
            ):
                self.add(
                    "NATURAL-UNIT-BOUNDARY",
                    "normalization crosses unit contexts without conversion",
                )
            if not node.get("zero_policy"):
                self.add("ZERO-DENOMINATOR", "normalization lacks zero-denominator policy")
            semantic_kind = str(node.get("semantic_kind", "scalar"))
            return TypeInfo(
                dimension=ZERO_DIMENSION,
                semantic_kind=semantic_kind,
                addition_family=self.registry.addition_family(semantic_kind),
                shape=self.registry.shape(semantic_kind),
                unit_context="neutral",
                frame="none",
                normalized=True,
            )

        if op == "log":
            argument = self.evaluate(node.get("arg"))
            if argument.dimension != ZERO_DIMENSION:
                self.add(
                    "LOG-DIM",
                    f"log argument has dimension {dimension_to_text(argument.dimension)}",
                )
            if node.get("base") is None:
                self.add("LOG-BASE", "logarithm lacks an explicit base")
            semantic_kind = str(node.get("semantic_kind", "scalar"))
            return TypeInfo(
                dimension=ZERO_DIMENSION,
                semantic_kind=semantic_kind,
                addition_family=self.registry.addition_family(semantic_kind),
                shape=self.registry.shape(semantic_kind),
                unit_context="neutral",
                frame="none",
                normalized=True,
                log_base=node.get("base"),
            )

        if op == "exp":
            argument = self.evaluate(node.get("arg"))
            if argument.dimension != ZERO_DIMENSION:
                self.add(
                    "EXP-DIM",
                    f"exponential argument has dimension {dimension_to_text(argument.dimension)}",
                )
            return TypeInfo(
                ZERO_DIMENSION, "scalar", "scalar", "scalar", "neutral", "none", True
            )

        if op == "trig":
            argument = self.evaluate(node.get("arg"))
            if argument.dimension != ZERO_DIMENSION or argument.semantic_kind != "angle":
                self.add(
                    "TRIG-TYPE",
                    f"trigonometric argument is {argument.semantic_kind} with "
                    f"dimension {dimension_to_text(argument.dimension)}",
                )
            return TypeInfo(
                ZERO_DIMENSION, "scalar", "scalar", "scalar", "neutral", "none", True
            )

        if op == "derivative":
            dependent = self.evaluate(node.get("dependent"))
            independent = self.evaluate(node.get("independent"))
            dimension = tuple(
                a - b for a, b in zip(dependent.dimension, independent.dimension, strict=True)
            )
            return TypeInfo(
                dimension,
                dependent.semantic_kind,
                dependent.addition_family,
                dependent.shape,
                self.context_product(dependent, independent),
                dependent.frame,
            )

        if op == "integrate":
            integrand = self.evaluate(node.get("integrand"))
            if "measure" not in node:
                self.add("MEASURE-DIM", "integral lacks a typed measure")
                return integrand
            measure = self.evaluate(node.get("measure"))
            dimension = tuple(
                a + b for a, b in zip(integrand.dimension, measure.dimension, strict=True)
            )
            return TypeInfo(
                dimension,
                integrand.semantic_kind,
                integrand.addition_family,
                integrand.shape,
                self.context_product(integrand, measure),
                integrand.frame,
            )

        if op == "compare":
            left = self.evaluate(node.get("left"))
            right = self.evaluate(node.get("right"))
            if left.dimension != right.dimension:
                self.add(
                    "COMPARE-DIM",
                    f"comparison mixes {dimension_to_text(left.dimension)} and "
                    f"{dimension_to_text(right.dimension)}",
                )
            if (
                left.addition_family != right.addition_family
                and left.semantic_kind != "scalar"
                and right.semantic_kind != "scalar"
            ):
                self.add(
                    "COMPARE-TYPE",
                    f"comparison mixes {left.semantic_kind} and {right.semantic_kind}",
                )
            return TypeInfo(
                ZERO_DIMENSION, "probability", "probability", "scalar", "neutral", "none", True
            )

        if op == "convert":
            argument = self.evaluate(node.get("arg"))
            target = str(node.get("to"))
            if target not in self.registry.contexts:
                self.add("CORE-SCHEMA", f"unknown conversion target {target}")
            if argument.unit_context != target and not node.get("constants"):
                self.add(
                    "NATURAL-UNIT-BOUNDARY",
                    f"conversion {argument.unit_context}->{target} lacks constants",
                )
            return TypeInfo(
                argument.dimension,
                argument.semantic_kind,
                argument.addition_family,
                argument.shape,
                target,
                argument.frame,
                argument.normalized,
                argument.log_base,
            )

        if op == "aggregate":
            terms = node.get("terms", [])
            if not isinstance(terms, list) or not terms:
                self.add("DEFECT-CODOMAIN", "aggregate has no terms")
            for term in terms if isinstance(terms, list) else []:
                value = self.evaluate(term)
                if value.dimension != ZERO_DIMENSION or not value.normalized:
                    self.add(
                        "DEFECT-CODOMAIN",
                        "aggregate contains a raw or dimensional component",
                    )
            return TypeInfo(
                ZERO_DIMENSION, "loss", "loss", "scalar", "neutral", "none", True
            )

        self.add("CORE-SCHEMA", f"unsupported expression operation {op!r}")
        return self.unknown()


class CorpusLinter:
    def __init__(self, registry: CoreRegistry, ledger_data: dict[str, Any]):
        self.registry = registry
        self.ledger_data = ledger_data

    def finding(
        self,
        document: str,
        rule: str,
        message: str,
        *,
        expression: str | None = None,
        anchor: str | None = None,
        detected_by: str = "automatic",
        severity: str | None = None,
    ) -> Finding:
        return Finding(
            document=document,
            rule=rule,
            severity=severity or self.registry.severity(rule),
            message=message,
            expression=expression,
            anchor=anchor,
            detected_by=detected_by,
        )

    def lint_document(self, document: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        doc_id = str(document.get("id", "<missing>"))

        for field in self.registry.spec.get("document_required_fields", []):
            if field not in document:
                findings.append(
                    self.finding(doc_id, "CORE-SCHEMA", f"document missing {field}")
                )

        ledger_level = document.get("ledger_level")
        if ledger_level not in self.registry.spec.get("ledger_levels", {}):
            findings.append(
                self.finding(doc_id, "CORE-SCHEMA", f"unknown ledger level {ledger_level}")
            )
        elif not self.registry.spec["ledger_levels"][ledger_level]["p1_gate_eligible"]:
            findings.append(
                self.finding(
                    doc_id,
                    "COVERAGE-INCOMPLETE",
                    "critical-formula adapter is not complete enough for a P1 pass",
                )
            )

        unit_contexts = document.get("unit_contexts", [])
        for context in unit_contexts:
            if context not in self.registry.contexts:
                findings.append(
                    self.finding(doc_id, "CORE-SCHEMA", f"unknown unit context {context}")
                )

        map_ids: set[str] = set()
        for mapping in document.get("maps", []):
            map_id = str(mapping.get("id", "<missing>"))
            if map_id in map_ids:
                findings.append(
                    self.finding(doc_id, "MAP-SIGNATURES", f"duplicate map id {map_id}")
                )
            map_ids.add(map_id)
            for field in ("id", "domain", "codomain", "kind", "invertibility"):
                if mapping.get(field) in (None, ""):
                    findings.append(
                        self.finding(
                            doc_id, "MAP-SIGNATURES", f"{map_id} missing {field}"
                        )
                    )
            kind = mapping.get("kind")
            if kind not in self.registry.operator_kinds:
                findings.append(
                    self.finding(doc_id, "MAP-SIGNATURES", f"{map_id} has unknown kind")
                )
            if (
                kind in {"frame_transform", "gauge_transform"}
                and mapping.get("information_loss") is not False
            ):
                findings.append(
                    self.finding(
                        doc_id,
                        "FRAME-CHANNEL-SEPARATION",
                        f"{map_id} is an invertible representation change marked lossy",
                    )
                )

        symbol_pairs: set[tuple[str, str]] = set()
        for symbol in document.get("symbols", []):
            pair = (str(symbol.get("scope")), str(symbol.get("key")))
            if pair in symbol_pairs:
                findings.append(
                    self.finding(
                        doc_id, "SYMBOL-COLLISION", f"duplicate symbol in scope {pair}"
                    )
                )
            symbol_pairs.add(pair)

        quantity_records = self.registry.merged_quantity_records(document)
        local_ids: set[str] = set()
        for quantity in document.get("quantities", []):
            qid = quantity.get("id")
            if not qid:
                findings.append(
                    self.finding(doc_id, "CORE-SCHEMA", "local quantity missing id")
                )
                continue
            if qid in local_ids:
                findings.append(
                    self.finding(doc_id, "CORE-SCHEMA", f"duplicate local quantity {qid}")
                )
            local_ids.add(str(qid))
            record = quantity_records.get(str(qid), {})
            try:
                self.registry.type_from_record(record)
            except (KeyError, ValueError) as error:
                findings.append(
                    self.finding(doc_id, "DIMENSION-VECTOR", f"{qid}: {error}")
                )

        for claim in document.get("claim_register", []):
            claim_id = str(claim.get("id", "<missing>"))
            status = claim.get("status")
            if status not in self.registry.claim_statuses:
                findings.append(
                    self.finding(
                        doc_id, "CLAIM-STATUS", f"{claim_id} has invalid status {status}"
                    )
                )
            if status in self.registry.strong_claim_statuses:
                hypotheses = claim.get("hypotheses")
                if not isinstance(hypotheses, list) or not hypotheses:
                    findings.append(
                        self.finding(
                            doc_id,
                            "CLAIM-STATUS",
                            f"{claim_id} lacks a nonempty hypothesis list",
                        )
                    )

        groups = set(document.get("groups", []))
        for invariant in document.get("invariants", []):
            if invariant.get("claimed_invariant") is True:
                group = invariant.get("group")
                if not group or group not in groups:
                    findings.append(
                        self.finding(
                            doc_id,
                            "FRAME-LAW",
                            f"{invariant.get('id', '<missing>')} is called invariant "
                            "without a declared transformation group",
                            anchor=invariant.get("anchor"),
                        )
                    )

        if ledger_level == "reference":
            present = set(document.get("protocol_fields_present", []))
            missing = self.registry.protocol_required - present
            if missing:
                findings.append(
                    self.finding(
                        doc_id,
                        "PROTOCOL-COMPLETE",
                        f"reference ledger lacks protocol fields {sorted(missing)}",
                    )
                )

        for expression in document.get("expressions", []):
            expression_id = str(expression.get("id", "<missing>"))
            anchor = expression.get("anchor")
            evaluator = ExpressionEvaluator(
                self.registry, doc_id, quantity_records, expression_id, anchor
            )
            result = evaluator.evaluate(expression.get("ast"))
            expression_findings = evaluator.findings

            expected = expression.get("expect", {})
            expected_dimension = expected.get("dimension")
            if expected_dimension is not None:
                try:
                    parsed_expected = parse_dimension(expected_dimension)
                    if result.dimension != parsed_expected:
                        expression_findings.append(
                            self.finding(
                                doc_id,
                                "RESULT-DIM",
                                f"result has {dimension_to_text(result.dimension)}, expected "
                                f"{dimension_to_text(parsed_expected)}",
                                expression=expression_id,
                                anchor=anchor,
                            )
                        )
                except ValueError as error:
                    expression_findings.append(
                        self.finding(
                            doc_id,
                            "DIMENSION-VECTOR",
                            f"invalid expected dimension: {error}",
                            expression=expression_id,
                            anchor=anchor,
                        )
                    )
            expected_kind = expected.get("semantic_kind")
            if expected_kind is not None and result.semantic_kind != expected_kind:
                expression_findings.append(
                    self.finding(
                        doc_id,
                        "RESULT-TYPE",
                        f"result is {result.semantic_kind}, expected {expected_kind}",
                        expression=expression_id,
                        anchor=anchor,
                    )
                )
            expected_frame = expected.get("frame")
            if expected_frame is not None and result.frame != expected_frame:
                expression_findings.append(
                    self.finding(
                        doc_id,
                        "RESULT-FRAME",
                        f"result frame is {result.frame}, expected {expected_frame}",
                        expression=expression_id,
                        anchor=anchor,
                    )
                )

            expected_rules = set(expected.get("rules", []))
            observed_rules = {item.rule for item in expression_findings}
            if not expected_rules.issubset(observed_rules):
                expression_findings.append(
                    self.finding(
                        doc_id,
                        "EXPECTATION-MISMATCH",
                        f"expected rules {sorted(expected_rules)}, observed "
                        f"{sorted(observed_rules)}",
                        expression=expression_id,
                        anchor=anchor,
                    )
                )
            if expected.get("outcome") == "pass" and expression_findings:
                expression_findings.append(
                    self.finding(
                        doc_id,
                        "EXPECTATION-MISMATCH",
                        "expression marked pass produced findings",
                        expression=expression_id,
                        anchor=anchor,
                    )
                )
            if expected.get("outcome") == "fail" and not expression_findings:
                expression_findings.append(
                    self.finding(
                        doc_id,
                        "EXPECTATION-MISMATCH",
                        "expression marked fail produced no finding",
                        expression=expression_id,
                        anchor=anchor,
                    )
                )
            findings.extend(expression_findings)

        for manual in document.get("manual_findings", []):
            rule = str(manual.get("rule", "CORE-SCHEMA"))
            findings.append(
                self.finding(
                    doc_id,
                    rule,
                    str(manual.get("message", "manual finding")),
                    anchor=manual.get("anchor"),
                    detected_by="review",
                    severity=manual.get("severity"),
                )
            )
        return findings

    def lint(
        self, *, only_level: str | None = None
    ) -> tuple[list[Finding], list[dict[str, Any]]]:
        findings = self.registry.validate()
        documents = self.ledger_data.get("documents", [])
        selected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_hashes: dict[str, str] = {}

        for document in documents:
            if only_level and document.get("ledger_level") != only_level:
                continue
            selected.append(document)
            doc_id = str(document.get("id", "<missing>"))
            if doc_id in seen_ids:
                findings.append(
                    self.finding(doc_id, "CORE-SCHEMA", f"duplicate document id {doc_id}")
                )
            seen_ids.add(doc_id)
            source_hash = document.get("source", {}).get("sha256")
            if source_hash:
                if source_hash in seen_hashes:
                    findings.append(
                        self.finding(
                            doc_id,
                            "DUPLICATE-SOURCE",
                            f"same source hash as {seen_hashes[source_hash]}",
                        )
                    )
                else:
                    seen_hashes[source_hash] = doc_id
            findings.extend(self.lint_document(document))

        for duplicate in self.ledger_data.get("duplicate_or_superseded_sources", []):
            if duplicate.get("status") == "duplicate":
                canonical_document = str(
                    duplicate.get("canonical_document", "__corpus__")
                )
                if only_level and canonical_document not in seen_ids:
                    continue
                findings.append(
                    self.finding(
                        canonical_document,
                        "DUPLICATE-SOURCE",
                        f"{duplicate.get('path')} duplicates "
                        f"{duplicate.get('canonical_path')}",
                        detected_by="automatic",
                    )
                )
        return findings, selected


def document_status(findings: Iterable[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if "error" in severities:
        return "FAIL"
    if "blocker" in severities:
        return "BLOCKED"
    if "warning" in severities:
        return "REVIEW"
    return "PASS"


def build_report(
    registry: CoreRegistry,
    ledger_data: dict[str, Any],
    documents: list[dict[str, Any]],
    findings: list[Finding],
) -> dict[str, Any]:
    by_doc: dict[str, list[Finding]] = {str(doc["id"]): [] for doc in documents}
    core_findings: list[Finding] = []
    for finding in findings:
        if finding.document in by_doc:
            by_doc[finding.document].append(finding)
        else:
            core_findings.append(finding)

    document_rows: list[dict[str, Any]] = []
    for document in documents:
        doc_id = str(document["id"])
        items = by_doc[doc_id]
        counts = Counter(item.severity for item in items)
        mode_counts = Counter(item.detected_by for item in items)
        document_rows.append(
            {
                "id": doc_id,
                "title": document.get("title"),
                "version": document.get("version"),
                "ledger_level": document.get("ledger_level"),
                "migration_status": document.get("migration_status"),
                "expressions": len(document.get("expressions", [])),
                "automatic_findings": mode_counts.get("automatic", 0),
                "review_findings": mode_counts.get("review", 0),
                "errors": counts.get("error", 0),
                "blockers": counts.get("blocker", 0),
                "warnings": counts.get("warning", 0),
                "status": document_status(items),
                "next_action": document.get("next_action"),
            }
        )

    status_counts = Counter(row["status"] for row in document_rows)
    rule_counts = Counter(item.rule for item in findings if item.document != "__core__")
    return {
        "schema": {
            "id": "go-lint-corpus-report",
            "version": "0.2.0",
            "core_contract": registry.spec.get("schema", {}).get("version"),
            "corpus_id": ledger_data.get("schema", {}).get("id"),
        },
        "summary": {
            "canonical_documents": len(document_rows),
            "reference_documents": sum(
                row["ledger_level"] == "reference" for row in document_rows
            ),
            "critical_adapters": sum(
                row["ledger_level"] == "critical_adapter" for row in document_rows
            ),
            "expressions_checked": sum(row["expressions"] for row in document_rows),
            "findings_total": len(findings),
            "core_findings": len(core_findings),
            "status_counts": dict(sorted(status_counts.items())),
            "rule_counts": dict(sorted(rule_counts.items())),
        },
        "documents": document_rows,
        "findings": [asdict(item) for item in findings],
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# GO Core v0.2 — отчёт линтера по корпусу",
        "",
        "Статус этого отчёта: машинный аудит типизированных ledgers. Для старых PDF "
        "использованы адаптеры критических формул; это не полное синтаксическое "
        "доказательство корректности каждой формулы.",
        "",
        "## Сводка",
        "",
        f"- канонических документов: {summary['canonical_documents']};",
        f"- полных эталонных ledgers: {summary['reference_documents']};",
        f"- адаптеров критических формул: {summary['critical_adapters']};",
        f"- проверенных выражений: {summary['expressions_checked']};",
        f"- всех находок: {summary['findings_total']};",
        f"- статусы: `{summary['status_counts']}`.",
        "",
        "## Статусы документов",
        "",
        "| Документ | Ledger | Выражения | Auto | Review | Ошибки | Блокеры | Статус |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["documents"]:
        lines.append(
            f"| `{row['id']}` | {row['ledger_level']} | {row['expressions']} | "
            f"{row['automatic_findings']} | {row['review_findings']} | "
            f"{row['errors']} | {row['blockers']} | **{row['status']}** |"
        )

    lines.extend(["", "## Находки по правилам", ""])
    for rule, count in report["summary"]["rule_counts"].items():
        lines.append(f"- `{rule}`: {count}")

    lines.extend(["", "## Детальная карта исправлений", ""])
    rows_by_id = {row["id"]: row for row in report["documents"]}
    findings_by_doc: dict[str, list[dict[str, Any]]] = {}
    for item in report["findings"]:
        findings_by_doc.setdefault(item["document"], []).append(item)
    for doc_id, row in rows_by_id.items():
        lines.extend(
            [
                f"### {row['title']} ({row['version']})",
                "",
                f"Статус: **{row['status']}**. Следующее действие: {row['next_action']}",
                "",
            ]
        )
        items = findings_by_doc.get(doc_id, [])
        if not items:
            lines.append("- Нарушений не найдено в заявленном покрытии.")
        else:
            for item in items:
                anchor = f" [{item['anchor']}]" if item.get("anchor") else ""
                mode = "AUTO" if item.get("detected_by") == "automatic" else "REVIEW"
                lines.append(
                    f"- `{item['severity'].upper()}` `{item['rule']}` ({mode})"
                    f"{anchor}: {item['message']}"
                )
        lines.append("")

    lines.extend(
        [
            "## Интерпретация шлюза",
            "",
            "- `PASS` означает прохождение зарегистрированного P0/P1-контракта.",
            "- `FAIL` означает обнаруженную формульную, типовую, кадровую или "
            "семантическую ошибку.",
            "- `BLOCKED` означает, что критические примеры не дали ошибки, но "
            "покрытие старого PDF недостаточно для строгого P1-pass.",
            "- `REVIEW` означает отсутствие ошибок и блокеров при наличии "
            "нефатальных замечаний.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--core-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "core",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "ledgers"
        / "corpus_ledgers_v0_1.yaml",
    )
    parser.add_argument("--only-level", choices=["reference", "critical_adapter"])
    parser.add_argument("--mode", choices=["audit", "strict"], default="audit")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    try:
        registry = CoreRegistry(args.core_dir)
        ledger_data = load_yaml(args.ledger)
    except (OSError, KeyError, ValueError, yaml.YAMLError) as error:
        print(f"FATAL: {error}", file=sys.stderr)
        return 2

    linter = CorpusLinter(registry, ledger_data)
    findings, documents = linter.lint(only_level=args.only_level)
    report = build_report(registry, ledger_data, documents, findings)
    if args.output_json:
        write_json(args.output_json, report)
    if args.output_md:
        write_markdown(args.output_md, markdown_report(report))

    summary = report["summary"]
    print(
        "GO-LINT "
        f"documents={summary['canonical_documents']} "
        f"expressions={summary['expressions_checked']} "
        f"findings={summary['findings_total']} "
        f"statuses={summary['status_counts']}"
    )
    core_errors = [
        item
        for item in findings
        if item.document == "__core__" and item.severity in {"error", "blocker"}
    ]
    if core_errors:
        for item in core_errors:
            print(f"CORE {item.rule}: {item.message}", file=sys.stderr)
        return 2
    if args.mode == "strict":
        blocking = [
            item
            for item in findings
            if item.severity in {"error", "blocker"}
            and item.rule != "COVERAGE-INCOMPLETE"
        ]
        incomplete = [
            item for item in findings if item.rule == "COVERAGE-INCOMPLETE"
        ]
        if blocking or incomplete:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

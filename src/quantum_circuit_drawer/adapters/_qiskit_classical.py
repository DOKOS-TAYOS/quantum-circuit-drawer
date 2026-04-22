"""Qiskit classical-expression helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NamedTuple, SupportsIndex, SupportsInt, cast

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR

QISKIT_EXPR_SENTINEL = object()
QISKIT_EXPR_PRECEDENCE_ATOM = 100
QISKIT_EXPR_PRECEDENCE_UNARY = 90
QISKIT_EXPR_PRECEDENCE_MULTIPLICATIVE = 80
QISKIT_EXPR_PRECEDENCE_ADDITIVE = 70
QISKIT_EXPR_PRECEDENCE_SHIFT = 60
QISKIT_EXPR_PRECEDENCE_BITWISE = 50
QISKIT_EXPR_PRECEDENCE_COMPARISON = 40
QISKIT_EXPR_PRECEDENCE_LOGICAL = 30


class RenderedQiskitClassicalExpression(NamedTuple):
    text: str
    wire_ids: tuple[str, ...]
    precedence: int
    is_atomic: bool


def switch_target_from_qiskit(
    target: object,
    classical_targets: Mapping[object, tuple[str, str]],
    register_targets: Mapping[object, tuple[str, str]],
) -> tuple[ClassicalConditionIR, str]:
    if is_known_classical_target(target, classical_targets):
        wire_id, bit_label = classical_targets[target]
        return ClassicalConditionIR(
            wire_ids=(wire_id,),
            expression=f"switch on {bit_label}",
        ), bit_label
    if is_known_classical_target(target, register_targets):
        wire_id, register_label = register_targets[target]
        return ClassicalConditionIR(
            wire_ids=(wire_id,),
            expression=f"switch on {register_label}",
        ), register_label
    rendered = render_qiskit_classical_expression(target, classical_targets, register_targets)
    return (
        ClassicalConditionIR(
            wire_ids=rendered.wire_ids,
            expression=f"switch on {rendered.text}",
        ),
        rendered.text,
    )


def condition_from_qiskit(
    condition: object,
    classical_targets: Mapping[object, tuple[str, str]],
    register_targets: Mapping[object, tuple[str, str]],
) -> ClassicalConditionIR:
    if isinstance(condition, tuple) and len(condition) == 2:
        lhs, value = condition
        rendered_value = render_qiskit_classical_literal(value)
        if is_known_classical_target(lhs, classical_targets):
            wire_id, bit_label = classical_targets[lhs]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"if {bit_label}={rendered_value}",
            )
        if is_known_classical_target(lhs, register_targets):
            wire_id, register_label = register_targets[lhs]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"if {register_label}={rendered_value}",
            )
        raise UnsupportedOperationError("unsupported Qiskit classical condition target")

    rendered = render_qiskit_classical_expression(
        condition,
        classical_targets,
        register_targets,
    )
    return ClassicalConditionIR(
        wire_ids=rendered.wire_ids,
        expression=f"if {rendered.text}",
    )


def render_qiskit_classical_expression(
    value: object,
    classical_targets: Mapping[object, tuple[str, str]],
    register_targets: Mapping[object, tuple[str, str]],
) -> RenderedQiskitClassicalExpression:
    if is_known_classical_target(value, classical_targets):
        wire_id, bit_label = classical_targets[value]
        return RenderedQiskitClassicalExpression(
            text=bit_label,
            wire_ids=(wire_id,),
            precedence=QISKIT_EXPR_PRECEDENCE_ATOM,
            is_atomic=True,
        )
    if is_known_classical_target(value, register_targets):
        wire_id, register_label = register_targets[value]
        return RenderedQiskitClassicalExpression(
            text=register_label,
            wire_ids=(wire_id,),
            precedence=QISKIT_EXPR_PRECEDENCE_ATOM,
            is_atomic=True,
        )

    variable = getattr(value, "var", QISKIT_EXPR_SENTINEL)
    if variable is not QISKIT_EXPR_SENTINEL:
        return render_qiskit_classical_expression(
            variable,
            classical_targets,
            register_targets,
        )

    literal_value = getattr(value, "value", QISKIT_EXPR_SENTINEL)
    if literal_value is not QISKIT_EXPR_SENTINEL:
        return RenderedQiskitClassicalExpression(
            text=render_qiskit_classical_literal(literal_value),
            wire_ids=(),
            precedence=QISKIT_EXPR_PRECEDENCE_ATOM,
            is_atomic=True,
        )

    operand = getattr(value, "operand", QISKIT_EXPR_SENTINEL)
    if operand is not QISKIT_EXPR_SENTINEL:
        return render_qiskit_unary_expression(
            op=getattr(value, "op", None),
            operand=operand,
            classical_targets=classical_targets,
            register_targets=register_targets,
        )

    left = getattr(value, "left", QISKIT_EXPR_SENTINEL)
    right = getattr(value, "right", QISKIT_EXPR_SENTINEL)
    if left is not QISKIT_EXPR_SENTINEL and right is not QISKIT_EXPR_SENTINEL:
        return render_qiskit_binary_expression(
            op=getattr(value, "op", None),
            left=left,
            right=right,
            classical_targets=classical_targets,
            register_targets=register_targets,
        )

    raise UnsupportedOperationError("unsupported Qiskit classical condition shape")


def render_qiskit_unary_expression(
    *,
    op: object,
    operand: object,
    classical_targets: Mapping[object, tuple[str, str]],
    register_targets: Mapping[object, tuple[str, str]],
) -> RenderedQiskitClassicalExpression:
    op_name = qiskit_operator_name(op)
    if op_name is None:
        raise UnsupportedOperationError("unsupported Qiskit classical condition shape")
    operator_text = {
        "LOGIC_NOT": "!",
        "BIT_NOT": "~",
    }.get(op_name)
    if operator_text is None:
        raise UnsupportedOperationError("unsupported Qiskit classical condition shape")

    rendered_operand = render_qiskit_classical_expression(
        operand,
        classical_targets,
        register_targets,
    )
    operand_text = wrap_qiskit_expression(
        rendered_operand,
        parent_precedence=QISKIT_EXPR_PRECEDENCE_UNARY,
        wrap_non_atomic=True,
    )
    return RenderedQiskitClassicalExpression(
        text=f"{operator_text}{operand_text}",
        wire_ids=rendered_operand.wire_ids,
        precedence=QISKIT_EXPR_PRECEDENCE_UNARY,
        is_atomic=False,
    )


def render_qiskit_binary_expression(
    *,
    op: object,
    left: object,
    right: object,
    classical_targets: Mapping[object, tuple[str, str]],
    register_targets: Mapping[object, tuple[str, str]],
) -> RenderedQiskitClassicalExpression:
    rendered_left = render_qiskit_classical_expression(
        left,
        classical_targets,
        register_targets,
    )
    rendered_right = render_qiskit_classical_expression(
        right,
        classical_targets,
        register_targets,
    )
    wire_ids = merge_qiskit_expression_wire_ids(
        rendered_left.wire_ids,
        rendered_right.wire_ids,
    )
    op_name = qiskit_operator_name(op)
    if op_name is None:
        raise UnsupportedOperationError("unsupported Qiskit classical condition shape")

    if op_name in {"LOGIC_AND", "LOGIC_OR"}:
        operator_text = "&&" if op_name == "LOGIC_AND" else "||"
        return RenderedQiskitClassicalExpression(
            text=(
                f"{wrap_qiskit_expression(rendered_left, parent_precedence=QISKIT_EXPR_PRECEDENCE_LOGICAL, wrap_non_atomic=True)} "
                f"{operator_text} "
                f"{wrap_qiskit_expression(rendered_right, parent_precedence=QISKIT_EXPR_PRECEDENCE_LOGICAL, wrap_non_atomic=True)}"
            ),
            wire_ids=wire_ids,
            precedence=QISKIT_EXPR_PRECEDENCE_LOGICAL,
            is_atomic=False,
        )

    if op_name in {
        "EQUAL",
        "NOT_EQUAL",
        "LESS",
        "LESS_EQUAL",
        "GREATER",
        "GREATER_EQUAL",
    }:
        operator_text = {
            "EQUAL": "=",
            "NOT_EQUAL": "!=",
            "LESS": "<",
            "LESS_EQUAL": "<=",
            "GREATER": ">",
            "GREATER_EQUAL": ">=",
        }[op_name]
        return RenderedQiskitClassicalExpression(
            text=(
                f"{wrap_qiskit_expression(rendered_left, parent_precedence=QISKIT_EXPR_PRECEDENCE_COMPARISON)}"
                f"{operator_text}"
                f"{wrap_qiskit_expression(rendered_right, parent_precedence=QISKIT_EXPR_PRECEDENCE_COMPARISON)}"
            ),
            wire_ids=wire_ids,
            precedence=QISKIT_EXPR_PRECEDENCE_COMPARISON,
            is_atomic=False,
        )

    operator_spec = {
        "BIT_AND": ("&", QISKIT_EXPR_PRECEDENCE_BITWISE),
        "BIT_OR": ("|", QISKIT_EXPR_PRECEDENCE_BITWISE),
        "BIT_XOR": ("^", QISKIT_EXPR_PRECEDENCE_BITWISE),
        "SHIFT_LEFT": ("<<", QISKIT_EXPR_PRECEDENCE_SHIFT),
        "SHIFT_RIGHT": (">>", QISKIT_EXPR_PRECEDENCE_SHIFT),
        "ADD": ("+", QISKIT_EXPR_PRECEDENCE_ADDITIVE),
        "SUB": ("-", QISKIT_EXPR_PRECEDENCE_ADDITIVE),
        "MUL": ("*", QISKIT_EXPR_PRECEDENCE_MULTIPLICATIVE),
        "DIV": ("/", QISKIT_EXPR_PRECEDENCE_MULTIPLICATIVE),
    }.get(op_name)
    if operator_spec is None:
        raise UnsupportedOperationError("unsupported Qiskit classical condition shape")
    operator_text, precedence = operator_spec

    return RenderedQiskitClassicalExpression(
        text=(
            f"{wrap_qiskit_expression(rendered_left, parent_precedence=precedence)} "
            f"{operator_text} "
            f"{wrap_qiskit_expression(rendered_right, parent_precedence=precedence)}"
        ),
        wire_ids=wire_ids,
        precedence=precedence,
        is_atomic=False,
    )


def wrap_qiskit_expression(
    rendered: RenderedQiskitClassicalExpression,
    *,
    parent_precedence: int,
    wrap_non_atomic: bool = False,
) -> str:
    if rendered.precedence < parent_precedence or (wrap_non_atomic and not rendered.is_atomic):
        return f"({rendered.text})"
    return rendered.text


def qiskit_operator_name(op: object) -> str | None:
    name = getattr(op, "name", None)
    return name if isinstance(name, str) else None


def render_qiskit_classical_literal(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    try:
        coerced = int(coercible_qiskit_literal(value))
    except (TypeError, ValueError):
        text = native_text(value)
        if text:
            return text
        raise UnsupportedOperationError("unsupported Qiskit classical literal") from None
    return str(coerced)


def coercible_qiskit_literal(
    value: object,
) -> str | bytes | bytearray | SupportsInt | SupportsIndex:
    if isinstance(value, str | bytes | bytearray):
        return value
    if hasattr(value, "__int__") or hasattr(value, "__index__"):
        return cast("SupportsInt | SupportsIndex", value)
    raise TypeError("unsupported Qiskit classical literal")


def merge_qiskit_expression_wire_ids(
    *groups: Sequence[str],
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for wire_id in group:
            if wire_id not in seen:
                seen.add(wire_id)
                merged.append(wire_id)
    return tuple(merged)


def is_known_classical_target(
    value: object,
    targets: Mapping[object, tuple[str, str]],
) -> bool:
    try:
        return value in targets
    except TypeError:
        return False


def native_text(value: object) -> str:
    if value is None:
        return "None"
    text = str(value).strip()
    if text:
        return text
    return value.__class__.__name__

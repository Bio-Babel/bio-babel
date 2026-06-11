"""Derive MCP ``inputSchema`` objects from handler signatures.

Every tool handler follows one convention: ``handler(registry, *, <agent args>)``
(the meta tools take no agent args at all). The agent-facing parameters are
exactly the keyword-only ones; the leading ``registry`` is bound by the server
with :func:`functools.partial`, which :func:`inspect.signature` then strips for
us. So the schema falls straight out of the existing convention — no per-tool
schema tables to maintain and drift.

Annotations are intentionally resolved with :func:`typing.get_type_hints`
(the handler modules use ``from __future__ import annotations``, so raw
``param.annotation`` values are strings). An annotation that cannot be resolved
is left to raise rather than be swallowed — a broken handler signature is a bug
to surface, not to paper over.
"""

from __future__ import annotations

import functools
import inspect
import types
import typing
from collections.abc import Callable
from typing import Any, Literal, Union, get_args, get_origin

_PRIMITIVES: dict[type, str] = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
}


def _map_type(annotation: Any) -> dict[str, Any]:
    """Map a resolved type annotation to a JSON Schema fragment.

    Covers the constructs the handlers actually use: primitives, ``X | None``
    (and ``Optional[X]``), ``list[...]``, and ``Literal[...]`` enums. Anything
    else maps to ``{}`` — the JSON Schema for "unconstrained", which is the
    honest representation of a type this mapper does not narrow.
    """
    origin = get_origin(annotation)

    if origin in (Union, types.UnionType):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return _map_type(non_none[0]) if len(non_none) == 1 else {}

    if origin is Literal:
        choices = list(get_args(annotation))
        schema: dict[str, Any] = {"enum": choices}
        json_type = _PRIMITIVES.get(type(choices[0])) if choices else None
        if json_type:
            schema["type"] = json_type
        return schema

    if origin in (list, tuple):
        args = get_args(annotation)
        item = _map_type(args[0]) if args else {}
        return {"type": "array", "items": item} if item else {"type": "array"}

    if annotation in _PRIMITIVES:
        return {"type": _PRIMITIVES[annotation]}

    return {}


def build_input_schema(handler: Callable[..., Any]) -> dict[str, Any]:
    """Build an MCP ``inputSchema`` from a wired tool handler.

    ``handler`` is whatever the server stored — a ``functools.partial`` over the
    real handler (registry pre-bound) or a closure. ``inspect.signature`` strips
    partial-bound positionals, so only the agent-facing keyword-only parameters
    remain.
    """
    target = handler.func if isinstance(handler, functools.partial) else handler
    hints = typing.get_type_hints(target)
    signature = inspect.signature(handler)

    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in signature.parameters.items():
        if param.kind is not inspect.Parameter.KEYWORD_ONLY:
            continue
        properties[name] = _map_type(hints.get(name, str))
        if param.default is inspect.Parameter.empty:
            required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema

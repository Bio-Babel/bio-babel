"""Schema v1 for Bio-Babel producer contracts.

The contract is an agent knowledge surface, not a workflow engine input.  It
describes what a package can do, how to call its public symbols, reusable
composition idioms, and common mistakes.  Natural-language planning stays with
the calling agent; biobabel only serves precise facts and runs complete code
snippets on request.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContractClass = Literal["analysis", "grammar", "mixed"]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RPackageRef(_Frozen):
    package: str
    repo: str = ""
    version_or_commit: str = ""
    fidelity: Literal["full", "partial", "subset"] = "partial"


class Parameter(_Frozen):
    name: str
    type: str = ""
    required: bool = False
    default: Any = None
    description: str = ""


class FailureFix(_Frozen):
    when: str
    suggest: list[str]
    explanation: str = ""


class SymbolContract(_Frozen):
    """Precise calling knowledge for one public package symbol."""

    id: str
    import_path: str
    kind: Literal["function", "class", "method", "constant", "object"] = "function"
    signature: str = ""
    purpose: str = ""
    description: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    mutates: str = ""
    returns: str = ""
    requires: list[str] = Field(default_factory=list)
    writes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    failure_fixes: list[FailureFix] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _fill_description(self) -> SymbolContract:
        if not self.description and self.purpose:
            object.__setattr__(self, "description", self.purpose)
        return self


class WorkflowInput(_Frozen):
    name: str = ""
    kind: str = ""
    description: str = ""
    requirements: list[str] = Field(default_factory=list)


class WorkflowStep(_Frozen):
    """One reference step in an agent-readable workflow."""

    symbol: str
    purpose: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class WorkflowContract(_Frozen):
    id: str
    title: str = ""
    description: str = ""
    task_tags: list[str] = Field(default_factory=list)
    when_to_use: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    inputs: list[WorkflowInput] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)
    templates: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class TemplateParameter(_Frozen):
    name: str
    type: str = ""
    required: bool = False
    default: Any = None
    description: str = ""


class TemplateSpec(_Frozen):
    """Reusable script or function skeleton that an agent can adapt."""

    id: str
    path: str = ""
    task_tags: list[str] = Field(default_factory=list)
    description: str = ""
    parameters: list[TemplateParameter] = Field(default_factory=list)
    code_template: str = ""
    expected_artifacts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ConceptSpec(_Frozen):
    id: str
    name: str
    category: str = ""
    description: str
    invariants: list[str] = Field(default_factory=list)
    mental_model: str = ""
    related_concepts: list[str] = Field(default_factory=list)


class IdiomSpec(_Frozen):
    id: str
    name: str
    applicable_to: list[str] = Field(default_factory=list)
    description: str
    code_template: str
    anti_pattern_paired: str | None = None
    typical_use_case: str = ""


class AntiPatternDetection(_Frozen):
    detector_id: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    regex: str = ""
    static_only: bool = True

    @model_validator(mode="after")
    def _at_least_one_rule(self) -> AntiPatternDetection:
        if not self.detector_id and not self.regex:
            raise ValueError(
                "AntiPatternDetection must set at least one of detector_id / regex"
            )
        return self


class AntiPatternSpec(_Frozen):
    id: str
    name: str
    applicable_to: list[str] = Field(default_factory=list)
    detection: AntiPatternDetection
    why_bad: str = ""
    correct_pattern: str | None = None
    code_example_wrong: str = ""
    code_example_right: str = ""


class CompositionSpec(_Frozen):
    id: str
    description: str
    parent: str
    child: str
    constraints: list[str] = Field(default_factory=list)
    typical_errors: list[str] = Field(default_factory=list)


class PackageManifest(_Frozen):
    schema_version: Literal[1] = 1
    repo: str
    distribution: str
    import_name: str
    display_name: str
    contract_class: ContractClass
    tier: int = 3
    maturity: Literal["alpha", "beta", "stable"] = "alpha"

    r_package: RPackageRef | None = None
    capabilities: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    task_tags: list[str] = Field(default_factory=list)
    foundation: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    not_when: list[str] = Field(default_factory=list)

    symbols: list[SymbolContract] = Field(default_factory=list)
    workflows: list[WorkflowContract] = Field(default_factory=list)
    templates: list[TemplateSpec] = Field(default_factory=list)
    concepts: list[ConceptSpec] = Field(default_factory=list)
    idioms: list[IdiomSpec] = Field(default_factory=list)
    anti_patterns: list[AntiPatternSpec] = Field(default_factory=list)
    compositions: list[CompositionSpec] = Field(default_factory=list)
    complements: list[str] = Field(default_factory=list)

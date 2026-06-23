"""Shared pytest fixtures for schema v1 contract tests."""

from __future__ import annotations

import ast
from typing import Any

import pytest

from biobabel._registry.builder import Registry
from biobabel._registry.discovery import DiscoveredDetector, DiscoveredManifest
from biobabel.detector_api import DetectorMatch
from biobabel.manifest_api import (
    AntiPatternDetection,
    AntiPatternSpec,
    ConceptSpec,
    FailureFix,
    IdiomSpec,
    PackageManifest,
    SymbolContract,
    TemplateSpec,
    WorkflowContract,
    WorkflowStep,
)


def _fake_for_loop_calls(tree: ast.AST, args: dict[str, Any]) -> list[DetectorMatch]:
    targets = set(args.get("calls", []))
    hits: list[DetectorMatch] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    fn = child.func
                    name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                    if name in targets:
                        hits.append(DetectorMatch(line=node.lineno, detail={"target_call": name}))
                        break
    return hits


def _fake_unbalanced(tree: ast.AST, args: dict[str, Any]) -> list[DetectorMatch]:
    push_fn = args.get("push", "")
    pop_fn = args.get("pop", "")
    push_count = pop_count = 0
    first_line = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if name == push_fn:
                push_count += 1
                if not first_line:
                    first_line = node.lineno
            elif name == pop_fn:
                pop_count += 1
    if push_count != pop_count:
        return [DetectorMatch(line=first_line or 1, detail={"push": push_count, "pop": pop_count})]
    return []


@pytest.fixture
def grammar_manifest() -> PackageManifest:
    return PackageManifest(
        repo="https://github.com/Bio-Babel/rgrid-python",
        distribution="rgrid-python",
        import_name="grid_py",
        display_name="grid_py",
        contract_class="grammar",
        tier=1,
        maturity="beta",
        symbols=[
            SymbolContract(
                id="grid_py.grid_points",
                import_path="grid_py.grid_points",
                signature="grid_points(x, y, gp=None)",
                purpose="Draw point markers in the current viewport.",
                requires=["current viewport coordinates are appropriate for Unit inputs"],
                examples=["grid_points(Unit(xs, 'native'), Unit(ys, 'native'))"],
            )
        ],
        concepts=[
            ConceptSpec(
                id="grid_py.Viewport",
                name="Viewport",
                category="drawing-context",
                description="Rectangular region on a graphics device.",
                invariants=["push and pop must balance"],
                mental_model="stack of coordinate transforms",
            ),
        ],
        idioms=[
            IdiomSpec(
                id="grid_py.push_draw_pop",
                name="Push-Draw-Pop",
                applicable_to=["grid_py.Viewport"],
                description="Standard sub-region drawing.",
                code_template="push_viewport(vp); grid_rect(); pop_viewport()",
            ),
        ],
        anti_patterns=[
            AntiPatternSpec(
                id="grid_py.grob_in_loop",
                name="Building grobs in a loop",
                applicable_to=["grid_py.Grob"],
                detection=AntiPatternDetection(
                    detector_id="rgrid.for_loop_calls",
                    args={"calls": ["rect_grob", "text_grob"]},
                ),
                why_bad="N draws instead of 1.",
                correct_pattern="grid_py.build_grobtree",
                code_example_right="grid_draw(grob_tree(*rects))",
            ),
            AntiPatternSpec(
                id="grid_py.unbalanced_push_pop",
                name="Unbalanced push_pop",
                applicable_to=["grid_py.Viewport"],
                detection=AntiPatternDetection(
                    detector_id="rgrid.unbalanced",
                    args={"push": "push_viewport", "pop": "pop_viewport"},
                ),
                why_bad="Stack ends dirty.",
                correct_pattern="grid_py.try_finally_pop",
            ),
        ],
        templates=[
            TemplateSpec(
                id="grid_py.scatter_threshold_skeleton",
                path="templates/scatter_threshold.py",
                description="Skeleton for drawing points and threshold lines with native units.",
                task_tags=["scatter-plot", "threshold-lines"],
            ),
        ],
    )


@pytest.fixture
def analysis_manifest() -> PackageManifest:
    return PackageManifest(
        repo="https://github.com/Bio-Babel/Monocle3-python",
        distribution="monocle3-python",
        import_name="monocle3_py",
        display_name="monocle3",
        contract_class="analysis",
        tier=2,
        maturity="beta",
        symbols=[
            SymbolContract(
                id="monocle3.estimate_size_factors",
                import_path="monocle3.estimate_size_factors",
                signature="estimate_size_factors(adata)",
                purpose="Compute per-cell size factors.",
                mutates="AnnData",
                writes=["adata.obs['Size_Factor']"],
                related=["monocle3.preprocess_cds"],
            ),
            SymbolContract(
                id="monocle3.preprocess_cds",
                import_path="monocle3.preprocess_cds",
                signature="preprocess_cds(adata, num_dim=50, ...)",
                purpose="Normalize counts and compute PCA.",
                mutates="AnnData",
                requires=["adata.X contains raw counts", "adata.obs['Size_Factor'] exists"],
                writes=["adata.obsm['X_pca']"],
                failure_fixes=[
                    FailureFix(
                        when=(
                            "KeyError: 'Size_Factor' — preprocess_cds reads "
                            "adata.obs['Size_Factor'] but size factors were never computed"
                        ),
                        suggest=["monocle3.estimate_size_factors"],
                        explanation=(
                            "Run estimate_size_factors before preprocess_cds so the "
                            "Size_Factor column exists."
                        ),
                    )
                ],
                related=["monocle3.reduce_dimension"],
            ),
            SymbolContract(
                id="monocle3.reduce_dimension",
                import_path="monocle3.reduce_dimension",
                signature="reduce_dimension(adata, reduction_method='UMAP', ...)",
                purpose="Compute low-dimensional embedding.",
                mutates="AnnData",
                requires=["adata.obsm['X_pca'] exists"],
                writes=["adata.obsm['X_umap']"],
            ),
        ],
        workflows=[
            WorkflowContract(
                id="monocle3.basic_trajectory",
                title="Basic pseudotime trajectory",
                description="Reference Monocle3 pseudotime workflow.",
                task_tags=["pseudotime", "trajectory"],
                when_to_use=["User asks for Monocle3 pseudotime on AnnData."],
                steps=[
                    WorkflowStep(
                        symbol="monocle3.estimate_size_factors",
                        purpose="Normalize library size.",
                    ),
                    WorkflowStep(
                        symbol="monocle3.preprocess_cds",
                        purpose="Create PCA state for downstream embedding.",
                    ),
                ],
                templates=["monocle3.basic_script"],
            )
        ],
        templates=[
            TemplateSpec(
                id="monocle3.basic_script",
                path="templates/basic.py",
                description="Adaptable script skeleton for a Monocle3 trajectory.",
                task_tags=["pseudotime"],
            )
        ],
    )


@pytest.fixture
def registry(grammar_manifest, analysis_manifest) -> Registry:
    reg = Registry()
    reg.packages["grid_py"] = DiscoveredManifest(
        import_name="grid_py",
        distribution="rgrid-python",
        distribution_version="4.5.3.post4",
        manifest=grammar_manifest,
    )
    reg.packages["monocle3_py"] = DiscoveredManifest(
        import_name="monocle3_py",
        distribution="monocle3-python",
        distribution_version="0.1.0",
        manifest=analysis_manifest,
    )
    for did, fn in (
        ("rgrid.for_loop_calls", _fake_for_loop_calls),
        ("rgrid.unbalanced", _fake_unbalanced),
    ):
        reg.detectors[did] = DiscoveredDetector(
            detector_id=did,
            distribution="rgrid-python",
            distribution_version="4.5.3.post4",
            fn=fn,
        )
    for d in reg.packages.values():
        m = d.manifest
        for symbol in m.symbols:
            reg._symbol_by_id[symbol.id] = (d.import_name, symbol)
        for workflow in m.workflows:
            reg._workflow_by_id[workflow.id] = (d.import_name, workflow)
        for template in m.templates:
            reg._template_by_id[template.id] = (d.import_name, template)
        for concept in m.concepts:
            reg._concept_by_id[concept.id] = (d.import_name, concept)
        for idiom in m.idioms:
            reg._idiom_by_id[idiom.id] = (d.import_name, idiom)
        for anti_pattern in m.anti_patterns:
            reg._anti_pattern_by_id[anti_pattern.id] = (d.import_name, anti_pattern)
    return reg

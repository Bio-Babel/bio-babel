---
name: use-monocle3
description: monocle3-python — single-cell trajectory & pseudotime (R Monocle3 port)
contract_class: analysis
package_version: 1.4.26.post1
biobabel_version: 0.3.0
generated_from_registry_commit: 58d22557492afe2e9a659b00fba98ac8c914046cde6e504c530dc2bd7e0b4d5f
---

# monocle3-python

Python port of [cole-trapnell-lab/monocle3](https://github.com/cole-trapnell-lab/monocle3) (v1.4.26). Operates on `AnnData` instead of R's `CellDataSet` S4 — every other API choice mirrors R as closely as possible.

## Mental model — the canonical 7-step pipeline

Monocle3 is a **state machine** over an AnnData. Each step writes specific slots and is consumed by the next:

```
1. detect_genes           → var.num_cells_expressed, obs.num_genes_expressed
2. estimate_size_factors  → obs.Size_Factor
3. preprocess_cds         → obsm.X_pca, uns.monocle3.preprocess
4. reduce_dimension       → obsm.X_umap
5. cluster_cells          → obs.monocle3_clusters, obs.monocle3_partitions
6. learn_graph            → uns.monocle3.principal_graph
7. order_cells            → obs.monocle3_pseudotime
```

Skipping a step or running them out of order will fail loudly inside the function — biobabel's `check_prerequisites` catches it before the call.

## Invariants

- **`adata.X` must be raw UMI counts.** `estimate_size_factors` assumes integer-like counts. Pre-normalized X breaks size-factor estimation silently in `preprocess_cds`.
- **`order_cells` needs an explicit root.** R Monocle3's interactive `chooseCells()` Shiny UI is **not** available in Python. Pass `root_cells=[barcode1, ...]` or `root_pr_nodes=[node_id, ...]` explicitly.
- **`learn_graph(use_partition=True)` (default) requires `obs.monocle3_partitions`** — i.e. `cluster_cells` must run first. Set `use_partition=False` to skip the dependency.

## When NOT to reach for Monocle3

- **Unstructured cell populations.** Monocle3 will fit a principal graph onto anything; that doesn't make the trajectory meaningful. Run UMAP first and confirm continuous developmental structure visually.
- **RNA velocity / splicing dynamics.** Use `scvelo` instead.
- **Compositional shifts only.** Monocle3 is for ordering cells along a learned graph, not for testing cell-type proportions.

## Quick reference

```python
import monocle3

monocle3.estimate_size_factors(adata)
monocle3.preprocess_cds(adata, num_dim=50)
monocle3.reduce_dimension(adata)
monocle3.cluster_cells(adata)
monocle3.learn_graph(adata)

# Root the WHOLE origin population (pseudotime is graph distance FROM the root,
# so the root population becomes the pseudotime minimum). One hand-picked cell
# pins a single node and can invert the gradient.
roots = adata.obs_names[adata.obs["cell_type"] == origin_label].tolist()
monocle3.order_cells(adata, root_cells=roots)

# Read results via the accessors (reindex to obs_names to keep cell identity).
pt   = monocle3.pseudotime(adata).reindex(adata.obs_names)
cl   = monocle3.clusters(adata).reindex(adata.obs_names)
part = monocle3.partitions(adata).reindex(adata.obs_names)

monocle3.plot_cells(adata, color_cells_by="pseudotime")
```

For each step's full signature: `biobabel.describe_symbol(symbol_id="monocle3.<name>")`.

For the full pipeline as a `WorkflowContract`: `biobabel.describe_workflow(workflow_id="monocle3.basic_trajectory")`.

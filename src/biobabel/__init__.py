"""biobabel — agent contract server for the Bio-Babel ecosystem.

Stable public Python surfaces for producer packages:

- :mod:`biobabel.manifest_api` — schema v1 contract models.
- :mod:`biobabel.detector_api` — callable types for optional AST detectors.

Everything else is implementation detail.
"""

from biobabel.detector_api import DetectorFn, DetectorMatch
from biobabel.manifest_api import (
    AntiPatternDetection,
    AntiPatternSpec,
    CompositionSpec,
    ConceptSpec,
    FailureFix,
    IdiomSpec,
    PackageManifest,
    Parameter,
    RPackageRef,
    SymbolContract,
    TemplateParameter,
    TemplateSpec,
    WorkflowContract,
    WorkflowInput,
    WorkflowStep,
)

__version__ = "0.3.0"
SCHEMA_VERSION = 1

__all__ = [
    "AntiPatternDetection",
    "AntiPatternSpec",
    "CompositionSpec",
    "ConceptSpec",
    "DetectorFn",
    "DetectorMatch",
    "FailureFix",
    "IdiomSpec",
    "PackageManifest",
    "Parameter",
    "RPackageRef",
    "SCHEMA_VERSION",
    "SymbolContract",
    "TemplateParameter",
    "TemplateSpec",
    "WorkflowContract",
    "WorkflowInput",
    "WorkflowStep",
    "__version__",
]

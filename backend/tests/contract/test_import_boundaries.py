"""No provider SDK imported outside providers/ (SC-010, Constitution II)."""

import ast
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[2] / "app"

# Modules that are inherently provider-specific and MAY appear outside
# providers/ only within providers/ itself.
_PROVIDER_SDK_MODULES = {"edge_tts", "azure", "elevenlabs"}


def _imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_provider_sdk_outside_providers_package():
    violations = []
    for py_file in BACKEND_APP.rglob("*.py"):
        if "providers" in py_file.parts:
            continue
        imports = _imports_in(py_file)
        bad = imports & _PROVIDER_SDK_MODULES
        if bad:
            violations.append((str(py_file), bad))
    assert not violations, f"Provider SDK imported outside providers/: {violations}"


def test_no_domain_module_branches_on_provider_name():
    """Services/text_processing must not contain an equality COMPARISON
    against a provider-name string literal (`x == "edge"`, `x != "azure"`) —
    routing must use capability data, not provider identity.

    AST-based rather than a substring search: a substring check would also
    flag legitimate non-branching uses (an error-message hint, a data field
    value, a CLI default), which are not what Principle II prohibits.
    """
    domain_dirs = ["services", "text_processing"]
    provider_names = {"edge", "azure", "elevenlabs"}
    violations = []

    for dirname in domain_dirs:
        for py_file in (BACKEND_APP / dirname).rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                operands = [node.left, *node.comparators]
                for operand in operands:
                    if (
                        isinstance(operand, ast.Constant)
                        and isinstance(operand.value, str)
                        and operand.value in provider_names
                    ):
                        violations.append((str(py_file), operand.value, node.lineno))

    assert not violations, f"Domain code branches on provider identity: {violations}"

import tomllib
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_pytest_discovery_is_limited_to_the_test_tree():
    config = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]

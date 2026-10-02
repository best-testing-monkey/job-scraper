import tomllib
from pathlib import Path


def test_playwright_importable():
    import playwright.sync_api  # noqa: F401


def test_patchright_importable():
    import patchright.sync_api  # noqa: F401


def test_declared_as_direct_dependencies():
    root = Path(__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        deps = tomllib.load(f)["project"]["dependencies"]
    names = {d.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip() for d in deps}
    assert {"playwright", "patchright"} <= names

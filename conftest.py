import pathlib


def pytest_ignore_collect(collection_path: pathlib.Path):
    if collection_path.parts[-1] == "viewer":
        return True
    if collection_path.parts[-1] == "analysis":
        return True

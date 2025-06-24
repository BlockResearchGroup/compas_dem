def pytest_ignore_collect(path):
    if str(path).endswith("cra.py"):
        return True
    if str(path).endswith("fea.py"):
        return True

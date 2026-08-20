from importlib import import_module


_EXPORTS = {
    "bla_solve": ("compas_dem.analysis.bla", "bla_solve"),
    "cra_solve": ("compas_dem.analysis.cra", "cra_solve"),
    "lmgc90_solve": ("compas_dem.analysis.lmgc90", "lmgc90_solve"),
    "prd_solve": ("compas_dem.analysis.prd", "prd_solve"),
    "rbe_solve": ("compas_dem.analysis.cra", "rbe_solve"),
    "threedec_solve": ("compas_dem.analysis.threedec", "threedec_solve"),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    """Load an optional solver backend only when its public function is used."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name)) from error

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value

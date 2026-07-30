__all__ = []
try:
    try:
        from compas_dem.analysis.cra import cra_solve  # noqa: F401

        __all__.append("cra_solve")
    except ImportError:
        pass

    try:
        from compas_dem.analysis.cra import rbe_solve  # noqa: F401

        __all__.append("rbe_solve")
    except ImportError:
        pass

    try:
        from compas_dem.analysis.lmgc90 import lmgc90_solve  # noqa: F401

        __all__.append("lmgc90_solve")
    except ImportError:
        pass

    try:
        from compas_dem.analysis.prd import prd_solve  # noqa: F401

        __all__.append("prd_solve")
    except ImportError:
        pass

    try:
        from compas_dem.analysis.bla import bla_solve  # noqa: F401

        __all__.append("bla_solve")
    except ImportError:
        pass

except ImportError:
    print("One or more analysis modules could not be imported. Please ensure all dependencies are installed.")

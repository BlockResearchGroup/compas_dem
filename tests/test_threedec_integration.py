import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from compas.datastructures import Mesh
from compas_dem.models import BlockModel
from compas_dem.material.generic import GenericMaterial
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.problem.results import Results
from compas_dem.templates import ArchTemplate

from compas_dem.analysis.threedec import threedec_solve


def test_threedec_solver_configuration_roundtrip():
    solver = Solver.ThreeDEC(
        version="7.0",
        executable="3dec.exe",
        gravity_steps=5,
    )

    restored = Solver.__from_data__(solver.__data__)

    assert restored.name == "3DEC"
    assert restored.parameters["version"] == "7.0"
    assert restored.parameters["executable"] == "3dec.exe"
    assert restored.parameters["gravity_steps"] == 5


def test_threedec_alias():
    assert Solver.threeDEC(version="7.0").name == "3DEC"


def test_problem_solve_dispatches_to_threedec_adapter():
    mesh = Mesh.from_vertices_and_faces(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        [[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]],
    )
    model = BlockModel()
    node = model.add_block_from_mesh(mesh)
    model.add_support(node)

    problem = Problem(model)
    problem.add_boundary_condition("gravity").add_gravity()
    problem.set_contact_model("MohrCoulomb", phi=35.0)
    problem.set_solver(Solver.ThreeDEC(version="7.0"))

    sentinel = object()
    with patch(
        "compas_dem.analysis.threedec.threedec_solve",
        return_value=sentinel,
    ) as solve:
        result = problem.solve()

    assert result is sentinel
    solve.assert_called_once()
    assert solve.call_args.args[:2] == (problem, model)


def test_threedec_adapter_builds_solves_and_converts():
    compas_3dec = pytest.importorskip("compas_3dec")
    model = Mock()
    problem = Mock()
    problem.model = model
    analysis = Mock()
    raw_results = Mock()
    dem_results = Mock()
    with patch.object(compas_3dec, "ThreeDECAnalysisBuilder") as builder_type:
        with patch.object(compas_3dec, "ThreeDECSolver") as solver_type:
            builder_type.from_dem_problem.return_value.build.return_value = analysis
            solver_type.return_value.solve.return_value = raw_results
            raw_results.to_compas_dem_results.return_value = dem_results

            result = threedec_solve(problem, model, version="7.0")

            assert result is dem_results
            builder_type.from_dem_problem.assert_called_once_with(problem)
            solver_type.return_value.solve.assert_called_once_with(analysis)
            raw_results.to_compas_dem_results.assert_called_once_with(analysis)


@pytest.mark.skipif(not os.getenv("COMPAS_3DEC_EXECUTABLE"), reason="Set COMPAS_3DEC_EXECUTABLE to run the real 3DEC smoke test.")
def test_threedec_real_gravity_smoke(tmp_path):
    arch = ArchTemplate(
        rise=0.5,
        span=5.0,
        thickness=0.3,
        depth=0.3,
        n=10,
    )
    model = BlockModel()
    nodes = [model.add_block_from_mesh(mesh) for mesh in arch.blocks()]
    model.add_supports([nodes[0], nodes[-1]])
    material = GenericMaterial(Ecm=25e9, density=2500, poisson=0.2)
    model.add_material(material)
    model.assign_material(material, elements=list(model.elements()))

    problem = Problem(model, name="3DEC gravity smoke test")
    problem.add_boundary_condition("gravity").add_gravity()
    problem.set_contact_model("MohrCoulomb", phi=35.0)
    problem.set_joint_model(kn=1e9, kt=5e8)
    problem.set_solver(
        Solver.ThreeDEC(
            version=os.getenv("COMPAS_3DEC_VERSION", "7.0"),
            executable=os.environ["COMPAS_3DEC_EXECUTABLE"],
            workspace=tmp_path,
            gravity_steps=10,
            suppress_output=True,
            timeout=300,
        )
    )

    # The adapter runs 3DEC and calls
    # raw_results.to_compas_dem_results(analysis) before returning.
    dem_results = problem.solve()

    assert isinstance(dem_results, Results)
    assert dem_results.metadata["solver"] == "3DEC"
    assert dem_results.metadata["converged"] is True
    assert set(dem_results.nodes()) == set(nodes)

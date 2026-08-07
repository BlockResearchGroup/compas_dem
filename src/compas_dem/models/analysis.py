from typing import TYPE_CHECKING
from typing import Optional

from compas.data import Data
from compas_dem.models.blockmodel import BlockModel

if TYPE_CHECKING:
    from compas_dem.problem import Problem


class Analysis(Data):
    """Container for a block model and the problems defined over it.

    Serializing the analysis writes the model exactly once, alongside its problems —
    the problems themselves never embed the model. On deserialization the model is
    loaded back into each problem, so ``problem.solve()`` works immediately without
    re-loading the model by hand.

    Parameters
    ----------
    model : :class:`~compas_dem.models.BlockModel`, optional
        The model to be analyzed. Can also be set later with :meth:`set_model`.
    name : str, optional
        Name of the analysis.

    Examples
    --------
    >>> analysis = Analysis(model)  # doctest: +SKIP
    >>> analysis.add_problem(problem)  # doctest: +SKIP
    >>> compas.json_dump(analysis, "analysis.json")  # doctest: +SKIP
    >>> analysis = compas.json_load("analysis.json")  # doctest: +SKIP
    >>> result = analysis.problems[0].solve()  # doctest: +SKIP
    """

    def __init__(self, model: Optional[BlockModel] = None, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.model: Optional[BlockModel] = model
        self.problems: list["Problem"] = []

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "problems": self.problems,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "Analysis":
        obj = cls(model=data["model"], name=data.get("name"))
        obj.problems = list(data["problems"])
        if obj.model is not None:
            for problem in obj.problems:
                problem.load_model(obj.model)
        return obj

    def set_model(self, model: BlockModel) -> None:
        """Set the model for the analysis, and load it into every problem already added.

        Parameters
        ----------
        model : :class:`~compas_dem.models.BlockModel`
            The model to be analyzed.

        Raises
        ------
        ValueError
            If a previously added problem was defined over a different model.
        """
        self.model = model
        for problem in self.problems:
            problem.load_model(model)

    def add_problem(self, problem: "Problem") -> None:
        """Add a problem to the analysis, loading the analysis model into it.

        Parameters
        ----------
        problem : :class:`~compas_dem.problem.Problem`
            The problem to be analyzed.

        Raises
        ------
        ValueError
            If the problem was defined over a different model than the analysis model.
        """
        self.problems.append(problem)
        if self.model is not None:
            problem.load_model(self.model)

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, eq=False, kw_only=True)
class Context:
    """
    Analysis context of an operation.

    The context consists of the data-taking campaign, the channel, the category,
    the dataset, the process, and the variation.
    """

    campaign: str
    channel: str
    category: str
    dataset: str
    process: str
    variation: str


@dataclass(frozen=True, eq=False, kw_only=True)
class Spec:
    """
    Base class for specifications serving as auxiliary data for a node in a
    computational graph.
    """

    pass


@dataclass(frozen=True, eq=False, kw_only=True)
class Dataset(Spec):
    """
    Specification of a dataset with input `"*.root"` files from a `CROWN`
    ntuple production.

    The dictionary `files` contains the input file lists for each subtree of the
     dataset. The main tree is identified by the key `"main"` and must always be
     present. Optional friend trees are identified by their corresponding name.

    Attributes
    ----------
    campaign : str
        Name of the data-taking campaign.

    channel : str
        Name of the analysis channel.

    dataset : str
        Name of the dataset.

    files: dict[str, list[str]]
        Dictionary containing the input files for each subtree of the dataset.

    Raises
    ------
    ValueError
        If the main tree is not present in the `files` dictionary.
    """

    campaign: str
    channel: str
    dataset: str
    files: dict[str, list[str]]

    def __post_init__(self):
        # Check if the main tree is present in the filemap
        if "main" not in self.files:
            raise ValueError(
                f"Dataset {self.dataset} must contain a main tree with key "
                + "'main'."
            )

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"dataset={self.dataset}",
                f"files=<{', '.join(f for f in self.files)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"


@dataclass(frozen=True, eq=False, kw_only=True)
class Filter(Spec):
    """
    Specification of a filter operation on an `RDataFrame` object.

    The filter is defined by the `expression`. This is a `ROOT` expression which
    yields a boolean value. The `name` is used to identify the filter in the
    `RDataFrame` computation graph.

    Attributes
    ----------
    name : str
        The name of the filter operation.

    expression : str
        The expression defining the filter condition.
    """

    name: str
    expression: str

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"name={self.name}",
                f"expression={self.expression}",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"


@dataclass(frozen=True, eq=False, kw_only=True)
class Weight(Spec):
    """
    Specification of a weight operation on an `RDataFrame` object.

    The weight is defined by the `expression`. This is a `ROOT` expression which
    yields a numerical value. The value will be stored in a new column. Together
    with a fixed prefix, `name` is used to define the name of the new column in
    the `RDataFrame` object.

    Attributes
    ----------
    name : str
        The name of the weight.

    expression : str
        The expression defining the weight.
    """

    name: str
    expression: str

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"name={self.name}",
                f"expression={self.expression}",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"


@dataclass(frozen=True, eq=False, kw_only=True)
class WeightProduct(Spec):
    """
    Specification for building the total weight by multiplying a list of
    individual weights.

    Attributes
    ----------
    name : str
        The name of the total weight.

    weights : list[Weight]
        The list of individual weights to be multiplied together.
    """

    name: str
    weights: list[Weight]

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"name={self.name}",
                f"weights=<{', '.join(w.name for w in self.weights)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"


@dataclass(frozen=True, eq=False, kw_only=True)
class FiltersAndWeights(Spec):
    campaign: str
    channel: str
    category: str
    process: str
    dataset: str
    variation: str
    filters: list[Filter]
    weights: list[Weight]

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"category={self.category}",
                f"process={self.process}",
                f"dataset={self.dataset}",
                f"variation={self.variation}",
                f"filters=<{', '.join(f.name for f in self.filters)}>",
                f"weights=<{', '.join(w.name for w in self.weights)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"

            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"

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
    campaign: str
    channel: str
    dataset: str
    nicks: list[str]
    files: dict[str, list[str]]

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"dataset={self.dataset}",
                f"nicks=[{', '.join(n for n in self.nicks)}]",
                f"files=<{', '.join(f for f in self.files)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"


@dataclass
class Histogram:
    campaign: str
    channel: str
    category: str
    variable: str
    expression: str
    bin_edges: list[int | float]

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"category={self.category}",
                f"variable={self.variable}",
                f"expression={self.expression}",
                f"bin_edges={self.bin_edges}",
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
    filters: OrderedDict[str, str]
    weights: OrderedDict[str, str]

    def __repr__(self) -> str:
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"category={self.category}",
                f"process={self.process}",
                f"dataset={self.dataset}",
                f"variation={self.variation}",
                f"filters=<{', '.join(f for f in self.filters)}>",
                f"weights=<{', '.join(w for w in self.weights)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"

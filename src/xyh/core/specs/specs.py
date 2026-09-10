from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class Dataset:
    campaign: str
    channel: str
    dataset: str
    nicks: list[str]
    files: list[str]
    friend_files: dict[str, list[str]]

    def __repr__(self):
        attributes = ", ".join(
            [
                f"campaign={self.campaign}",
                f"channel={self.channel}",
                f"dataset={self.dataset}",
                f"nicks=[{', '.join(n for n in self.nicks)}]",
                f"files=<{len(self.files)} files>",
                f"friend_files=<{', '.join(f for f in self.friend_files)}>",
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


@dataclass
class FiltersAndWeights:
    campaign: str
    channel: str
    category: str
    process: str
    dataset: str
    filters: OrderedDict[str, str]
    weights: OrderedDict[str, str]

    def __repr__(self):
        attributes = ", ".join(
            [
                f"filters=<{', '.join(f for f in self.filters)}>",
                f"weights=<{', '.join(w for w in self.weights)}>",
            ]
        )
        return f"{self.__class__.__name__}<{attributes}>"

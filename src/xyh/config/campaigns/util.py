import json
from dataclasses import dataclass, field, fields
from functools import cache, singledispatch
from math import isclose
from pathlib import Path
from typing import Any
import string
import inspect

from order import Campaign, Dataset

from xyh.settings import Settings


@dataclass
class Sample:
    """
    Dataclass representing a sample in the sample database.
    """

    nick: str
    era: str
    nevents: int
    nfiles: int
    sample_type: str
    dbs: str | None = field(default=None)
    filelist: list[str] | None = field(default=None)
    instance: str | None = field(default=None)
    xsec: float | None = field(default=None)
    generator_weight: float | None = field(default=None)


@cache
def load_database(
    sample_database_dir: Path,
    nano_version: str,
) -> dict[str, Sample]:
    """
    Load the sample database from a JSON file.

    The sample database is cached to avoid reloading the same file multiple
    times during the same execution.

    Parameters
    ----------
    sample_database_dir : Path
        Directory containing the sample database JSON file.

    nano_version : str
        Version of the NanoAOD samples to load.

    Returns
    -------
    dict[str, Sample]
        Dictionary mapping sample nicks to Sample instances.
    """
    # Construct the path to the sample database JSON file
    sample_database_file = (
        sample_database_dir / f"nanoAOD_{nano_version}" / "datasets.json"
    )

    # Load the JSON data from the file
    with sample_database_file.open("r") as f:
        samples = {nick: Sample(**data) for nick, data in json.load(f).items()}

    return samples


def get_format_string_parameters(format_string: str) -> set[str]:
    """
    Get parameter of a format string.

    The function extracts the names of parameters in curly braces inside a
    string. The parameter names are returned as a set of strings.

    Parameters
    ----------

    format_string : str
        The format string to extract parameters from.

    Returns
    -------
    set[str]
        A set of parameter names found in the format string.
    """

    return set(
        (
            field_name
            for _, field_name, _, _ in string.Formatter().parse(format_string)
            if field_name is not None
        )
    )


def add_dataset(
    campaign_inst: Campaign,
    name: str,
    nicks: list[str] | str,
) -> Dataset:
    """
    Add a dataset to a campaign instance.

    For unique `name` strings, a `Dataset` is created directly with information
    from the sample database.

    If `name` can be interpreted as a format string with named parameters, a
    `ProxyDataset` is created instead of a `Dataset` for lazy evaluation with
    parameters of the analysis.

    Parameters
    ----------
    campaign_inst : Campaign
        The campaign instance to which the dataset will be added.

    name : str
        The short name of the dataset to be added.

    nicks : list[str] | str
        The nicks of the dataset to be added. Can be provided as single string
        or as a list of strings if the dataset is composed of multiple nicks.

    Returns
    -------
    Dataset
        The created `Dataset` object.
    """

    # First check if the name has a dependency on the parameters of the
    # analysis, e.g., for a signal sample.
    if len(get_format_string_parameters(name)) > 0:
        dataset_inst = campaign_inst.add_dataset(
            DatasetProxy(
                name=name,
                id=campaign_inst.datasets.cls._max_id + 1,
                aux={"nicks": nicks},
            )
        )
        campaign_inst.datasets.cls._max_id += 1
        return dataset_inst

    # If 'nicks' is a string, convert it to a list of strings
    if isinstance(nicks, str):
        nicks = [nicks]

    # Get the sample database directory and the nanoAOD version
    sample_database_dir = Path(Settings().get("sample_database_dir"))
    nano_version = campaign_inst.x.nano_version

    # Merge cross section and generator weight information from all nicks in the
    # list
    sample_info = {}
    for nick in nicks:
        # Load the sample database information
        sample = load_database(sample_database_dir, nano_version).get(nick)

        # Add the sample information to the sample_info dictionary
        for f in fields(Sample):
            # Ignore fields which are not expected to be equal across all nicks
            # in the list and do not need to be merged
            if f in ["nick", "dbs", "filelist", "instance"]:
                continue

            # Add value of this sample to merging list in sample_info
            sample_info.setdefault(f.name, []).append(getattr(sample, f.name))

    # Check if all generator weights and cross sections are equal within a
    # relative tolerance of 1e-3
    for f in ["generator_weight", "xsec"]:
        if any(value is None for value in sample_info[f]) and not all(
            value is None for value in sample_info[f]
        ):
            raise TypeError(f"Types of '{f}' not equal for nicks: {nicks}")

        if all(value is None for value in sample_info[f]):
            # Check if all values are 'None'
            sample_info[f] = None

        elif all(
            isclose(sample_info[f][0], value, rel_tol=1e-3)
            for value in sample_info[f]
        ):
            # Check if all values are numerically close (relative tolerance of
            # 1e-3)
            sample_info[f] = sample_info[f][0]

        else:
            # Other formats are not supported, raise an error
            raise ValueError(f"Values of '{f}' not equal for nicks: {nicks}")

    # Check if eras and sample types are the same for all nicks in the list
    for f in ["era", "sample_type"]:
        if not all(sample_info[f][0] == value for value in sample_info[f]):
            raise ValueError(f"Values of '{f}' not equal for nicks: {nicks}")

        # Reduce list of values to a single value (the first one) since they are
        # all equal
        sample_info[f] = sample_info[f][0]

    # Reduce 'nevents' and 'nfiles' to the sum of all values in the list
    for f in ["nevents", "nfiles"]:
        sample_info[f] = sum(sample_info[f])

    # Create the new dataset
    dataset_inst = campaign_inst.add_dataset(
        name=name,
        id="+",
        is_data=(sample_info["sample_type"] == "data"),
        n_events=sample_info["nevents"],
        n_files=sample_info["nfiles"],
        aux={
            "nicks": nicks,
            "xsec": sample_info["xsec"],
            "generator_weight": sample_info["generator_weight"],
        },
    )

    return dataset_inst


class DatasetProxy(Dataset):
    """
    Proxy class for a dataset that allows for lazy creation of the dataset
    instance.
    """

    def __init__(
        self,
        name,
        id,
        campaign=None,
        info=None,
        processes=None,
        label=None,
        label_short=None,
        is_data=False,
        tags=None,
        aux=None,
        **kwargs,
    ):
        # Initialize base class
        super().__init__(
            name=name,
            id=id,
            campaign=campaign,
            info=info,
            processes=processes,
            label=label,
            label_short=label_short,
            is_data=is_data,
            tags=tags,
            aux=aux,
            **kwargs,
        )

        # Extract parameters from the name
        self._parameters = get_format_string_parameters(name)

        # Inspect the nicks in the aux dictionary and check whether
        # they contain the same parameter names as the dataset name.
        nicks = self.aux.get("nicks", [])
        if not isinstance(nicks, list):
            nicks = [nicks]
        for nick in nicks:
            nick_parameters = set()
            if callable(nick):
                nick_parameters = set(inspect.signature(nick).parameters.keys())
            elif isinstance(nick, str):
                nick_parameters = get_format_string_parameters(nick)
            else:
                raise TypeError(
                    f"Unsupported type for nick: {type(nick)}. "
                    "Expected str or callable."
                )

            if not nick_parameters.issubset(self._parameters):
                raise ValueError(
                    f"Nick '{nick}' contains parameters {nick_parameters} "
                    f"which are not present in the dataset name '{name}' "
                    f"with parameters {self._parameters}."
                )

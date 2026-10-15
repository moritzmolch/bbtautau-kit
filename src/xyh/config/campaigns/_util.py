import json
import re
import string
from dataclasses import dataclass, field, fields
from functools import cache
from math import isclose
from pathlib import Path

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

    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(format_string)
        if field_name is not None
    }


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


# Decay modes of the kit-private NMSSM signal samples and the corresponding
# Y/H decay modes used in the names of the signal datasets
KIT_PRIVATE_DECAY_MODES = {
    "2B2Tau": ("y2b", "h2tau"),
    "2Tau2B": ("y2tau", "h2b"),
}


def add_kit_private_signal_datasets(
    campaign_inst: Campaign,
) -> list[Dataset]:
    """
    Add the kit-private NMSSM signal samples to the campaign.

    The kit-private samples are private nanoAOD productions of the NMSSM
    X -> Y H -> b b tau tau signal samples. They are provided in the sample
    database with the `-kit-private` suffix and are discovered here for the
    year of the given campaign. A dataset named `<name>_kitprivate` is created
    for each covered signal point as a complement to the corresponding
    official dataset.

    Parameters
    ----------
    campaign_inst : Campaign
        The campaign instance to which the kit-private signal datasets will be
        added.

    Returns
    -------
    list[Dataset]
        The created `Dataset` instances.
    """

    # Get the sample database directory and the nanoAOD version
    sample_database_dir = Path(Settings().get("sample_database_dir"))
    nano_version = campaign_inst.x.nano_version

    # Compile a pattern that matches the nicks of the kit-private NMSSM signal
    # samples for the year of the campaign. Multiple productions of the same
    # sample are marked with a '_1' suffix in the nick.
    nick_pattern = re.compile(
        r"^NMSSM-XtoYHto(?P<decay_mode>2B2Tau|2Tau2B)_"
        r"Par-MX-(?P<m_x>\d+)-MY-(?P<m_y>\d+)_"
        r"TuneCP5_13p6TeV_madgraph-pythia8(?:_1)?_"
        + rf"RunIII{campaign_inst.x.year}Summer24NanoAODv15-150X-kit-private$"
    )

    # Map the dataset names to the nicks of the corresponding kit-private
    # samples. Nicks of multiple productions of the same sample are grouped
    # together.
    dataset_nicks = {}
    for nick in load_database(sample_database_dir, nano_version):
        match = nick_pattern.match(nick)
        if match is None:
            continue

        # Get the Y/H decay modes of the signal point from the nick
        y_decay_mode, h_decay_mode = KIT_PRIVATE_DECAY_MODES[
            match.group("decay_mode")
        ]
        m_x = int(match.group("m_x"))
        m_y = int(match.group("m_y"))

        # Group the nicks of the same signal point
        name = (
            f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph"
            "_kitprivate"
        )
        dataset_nicks.setdefault(name, []).append(nick)

    # Add the kit-private signal datasets to the campaign
    return [
        add_dataset(campaign_inst, name, nicks)
        for name, nicks in sorted(dataset_nicks.items())
    ]

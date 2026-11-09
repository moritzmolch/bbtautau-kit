import logging
from collections.abc import Collection, Generator
from dataclasses import dataclass
from pathlib import Path

import ROOT

from xyh.core.config import ProcessGroup, ProcessSet
from xyh.core.io import load_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TH1Wrapper:
    campaign: str
    channel: str
    category: str
    process: str
    dataset: str
    variable: str
    variation: str
    histogram: ROOT.TH1


def _key_selected(
    hist_key: str, selection: dict[str, Collection[str] | None]
) -> bool:
    """Whether a histogram key passes the (AND-combined) selection."""
    parts = hist_key.split("/")
    if len(parts) != 6 or "__" not in parts[-1]:
        return True  # Malformed, let `load_all` raise
    variable, variation = parts[-1].rsplit("__", 1)
    values = {
        "campaign": parts[0],
        "channel": parts[1],
        "variable": variable,
        "variation": variation,
    }
    return all(
        allowed is None or values[name] in allowed
        for name, allowed in selection.items()
    )


def load_all(
    histograms_dir: Path,
    campaigns: Collection[str] | None = None,
    channels: Collection[str] | None = None,
    variables: Collection[str] | None = None,
    variations: Collection[str] | None = None,
) -> list[TH1Wrapper]:
    """
    Load all histograms from graph output files of a production campaign.

    The function returns `TH1Wrapper` objects which contain the `TH1` histogram
    as well as associated metadata: campaign, channel, category, process,
    dataset, variable, and variation.

    Parameters
    ----------
    histograms_dir : Path
        Path to the directory containing the output files of the production
        campaign.

    campaigns, channels, variables, variations : Collection[str] | None, optional
        If given, only histograms with one of these values are read, and files
        without any of them are not opened. Loading everything can take very
        long for large productions. Keys that do not have the expected form
        are never filtered out, so that they still raise.

    Returns
    -------
    list[TH1Wrapper]
        A list of `TH1Wrapper` objects.
    """

    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Load the histogram keys and corresponding files from the JSON file
    histogram_keys_file = histograms_dir / "histogram_keys.json.gz"
    histogram_keys = load_json(histogram_keys_file)

    selection = {
        "campaign": campaigns,
        "channel": channels,
        "variable": variables,
        "variation": variations,
    }

    histograms = []

    for output_file, hist_keys in histogram_keys.items():
        # Construct the full path of the output file
        output_file_path = histograms_dir / output_file

        # Select the keys to read before touching the file
        hist_keys = [k for k in hist_keys if _key_selected(k, selection)]
        if not hist_keys:
            continue

        # Open the ROOT file and load all histograms
        rf = ROOT.TFile.Open(str(output_file_path), "READ")
        for hist_key in hist_keys:
            # Get the analysis context from the histogram key, which has the
            # form 'campaign/channel/category/process/dataset/variable__variation'
            key_parts = hist_key.split("/")
            if len(key_parts) != 6 or "__" not in key_parts[-1]:
                raise ValueError(
                    f"Histogram key {hist_key} in {output_file_path} does not "
                    + "match the pattern 'campaign/channel/category/process/"
                    + "dataset/variable__variation'"
                )
            campaign, channel, category, process, dataset, name = key_parts
            variable, variation = name.rsplit("__", 1)

            # Get the histogram
            hist = rf.Get(hist_key)
            if not hist:
                raise ValueError(
                    f"Histogram {hist_key} not found in {output_file_path}"
                )
            histograms.append(
                TH1Wrapper(
                    campaign=campaign,
                    channel=channel,
                    category=category,
                    process=process,
                    dataset=dataset,
                    variable=variable,
                    variation=variation,
                    histogram=hist,
                )
            )

        rf.Close()

    return histograms


def filter_histograms(
    histograms: list[TH1Wrapper],
    campaign: str | None = None,
    channel: str | None = None,
    category: str | None = None,
    process: str | None = None,
    dataset: str | None = None,
    variable: str | None = None,
    variation: str | None = None,
) -> Generator[TH1Wrapper, None, None]:
    """
    Filter a list of `TH1Wrapper` objects based on the provided criteria.

    Parameters
    ----------
    histograms : list[TH1Wrapper]
        The list of `TH1Wrapper` objects to filter.

    campaign : str | None, optional
        The campaign to filter by. If `None`, do not filter by campaign.

    channel : str | None, optional
        The channel to filter by. If `None`, do not filter by channel.

    category : str | None, optional
        The category to filter by. If `None`, do not filter by category.

    process : str | None, optional
        The process to filter by. If `None`, do not filter by process.

    dataset : str | None, optional
        The dataset to filter by. If `None`, do not filter by dataset.

    variable : str | None, optional
        The variable to filter by. If `None`, do not filter by variable.

    variation : str | None, optional
        The variation to filter by. If `None`, do not filter by variation.

    Yields
    ------
    TH1Wrapper
        The filtered `TH1Wrapper` objects.
    """
    # Compile list of criteria for filtering (interpreted as AND)
    criteria = {
        "campaign": campaign,
        "channel": channel,
        "category": category,
        "process": process,
        "dataset": dataset,
        "variable": variable,
        "variation": variation,
    }
    criteria = {k: v for k, v in criteria.items() if v is not None}

    for hist in histograms:
        if all(getattr(hist, k) == v for k, v in criteria.items()):
            yield hist


def get_histogram(
    histograms: list[TH1Wrapper],
    campaign: str,
    channel: str,
    category: str,
    process: str,
    dataset: str,
    variable: str,
    variation: str,
) -> TH1Wrapper:
    """
    Get a `TH1Wrapper` object based on the provided criteria.

    Parameters
    ----------
    histograms : list[TH1Wrapper]
        The list of `TH1Wrapper` objects to filter.

    campaign : str
        The campaign to filter by.

    channel : str | None, optional
        The channel to filter by.

    category : str | None, optional
        The category to filter by.

    process : str | None, optional
        The process to filter by.

    dataset : str | None, optional
        The dataset to filter by.

    variable : str | None, optional
        The variable to filter by.

    variation : str | None, optional
        The variation to filter by.

    Returns
    ------
    TH1Wrapper
        The filtered `TH1Wrapper` object.

    Raises
    ------
    ValueError
        If no matching histogram is found.
    """

    # Compile list of criteria for filtering (interpreted as AND)
    criteria = {
        "campaign": campaign,
        "channel": channel,
        "category": category,
        "process": process,
        "dataset": dataset,
        "variable": variable,
        "variation": variation,
    }

    # Get the histogram that matches the criteria
    for hist in histograms:
        if all(getattr(hist, k) == v for k, v in criteria.items()):
            return hist

    raise ValueError("No matching histogram found for the given criteria")


def get_histograms_for_process_set(
    histograms: list[TH1Wrapper],
    process_set: ProcessSet,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    variation: str,
) -> dict[str, dict[str, dict[str, list[TH1Wrapper]]]]:
    """
    Load histograms for a given `ProcessSet` from graph output files.

    The dictionary has the following structure:

    ```python
    {
        "data": {
            "<process_group_name>": {
                "<process_inst>": [<TH1Wrapper>, ...],
            },
            ...,
        },
        "signals": { ... },
        "backgrounds": { ... },
    }
    ```

    Parameters
    ----------
    histograms : list[TH1Wrapper]
        A list of `TH1Wrapper` objects to filter.

    process_set : ProcessSet
        The `ProcessSet` object containing the process groups to load histograms
        for.

    campaign : str
        The campaign to filter by.

    channel : str
        The channel to filter by.

    category : str
        The category to filter by.

    variable : str
        The variable to filter by.

    variation : str
        The variation to filter by.

    Returns
    -------
    dict[str, dict[str, dict[str, list[TH1Wrapper]]]]
        A dictionary containing the histograms for each process in the
        `ProcessSet`, organized by process group and process name.
    """

    # Filter histograms for the given campaign, channel, category, and variable
    filtered_histograms = list(
        filter_histograms(
            histograms,
            campaign=campaign,
            channel=channel,
            category=category,
            variable=variable,
            variation=variation,
        )
    )

    # Create a dictionary to hold the histograms for each process in the
    # `ProcessSet`
    def _get_histograms_for_processes(process_groups: list[ProcessGroup]):
        return {
            process_group.name: {
                p: list(
                    filter_histograms(
                        filtered_histograms,
                        process=p,
                    )
                )
            }
            for process_group in process_groups
            for p in process_group.processes
        }

    # Form dictionary of process set histograms
    process_set_histograms = {
        "data": _get_histograms_for_processes(process_set.data),
        "signals": _get_histograms_for_processes(process_set.signals),
        "backgrounds": _get_histograms_for_processes(process_set.backgrounds),
    }

    return process_set_histograms


def add_histograms(histograms: list[ROOT.TH1]) -> ROOT.TH1:
    # Raise exception if no histograms are provided
    if len(histograms) == 0:
        raise ValueError("No histograms to add")

    # Iterate over the histograms, take the first one as the base to clone
    hist_iter = iter(histograms)
    hist_added = next(hist_iter).Clone()
    for hist in hist_iter:
        hist_added.Add(hist)

    return hist_added


def add_th1_wrappers(th1_wrappers: list[TH1Wrapper]) -> ROOT.TH1:
    # Raise exception if no histograms are provided
    if len(th1_wrappers) == 0:
        raise ValueError("No histograms to add")

    return [
        add_histograms([th1_wrapper.histogram for th1_wrapper in th1_wrappers])
    ]


def index_histograms(
    histograms: list[TH1Wrapper],
) -> dict[tuple[str, str, str, str, str], list[TH1Wrapper]]:
    """
    Group histograms by (campaign, channel, category, variable, variation).

    Looking up a group in the dictionary replaces a `filter_histograms` scan
    over all histograms, which is quadratic when done for every category.
    """
    index: dict[tuple[str, str, str, str, str], list[TH1Wrapper]] = {}
    for h in histograms:
        key = (h.campaign, h.channel, h.category, h.variable, h.variation)
        index.setdefault(key, []).append(h)
    return index

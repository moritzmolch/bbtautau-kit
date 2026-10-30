import logging
from time import time

from xyh.core.graph.node import Node

# Set up logging
logger = logging.getLogger(__name__)


class Artifacts(dict):
    """
    Artifacts object to store objects that persist in memory for the lifetime of
    the computation graph.
    """

    def __getattr__(self, key):
        return self[key]


class OutputFiles(dict):
    """
    Persistent output files object to store output files that are generated
    during the graph computation.
    """

    def __getattr__(self, key):
        return self[key]


def input_files(node: Node) -> tuple[Artifacts, OutputFiles]:
    """
    Load input files into an `RDataFrame`.

    This class stores the loaded object and associated `ROOT.TChain` objects
    as artifacts. The `ROOT.TChain` objects need to persist in memory as long as
    the `RDataFrame` exists.

    Parameters
    ----------
    node : Node
        The `"input_files"` operation node that is being processed.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
    """

    # Log current node's context and start time profiling
    logger.debug(
        "\n".join(
            [
                "Initialize data frame from input files for",
                f"    campaign: {node.data.campaign}",
                f"    channel:  {node.data.channel}",
                f"    dataset:  {node.data.dataset}",
            ]
        )
    )
    start = time()

    # Create the chains of the input files
    chains = {}
    for key, files in node.data.files.items():
        chain = ROOT.TChain("ntuple")
        for file in files:
            chain.Add(file)
        chains[key] = chain

    # Add friends to main chain
    main_chain = chains.pop("main")
    for chain in chains.values():
        if chain.GetListOfFiles().GetEntries() > 0:
            main_chain.AddFriend(chain)

    # Create the RDataFrame
    data_frame = ROOT.RDataFrame(main_chain)

    # Stop time profiling and log time that has been used loading the
    # RDataFrame
    stop = time()
    delta = round(stop - start, 2)
    logger.debug(
        "\n".join(
            [
                f"Initialized data frame in {delta} s",
            ]
        )
    )

    return Artifacts(
        data_frame=data_frame,
        main_chain=main_chain,
        friend_chains=chains,
    ), OutputFiles()

import itertools
import logging

from XRootD.client import FileSystem

from xyh.core.analysis_config import load_analysis_inst
from xyh.core.specs.specs import Dataset

# Get the logger for this module
logger = logging.getLogger(__name__)


def create_dataset_spec(
    config_inst,
    channel_inst,
    dataset_inst,
    xrootd_server,
    ntuple_base_dir,
    ntuple_tag,
    ntuple_friends,
) -> Dataset:
    logging.info(f"Create dataset spec {dataset_inst.name}")

    # Create the XRootD file system
    fs = FileSystem(xrootd_server)

    # Map tree types ('main' for main ntuple, friend key for friends) to the
    # corresponding lists of files. The file lists should be sorted
    # alphabetically to ensure that the correct files are linked together when
    # attaching friends to the main tree.
    main_files = []
    friend_files = {}

    # Iterate through all nicks of the dataset and concatenate file lists
    for nick in dataset_inst.x.nicks:
        logging.info(f"Query files for nick {nick}")

        # Query main files
        main_files_channel_dir = (
            ntuple_base_dir
            / ntuple_tag
            / "CROWNRun"
            / config_inst.campaign.name
            / nick
            / channel_inst.name
        )
        _, listing = fs.dirlist(str(main_files_channel_dir), timeout=30)
        _files = []
        for item in listing or []:
            if item.name.endswith(".root"):
                _files.append(
                    xrootd_server.rstrip("/")
                    + "//"
                    + str(main_files_channel_dir / item.name).lstrip("/")
                )

        # Extend main file list with files from this nick
        main_files.extend(_files)

        # Query friend files
        for friend in ntuple_friends:
            friend_files_channel_dir = (
                ntuple_base_dir
                / ntuple_tag
                / "CROWNFriends"
                / friend
                / config_inst.campaign.name
                / nick
                / channel_inst.name
            )
            _, listing = fs.dirlist(
                str(friend_files_channel_dir),
                timeout=30,
            )
            _files = []
            for item in listing or []:
                if item.name.endswith(".root"):
                    _files.append(
                        xrootd_server.rstrip("/")
                        + "//"
                        + str(friend_files_channel_dir / item.name).lstrip("/")
                    )
            _files.sort()

            # Add friend to list of friends
            friend_files.setdefault(friend, []).extend(_files)

    # Create the dataset specs
    dataset_spec = Dataset(
        campaign=config_inst.campaign.name,
        channel=channel_inst.name,
        dataset=dataset_inst.name,
        nicks=dataset_inst.x.nicks,
        files=main_files,
        friend_files=friend_files,
    )
    logger.debug(f"Created ntuple spec {dataset_spec}")

    return dataset_spec


def create_dataset_specs(
    analysis: str,
    campaigns: list[str],
    channels: list[str],
    xrootd_server,
    ntuple_base_dir,
    ntuple_tag,
    ntuple_friends,
) -> list[Dataset]:
    # Load the analysis instance
    analysis_inst = load_analysis_inst(analysis)

    # List of dataset specs
    dataset_specs = []

    for campaign, channel in itertools.product(campaigns, channels):
        logger.info(
            "\n".join(
                [
                    "Creating dataset specs",
                    f"    campaign:         {campaign}",
                    f"    channel:          {channel}",
                    f"    XRootD server:    {xrootd_server}",
                    f"    ntuple base dir:  {ntuple_base_dir}",
                    f"    ntuple tag:       {ntuple_tag}",
                    f"    ntuple friends:   {ntuple_friends}",
                ],
            ),
        )

        # Get the configuration and channel instances
        config_inst = analysis_inst.get_config(campaign)
        channel_inst = config_inst.get_channel(channel)

        # Get the process-datasets map for this channel
        process_datasets_map = config_inst.x.get_process_datasets_map(
            channel_inst
        )

        # Create a dataset specification for each dataset
        for dataset in itertools.chain.from_iterable(
            process_datasets_map.values()
        ):
            dataset_specs.append(
                create_dataset_spec(
                    config_inst,
                    channel_inst,
                    config_inst.get_dataset(dataset),
                    xrootd_server,
                    ntuple_base_dir,
                    ntuple_tag,
                    ntuple_friends,
                )
            )

    return dataset_specs

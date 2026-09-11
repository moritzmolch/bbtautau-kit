import itertools
import logging

from XRootD.client import FileSystem

from xyh.core.config import load_inventory
from xyh.core.specs.specs import Dataset

# Get the logger for this module
logger = logging.getLogger(__name__)


def create_dataset_spec(
    campaign_inst,
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
            / campaign_inst.name
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
                / campaign_inst.name
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
        campaign=campaign_inst.name,
        channel=channel_inst.name,
        dataset=dataset_inst.name,
        nicks=dataset_inst.x.nicks,
        files=main_files,
        friend_files=friend_files,
    )
    logger.debug(f"Created ntuple spec {dataset_spec}")

    return dataset_spec


def create_dataset_specs(
    inventory_factory_fn_path: str,
    campaigns: list[str],
    channels: list[str],
    xrootd_server,
    ntuple_base_dir,
    ntuple_tag,
    ntuple_friends,
) -> list[Dataset]:
    # List of dataset specs
    dataset_specs = []

    for campaign, channel in itertools.product(campaigns, channels):
        # Load the analysis instance
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
        )

        # Get the campaign and channel instances, and load the process-datasets
        # map
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel
        process_datasets_map = inventory.process_datasets_map
        logger.info(
            "\n".join(
                [
                    "Creating dataset specs",
                    f"    campaign:         {campaign_inst.name}",
                    f"    channel:          {channel_inst.name}",
                    f"    XRootD server:    {xrootd_server}",
                    f"    ntuple base dir:  {ntuple_base_dir}",
                    f"    ntuple tag:       {ntuple_tag}",
                    f"    ntuple friends:   {ntuple_friends}",
                ],
            ),
        )

        # Create a dataset specification for each dataset
        for dataset in itertools.chain.from_iterable(
            process_datasets_map.values()
        ):
            dataset_inst = campaign_inst.get_dataset(dataset)
            dataset_specs.append(
                create_dataset_spec(
                    campaign_inst,
                    channel_inst,
                    dataset_inst,
                    xrootd_server,
                    ntuple_base_dir,
                    ntuple_tag,
                    ntuple_friends,
                )
            )

    return dataset_specs

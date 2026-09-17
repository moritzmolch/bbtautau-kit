import itertools
import logging
from typing import Any

from XRootD.client import FileSystem

from xyh.core.config import load_inventory
from xyh.core.config.util import gen_dataset_insts
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
    logger.debug(f"Create dataset spec {dataset_inst.name}")

    # Get the campaign's short handle
    campaign_short = f"{campaign_inst.x.year}{campaign_inst.x.postfix or ''}"

    # Create the XRootD file system
    fs = FileSystem(xrootd_server)

    # Map tree types ('main' for main ntuple, friend key for friends) to the
    # corresponding lists of files. The file lists should be sorted
    # alphabetically to ensure that the correct files are linked together when
    # attaching friends to the main tree.
    files: dict[str, list[str]] = {}

    # Iterate through all nicks of the dataset and concatenate file lists
    for nick in dataset_inst.x.nicks:
        logger.debug(f"Query files for nick {nick}")

        # Query main files
        main_files_channel_dir = (
            ntuple_base_dir
            / ntuple_tag
            / "CROWNRun"
            / campaign_short
            / nick
            / channel_inst.name
        )
        logger.debug(f"Query main files in directory {main_files_channel_dir}")
        status, listing = fs.dirlist(str(main_files_channel_dir), timeout=30)
        if not status.ok:
            logger.warning(
                f"Failed to query main files for nick {nick} in dataset "
                f"{dataset_inst.name} of channel {channel_inst.name} and "
                f"campaign {campaign_inst.name}: {status}"
            )
            continue

        # Iterate through the listing
        _files = []
        for item in listing or []:
            if item.name.endswith(".root"):
                _files.append(
                    xrootd_server.rstrip("/")
                    + "//"
                    + str(main_files_channel_dir / item.name).lstrip("/")
                )

        # Extend main file list with files from this nick
        files.setdefault("main", []).extend(_files)

        # Query friend files
        for friend in ntuple_friends:
            friend_files_channel_dir = (
                ntuple_base_dir
                / ntuple_tag
                / "CROWNFriends"
                / friend
                / campaign_short
                / nick
                / channel_inst.name
            )
            status, listing = fs.dirlist(
                str(friend_files_channel_dir),
                timeout=30,
            )
            if not status.ok:
                logger.warning(
                    f"Failed to query friend files for nick {nick}, friend tag {friend} in dataset "
                    f"{dataset_inst.name} of channel {channel_inst.name} and "
                    f"campaign {campaign_inst.name}: {status}"
                )
                continue

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
            files.setdefault(friend, []).extend(_files)

    # Create the dataset specs
    dataset_spec = Dataset(
        campaign=campaign_inst.name,
        channel=channel_inst.name,
        dataset=dataset_inst.name,
        nicks=dataset_inst.x.nicks,
        files=files,
    )
    logger.debug(f"Created ntuple spec {dataset_spec}")

    return dataset_spec


def create_dataset_specs(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict[str, Any],
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
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
            **inventory_factory_kwargs,
        )

        # Get the campaign and channel instances, and load the process-datasets
        # map
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel

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
        for dataset_inst in gen_dataset_insts(inventory):
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

        logger.info(
            f"Created {len(dataset_specs)} dataset specs for campaign "
            f"{campaign_inst.name} and channel {channel_inst.name}"
        )

    return dataset_specs

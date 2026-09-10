import gzip
import json
import logging
from pathlib import Path
from typing import Any


def dump_json(data: Any, output_file: Path):
    """
    Dump `data` into a JSON file.

    If the file ends with `.gz`, the file will be compressed using gzip.

    Parameters
    ----------
    data : Any
        The data to be dumped into the JSON file.

    output_file : Path
        The path to the output JSON file.
    """

    # Create parent directory if it does not exist
    if not output_file.parent.exists():
        logging.info(
            f"Created the output file's parent directory {output_file}"
        )
        output_file.parent.mkdir(parents=True)

    if output_file.name.endswith(".json.gz"):
        # If the file ends with 'gz', open the file with gzip library
        with gzip.open(output_file, "w") as f:
            f.write(json.dumps(data).encode("utf-8"))

    else:
        # Use default json.dump behavior otherwise
        with output_file.open("w") as f:
            json.dump(data, f)

    logging.info(f"Dumped dataset specs to {output_file}")


def load_json(input_file) -> Any:
    """
    Load data from JSON file.

    If the file ends with `.gz`, the file will be decompressed using gzip before
    decoding he content.

    Parameters
    ----------
    input_file : Path
        The path to the input JSON file.

    Returns
    -------
    Any
        The decoded data loaded from the JSON file.
    """

    # Initialize data object
    data = None

    if input_file.name.endswith(".json.gz"):
        # If the file ends with 'gz', open the file with gzip library
        with gzip.open(input_file, "r") as f:
            data = json.loads(f.read().decode("utf-8"))

    else:
        # Use default json.load behavior otherwise
        with input_file.open("w") as f:
            data = json.load(f)

    logging.info(f"Loaded data from {input_file}")

    return data

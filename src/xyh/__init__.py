import warnings
from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# ROOT warns about the unavailable `RDF.Distributed` backends (e.g. Spark or
# Dask) when it is imported, which is irrelevant for this project. The filter
# is installed here so that it is active before ROOT is imported in the main
# process and in spawned workers, which import `xyh` first.
warnings.filterwarnings(
    "ignore",
    message=r"(?is)(?=.*RDF)(?=.*Distributed)",
)

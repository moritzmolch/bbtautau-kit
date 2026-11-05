class Artifacts(dict):
    """
    Artifacts object to store objects that persist in memory for the lifetime of
    the computation graph.
    """

    def __getattr__(self, key):
        return self[key]


class ArtifactsStore:
    def __init__(self):
        self._store: dict[str, Artifacts] = {}

    def put(self, node_hash: str, artifacts: Artifacts):
        self._store[node_hash] = artifacts

    def get(self, *args: str) -> dict[str, Artifacts]:
        # Check that args are unique and that all node hashes exist in the store
        if len(args) != len(set(args)):
            raise ValueError("Duplicate node hashes provided.")
        if not all(node_hash in self._store for node_hash in args):
            missing_hashes = [
                node_hash for node_hash in args if node_hash not in self._store
            ]
            raise KeyError(
                f"Artifacts for node hashes {missing_hashes} not found."
            )

        # Get the artifacts
        artifacts = {}
        for node_hash in args:
            artifacts[node_hash] = self._store[node_hash]

        return artifacts

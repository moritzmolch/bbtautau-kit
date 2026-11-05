import pytest

from xyh.core.graph.artifacts import Artifacts, ArtifactsStore


class TestArtifacts:
    def test_artifacts_getattr_returns_item(self):
        assert Artifacts(a=1).a == 1

    def test_artifacts_getattr_missing_raises_key_error(self):
        with pytest.raises(KeyError):
            _ = Artifacts().missing


class TestArtifactsStore:
    def test_get_single_hash_returns_dict_with_put_artifacts(self):
        store = ArtifactsStore()
        arts = Artifacts(a=1)
        store.put("h1", arts)
        result = store.get("h1")
        assert result == {"h1": arts}
        assert result["h1"] is arts

    def test_get_several_hashes_returns_all_keyed_by_hash(self):
        store = ArtifactsStore()
        a, b, c = Artifacts(a=1), Artifacts(b=2), Artifacts(c=3)
        store.put("h1", a)
        store.put("h2", b)
        store.put("h3", c)
        result = store.get("h3", "h1")
        assert result == {"h3": c, "h1": a}

    def test_get_no_arguments_returns_empty_dict(self):
        assert ArtifactsStore().get() == {}

    def test_get_duplicate_hashes_raises_value_error(self):
        store = ArtifactsStore()
        store.put("h1", Artifacts())
        with pytest.raises(ValueError, match="Duplicate"):
            store.get("h1", "h1")

    def test_get_missing_hash_raises_key_error_naming_it(self):
        store = ArtifactsStore()
        store.put("h1", Artifacts())
        with pytest.raises(KeyError, match="nope"):
            store.get("h1", "nope")

    def test_get_multiple_missing_hashes_lists_all_missing(self):
        store = ArtifactsStore()
        store.put("h1", Artifacts())
        with pytest.raises(KeyError) as exc:
            store.get("m1", "h1", "m2")
        assert "m1" in str(exc.value)
        assert "m2" in str(exc.value)
        assert "h1" not in str(exc.value)

    def test_put_overwrites_existing_hash(self):
        store = ArtifactsStore()
        new = Artifacts(v=2)
        store.put("h1", Artifacts(v=1))
        store.put("h1", new)
        assert store.get("h1")["h1"] is new

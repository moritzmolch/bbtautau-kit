from dataclasses import asdict

import pytest

from xyh.core.specs.specs import HistogramsOutput


@pytest.fixture
def spec():
    return HistogramsOutput(output_dir="/out", subgraph_hash="abc123")


class TestHistogramsOutput:
    def test_repr_contains_class_name_and_both_fields(self, spec):
        assert repr(spec) == (
            "HistogramsOutput<output_dir=/out, subgraph_hash=abc123>"
        )

    def test_asdict_contains_both_fields(self, spec):
        assert asdict(spec) == {
            "output_dir": "/out",
            "subgraph_hash": "abc123",
        }

    def test_asdict_roundtrips_to_equal_fields(self, spec):
        clone = HistogramsOutput(**asdict(spec))
        assert asdict(clone) == asdict(spec)

    def test_fields_are_keyword_only(self):
        with pytest.raises(TypeError):
            HistogramsOutput("/out", "abc123")

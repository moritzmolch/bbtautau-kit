import pytest

from xyh.core.specs.specs import Dataset, Filter, Histogram, Weight


@pytest.fixture
def make_dataset():
    def _make(dataset="ds", files=None):
        return Dataset(
            campaign="c",
            channel="ch",
            dataset=dataset,
            files={"main": ["a.root"]} if files is None else files,
        )

    return _make


@pytest.fixture
def make_filter():
    def _make(name="f", expression="x > 0"):
        return Filter(name=name, expression=expression)

    return _make


@pytest.fixture
def make_weight():
    def _make(name="w", expression="1.0"):
        return Weight(name=name, expression=expression)

    return _make


@pytest.fixture
def make_histogram():
    def _make(variable="pt", expression=None, bin_edges=(0.0, 1.0, 3.0)):
        return Histogram(
            campaign="c",
            channel="ch",
            category="cat",
            dataset="ds",
            process="p",
            variation="nominal",
            variable=variable,
            expression=expression,
            bin_edges=list(bin_edges),
        )

    return _make

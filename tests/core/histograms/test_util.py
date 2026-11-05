import pytest
import ROOT

from xyh.core.histograms import util
from xyh.core.histograms.util import TH1Wrapper
from xyh.core.io import dump_json


@pytest.fixture(autouse=True)
def detach_histograms():
    # Histograms must not be owned by the current ROOT directory. This is also
    # what `load_all` expects from its caller (as `run_fake_factor_histograms`
    # does), otherwise loaded histograms are deleted when their file is closed.
    previous = ROOT.TH1.AddDirectoryStatus()
    ROOT.TH1.AddDirectory(False)
    yield
    ROOT.TH1.AddDirectory(previous)


def _make_th1(name="h", values=(1.0, 2.0, 3.0)):
    hist = ROOT.TH1D(name, name, len(values), 0.0, float(len(values)))
    hist.SetDirectory(0)
    for i, v in enumerate(values, start=1):
        hist.SetBinContent(i, v)
    return hist


def _contents(hist):
    return [hist.GetBinContent(i) for i in range(1, hist.GetNbinsX() + 1)]


@pytest.fixture
def make_wrapper():
    def _make(
        campaign="c",
        channel="ch",
        category="cat",
        process="p",
        dataset="ds",
        variable="pt",
        variation="nominal",
        values=(1.0, 2.0, 3.0),
    ):
        return TH1Wrapper(
            campaign=campaign,
            channel=channel,
            category=category,
            process=process,
            dataset=dataset,
            variable=variable,
            variation=variation,
            histogram=_make_th1(values=values),
        )

    return _make


@pytest.fixture
def write_root_file():
    """Write TH1D objects into a ROOT file at `path` under the given keys."""

    def _write(path, contents):
        root_file = ROOT.TFile.Open(str(path), "RECREATE")
        for key, values in contents.items():
            dir_name, _, name = key.rpartition("/")
            directory = root_file.GetDirectory(dir_name)
            if not directory:
                directory = root_file.mkdir(dir_name)
            directory.cd()
            hist = _make_th1(name, values)
            hist.Write()
        root_file.Close()

    return _write


class TestTH1Wrapper:
    def test_th1_wrapper_stores_metadata_and_histogram(self, make_wrapper):
        w = make_wrapper(variation="up")
        assert (w.campaign, w.channel, w.category) == ("c", "ch", "cat")
        assert (w.process, w.dataset, w.variable) == ("p", "ds", "pt")
        assert w.variation == "up"
        assert _contents(w.histogram) == [1.0, 2.0, 3.0]

    def test_th1_wrapper_is_frozen(self, make_wrapper):
        w = make_wrapper()
        with pytest.raises(AttributeError):
            w.campaign = "other"  # type: ignore[misc]

    def test_th1_wrapper_requires_keyword_arguments(self):
        with pytest.raises(TypeError):
            TH1Wrapper("c", "ch", "cat", "p", "ds", "pt", "nominal", None)  # type: ignore[misc]


class TestLoadAll:
    @pytest.fixture
    def keys_file(self, tmp_path):
        return tmp_path / "histogram_keys.json.gz"

    def test_load_all_parses_context_from_keys(
        self, tmp_path, keys_file, write_root_file
    ):
        key = "c/ch/cat/proc/ds/pt__up"
        write_root_file(tmp_path / "h.root", {key: (1.0, 2.0)})
        dump_json({"h.root": [key]}, keys_file)
        (w,) = util.load_all(keys_file, tmp_path)
        assert (w.campaign, w.channel, w.category) == ("c", "ch", "cat")
        assert (w.process, w.dataset) == ("proc", "ds")
        assert (w.variable, w.variation) == ("pt", "up")
        assert _contents(w.histogram) == [1.0, 2.0]

    def test_load_all_variable_with_double_underscore_splits_at_last(
        self, tmp_path, keys_file, write_root_file
    ):
        key = "c/ch/cat/p/ds/my__var__nominal"
        write_root_file(tmp_path / "h.root", {key: (1.0,)})
        dump_json({"h.root": [key]}, keys_file)
        (w,) = util.load_all(keys_file, tmp_path)
        assert (w.variable, w.variation) == ("my__var", "nominal")

    def test_load_all_reads_multiple_files_and_keys(
        self, tmp_path, keys_file, write_root_file
    ):
        k1 = "c/ch/cat/p/ds/pt__nominal"
        k2 = "c/ch/cat/p/ds/eta__nominal"
        k3 = "c/ch/cat/q/ds2/pt__nominal"
        write_root_file(tmp_path / "a.root", {k1: (1.0,), k2: (2.0,)})
        write_root_file(tmp_path / "b.root", {k3: (3.0,)})
        dump_json({"a.root": [k1, k2], "b.root": [k3]}, keys_file)
        result = util.load_all(keys_file, tmp_path)
        assert [(w.process, w.variable) for w in result] == [
            ("p", "pt"),
            ("p", "eta"),
            ("q", "pt"),
        ]
        assert [w.histogram.GetBinContent(1) for w in result] == [
            1.0,
            2.0,
            3.0,
        ]

    def test_load_all_empty_keys_file_returns_empty_list(
        self, tmp_path, keys_file
    ):
        dump_json({}, keys_file)
        assert util.load_all(keys_file, tmp_path) == []

    @pytest.mark.parametrize(
        "key",
        [
            "c/ch/cat/p/pt__nominal",
            "c/ch/cat/p/ds/extra/pt__nominal",
            "c/ch/cat/p/ds/ptnominal",
        ],
        ids=["too-few-parts", "too-many-parts", "no-variation-separator"],
    )
    def test_load_all_malformed_key_raises(
        self, tmp_path, keys_file, write_root_file, key
    ):
        write_root_file(tmp_path / "h.root", {"a/b": (1.0,)})
        dump_json({"h.root": [key]}, keys_file)
        with pytest.raises(ValueError, match="does not match the pattern"):
            util.load_all(keys_file, tmp_path)

    def test_load_all_missing_histogram_raises(
        self, tmp_path, keys_file, write_root_file
    ):
        write_root_file(
            tmp_path / "h.root", {"c/ch/cat/p/ds/pt__nominal": (1.0,)}
        )
        dump_json({"h.root": ["c/ch/cat/p/ds/eta__nominal"]}, keys_file)
        with pytest.raises(ValueError, match="eta__nominal.*not found"):
            util.load_all(keys_file, tmp_path)


class TestFilterHistograms:
    @pytest.fixture
    def histograms(self, make_wrapper):
        return [
            make_wrapper(),
            make_wrapper(variation="up"),
            make_wrapper(variable="eta"),
            make_wrapper(channel="other", process="q"),
            make_wrapper(campaign="c2", category="cat2", dataset="ds2"),
        ]

    def test_filter_histograms_no_criteria_returns_all(self, histograms):
        assert list(util.filter_histograms(histograms)) == histograms

    def test_filter_histograms_is_lazy_generator(self, histograms):
        result = util.filter_histograms(histograms)
        assert iter(result) is result

    @pytest.mark.parametrize(
        ("criteria", "expected_indices"),
        [
            ({"variation": "up"}, [1]),
            ({"variable": "eta"}, [2]),
            ({"channel": "other"}, [3]),
            ({"process": "q"}, [3]),
            ({"campaign": "c2"}, [4]),
            ({"category": "cat2"}, [4]),
            ({"dataset": "ds2"}, [4]),
            ({"campaign": "c", "variation": "nominal"}, [0, 2, 3]),
            ({"campaign": "c", "variation": "up", "variable": "eta"}, []),
            ({"variable": "none"}, []),
        ],
        ids=[
            "variation",
            "variable",
            "channel",
            "process",
            "campaign",
            "category",
            "dataset",
            "and-semantics",
            "and-no-match",
            "no-match",
        ],
    )
    def test_filter_histograms_selects_matching(
        self, histograms, criteria, expected_indices
    ):
        result = list(util.filter_histograms(histograms, **criteria))
        assert result == [histograms[i] for i in expected_indices]

    def test_filter_histograms_empty_input_gives_empty_result(self):
        assert list(util.filter_histograms([], campaign="c")) == []


class TestGetHistogram:
    ALL = {
        "campaign": "c",
        "channel": "ch",
        "category": "cat",
        "process": "p",
        "dataset": "ds",
        "variable": "pt",
        "variation": "nominal",
    }

    def test_get_histogram_returns_matching_wrapper(self, make_wrapper):
        hists = [make_wrapper(variation="up"), make_wrapper()]
        assert util.get_histogram(hists, **self.ALL) is hists[1]

    def test_get_histogram_returns_first_of_multiple_matches(
        self, make_wrapper
    ):
        hists = [make_wrapper(values=(1.0,)), make_wrapper(values=(2.0,))]
        assert util.get_histogram(hists, **self.ALL) is hists[0]

    @pytest.mark.parametrize("field", sorted(ALL))
    def test_get_histogram_every_field_must_match(self, make_wrapper, field):
        hists = [make_wrapper()]
        criteria = {**self.ALL, field: "nope"}
        with pytest.raises(ValueError, match="No matching histogram"):
            util.get_histogram(hists, **criteria)

    def test_get_histogram_empty_list_raises(self):
        with pytest.raises(ValueError, match="No matching histogram"):
            util.get_histogram([], **self.ALL)


class TestAddHistograms:
    def test_add_histograms_empty_list_raises(self):
        with pytest.raises(ValueError, match="No histograms to add"):
            util.add_histograms([])

    def test_add_histograms_sums_bin_contents(self):
        h1 = _make_th1("a", (1.0, 2.0, 3.0))
        h2 = _make_th1("b", (10.0, 20.0, 30.0))
        h3 = _make_th1("c", (100.0, 200.0, 300.0))
        total = util.add_histograms([h1, h2, h3])
        assert _contents(total) == [111.0, 222.0, 333.0]

    def test_add_histograms_does_not_modify_inputs(self):
        h1 = _make_th1("a", (1.0, 2.0))
        h2 = _make_th1("b", (3.0, 4.0))
        total = util.add_histograms([h1, h2])
        assert total is not h1
        assert _contents(h1) == [1.0, 2.0]
        assert _contents(h2) == [3.0, 4.0]

    def test_add_histograms_single_histogram_returns_clone(self):
        h = _make_th1("a", (1.0, 2.0))
        total = util.add_histograms([h])
        assert total is not h
        assert _contents(total) == [1.0, 2.0]

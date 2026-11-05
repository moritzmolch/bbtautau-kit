"""Unit tests for the creation of dataset specs from XRootD listings."""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from xyh.core.specs import dataset as dataset_module
from xyh.core.specs.dataset import create_dataset_spec, create_dataset_specs

SERVER = "root://server.example//"
BASE = Path("/store/ntuples")
TAG = "tag"


class FakeFileSystem:
    """XRootD `FileSystem` stand-in answering `dirlist` from a dict."""

    listings: dict[str, list[str] | None] = {}
    queried: list[str] = []
    server = None

    def __init__(self, server):
        type(self).server = server

    def dirlist(self, path, timeout=None):
        type(self).queried.append(path)
        names = type(self).listings.get(path)
        if names is None:
            return SimpleNamespace(ok=False), None
        return SimpleNamespace(ok=True), [
            SimpleNamespace(name=n) for n in names
        ]


@pytest.fixture
def listings(monkeypatch):
    FakeFileSystem.listings = {}
    FakeFileSystem.queried = []
    FakeFileSystem.server = None
    monkeypatch.setattr(dataset_module, "FileSystem", FakeFileSystem)
    return FakeFileSystem.listings


def _campaign(name="camp", year=2024, postfix=None):
    return SimpleNamespace(
        name=name, x=SimpleNamespace(year=year, postfix=postfix)
    )


def _dataset(name="ds", nicks=("nick",)):
    return SimpleNamespace(name=name, x=SimpleNamespace(nicks=list(nicks)))


def _main_dir(nick="nick", channel="tt", campaign="2024"):
    return f"{BASE}/{TAG}/CROWNRun/{campaign}/{nick}/{channel}"


def _friend_dir(friend, nick="nick", channel="tt", campaign="2024"):
    return f"{BASE}/{TAG}/CROWNFriend/{friend}/{campaign}/{nick}/{channel}"


def _spec(friends=(), campaign=None, dataset=None, channel="tt"):
    return create_dataset_spec(
        campaign or _campaign(),
        SimpleNamespace(name=channel),
        dataset or _dataset(),
        SERVER,
        BASE,
        TAG,
        list(friends),
    )


class TestCreateDatasetSpec:
    def test_main_files_collected_as_xrootd_urls(self, listings):
        listings[_main_dir()] = ["b.root", "a.root"]
        spec = _spec()
        assert spec.campaign == "camp"
        assert spec.channel == "tt"
        assert spec.dataset == "ds"
        assert spec.files == {
            "main": [
                f"root://server.example//{_main_dir().lstrip('/')}/b.root",
                f"root://server.example//{_main_dir().lstrip('/')}/a.root",
            ]
        }
        assert FakeFileSystem.server == SERVER

    def test_non_root_files_are_ignored(self, listings):
        listings[_main_dir()] = ["a.root", "a.txt", "log", "b.root.bak"]
        (file,) = _spec().files["main"]
        assert file.endswith("/a.root")

    def test_campaign_postfix_is_part_of_the_directory(self, listings):
        listings[_main_dir(campaign="2024APV")] = ["a.root"]
        spec = _spec(campaign=_campaign(postfix="APV"))
        assert len(spec.files["main"]) == 1

    def test_files_of_all_nicks_are_concatenated(self, listings):
        listings[_main_dir("n1")] = ["a.root"]
        listings[_main_dir("n2")] = ["b.root"]
        spec = _spec(dataset=_dataset(nicks=("n1", "n2")))
        assert [f.rsplit("/", 1)[1] for f in spec.files["main"]] == [
            "a.root",
            "b.root",
        ]

    def test_failed_main_listing_skips_nick_with_warning(
        self, listings, caplog
    ):
        listings[_main_dir("n2")] = ["b.root"]
        with caplog.at_level(logging.WARNING, logger=dataset_module.__name__):
            spec = _spec(dataset=_dataset(nicks=("n1", "n2")))
        assert [f.rsplit("/", 1)[1] for f in spec.files["main"]] == ["b.root"]
        assert "Failed to query main files for nick n1" in caplog.text

    def test_all_listings_failing_raises_missing_main(self, listings):
        with pytest.raises(ValueError, match="main tree"):
            _spec()

    def test_empty_listing_gives_empty_main_list(self, listings):
        listings[_main_dir()] = []
        assert _spec().files == {"main": []}

    def test_string_friend_files_are_sorted(self, listings):
        listings[_main_dir()] = ["a.root"]
        listings[_friend_dir("ff")] = ["2.root", "1.root", "x.txt"]
        spec = _spec(friends=["ff"])
        assert [f.rsplit("/", 1)[1] for f in spec.files["ff"]] == [
            "1.root",
            "2.root",
        ]

    def test_failed_friend_listing_omits_friend_and_warns(
        self, listings, caplog
    ):
        listings[_main_dir()] = ["a.root"]
        with caplog.at_level(logging.WARNING, logger=dataset_module.__name__):
            spec = _spec(friends=["ff"])
        assert set(spec.files) == {"main"}
        assert "Failed to query friend files" in caplog.text

    def test_dict_friend_without_restrictions_is_used(self, listings):
        listings[_main_dir()] = ["a.root"]
        listings[_friend_dir("ff")] = ["1.root"]
        spec = _spec(friends=[{"name": "ff"}])
        assert len(spec.files["ff"]) == 1

    @pytest.mark.parametrize(
        "friend",
        [
            {"name": "ff", "channels": ["et"]},
            {"name": "ff", "campaigns": ["other"]},
            {"name": "ff", "exclude_datasets": ["^d"]},
            {"name": "ff", "exclude_datasets": ["nomatch", "ds$|^ds"]},
        ],
        ids=["channel", "campaign", "dataset", "second-pattern"],
    )
    def test_dict_friend_restrictions_skip_friend_without_query(
        self, listings, friend
    ):
        listings[_main_dir()] = ["a.root"]
        listings[_friend_dir("ff")] = ["1.root"]
        spec = _spec(friends=[friend])
        assert set(spec.files) == {"main"}
        assert _friend_dir("ff") not in FakeFileSystem.queried

    def test_dict_friend_matching_restrictions_is_used(self, listings):
        listings[_main_dir()] = ["a.root"]
        listings[_friend_dir("ff")] = ["1.root"]
        spec = _spec(
            friends=[
                {
                    "name": "ff",
                    "channels": ["tt"],
                    "campaigns": ["camp"],
                    "exclude_datasets": ["^other"],
                }
            ]
        )
        assert "ff" in spec.files

    def test_exclude_pattern_matches_at_start_of_dataset_name(self, listings):
        # `re.match` anchors at the start: a pattern for a suffix is no match
        listings[_main_dir()] = ["a.root"]
        listings[_friend_dir("ff")] = ["1.root"]
        spec = _spec(
            friends=[{"name": "ff", "exclude_datasets": ["s$"]}],
            dataset=_dataset(name="ds"),
        )
        assert "ff" in spec.files


class TestCreateDatasetSpecs:
    @pytest.fixture
    def patch_config(self, monkeypatch):
        created = []
        loads = []

        def fake_load_inventory(path, campaign, channel, **kwargs):
            loads.append((path, campaign, channel, kwargs))
            return SimpleNamespace(
                campaign=SimpleNamespace(name=campaign),
                channel=SimpleNamespace(name=channel),
            )

        def fake_create(campaign, channel, dataset, *args):
            created.append((campaign.name, channel.name, dataset.name, args))
            return (campaign.name, channel.name, dataset.name)

        monkeypatch.setattr(
            dataset_module, "load_inventory", fake_load_inventory
        )
        monkeypatch.setattr(
            dataset_module,
            "gen_dataset_insts",
            lambda inv: [
                SimpleNamespace(name="d1"),
                SimpleNamespace(name="d2"),
            ],
        )
        monkeypatch.setattr(dataset_module, "create_dataset_spec", fake_create)
        return created, loads

    def test_spec_created_per_campaign_channel_dataset(self, patch_config):
        created, loads = patch_config
        specs = create_dataset_specs(
            "pkg:fn",
            {"k": 1},
            ["c1", "c2"],
            ["tt", "et"],
            SERVER,
            BASE,
            TAG,
            ["f"],
        )
        assert len(specs) == 8
        assert specs[:2] == [("c1", "tt", "d1"), ("c1", "tt", "d2")]
        assert loads[0] == ("pkg:fn", "c1", "tt", {"k": 1})
        assert len(loads) == 4

    def test_arguments_are_forwarded_to_spec_creation(self, patch_config):
        created, _ = patch_config
        create_dataset_specs(
            "pkg:fn", {}, ["c"], ["tt"], SERVER, BASE, TAG, ["f"]
        )
        assert created[0][3] == (SERVER, BASE, TAG, ["f"])

    def test_no_campaigns_gives_empty_list(self, patch_config):
        assert (
            create_dataset_specs("p", {}, [], ["tt"], SERVER, BASE, TAG, [])
            == []
        )

"""
Dataset-process maps that map a physics process of the analysis to a list of
datasets that the events are sourced from.
"""

from itertools import product

from order import Campaign, Channel

from xyh.config.profiles import get_profile


def get_process_datasets_map(
    campaign_inst: Campaign,
    channel_inst: Channel,
) -> dict[str, list[str]]:
    """
    Create a mapping of processes to datasets for a given campaign and channel.

    Parameters
    ----------
    campaign_inst : Campaign
        The campaign instance for which to create the mapping.

    channel_inst : Channel
        The channel instance for which to create the mapping.

    Returns
    -------
    dict[str, list[str]]
        A dictionary mapping process names to lists of dataset names.
    """

    # Define data process
    data_datasets = {
        "2022_pre_ee_nano_v12": {
            "et": ["egamma_2022_cd"],
            "mt": ["muon_2022_cd"],
            "tt": ["tau_2022_cd"],
            "em": ["egamma_2022_cd"],
            "ee": ["egamma_2022_cd"],
            "mm": ["muon_2022_cd"],
        },
        "2022_post_ee_nano_v12": {
            "et": ["egamma_2022_efg"],
            "mt": ["muon_2022_efg"],
            "tt": ["tau_2022_efg"],
            "em": ["egamma_2022_efg"],
            "ee": ["egamma_2022_efg"],
            "mm": ["muon_2022_efg"],
        },
        "2023_pre_bpix_nano_v12": {
            "et": ["egamma_2023_c"],
            "mt": ["muon_2023_c"],
            "tt": ["tau_2023_c"],
            "em": ["egamma_2023_c"],
            "ee": ["egamma_2023_c"],
            "mm": ["muon_2023_c"],
        },
        "2023_post_bpix_nano_v12": {
            "et": ["egamma_2023_d"],
            "mt": ["muon_2023_d"],
            "tt": ["tau_2023_d"],
            "em": ["egamma_2023_d"],
            "ee": ["egamma_2023_d"],
            "mm": ["muon_2023_d"],
        },
        "2024_nano_v15": {
            "et": ["egamma_2024_cdefghi"],
            "mt": ["muon_2024_cdefghi"],
            "tt": ["tau_2024_cdefghi"],
            "em": ["egamma_2024_cdefghi"],
            "ee": ["egamma_2024_cdefghi"],
            "mm": ["muon_2024_cdefghi"],
        },
        "2025_nano_v15": {
            "et": ["egamma_2025_cdefg"],
            "mt": ["muon_2025_cdefg"],
            "tt": ["tau_2025_cdefg"],
            "em": ["egamma_2025_cdefg"],
            "ee": ["egamma_2025_cdefg"],
            "mm": ["muon_2025_cdefg"],
        },
    }[campaign_inst.name][channel_inst.name]

    # Top quark pair production datasets
    tt_datasets = [
        "tt_4q_powheg",
        "tt_lnu2q_powheg",
        "tt_2l2nu_powheg",
    ]

    # Single top quark datasets
    single_t_datasets = []
    if campaign_inst.x.year in [2022, 2023]:
        single_t_datasets = [
            "tbq_t_tchannel_powheg",
            "tbq_tbar_tchannel_powheg",
            "tb_lnub_t_schannel_4fs_amcatnlo",
            "tb_lnub_tbar_schannel_4fs_amcatnlo",
            "tw_2l2nu_t_powheg",
            "tw_lnu2q_t_powheg",
            "tw_4q_t_powheg",
            "tw_2l2nu_tbar_powheg",
            "tw_lnu2q_tbar_powheg",
            "tw_4q_tbar_powheg",
        ]
    elif campaign_inst.x.year in [2024, 2025]:
        single_t_datasets = [
            "tbq_lnu_t_tchannel_powheg",
            "tbq_2q_t_tchannel_powheg",
            "tbq_lnu_tbar_tchannel_powheg",
            "tbq_2q_tbar_tchannel_powheg",
            "tb_lnub_t_schannel_4fs_amcatnlo",
            "tb_2q_t_schannel_4fs_amcatnlo",
            "tb_lnub_tbar_schannel_4fs_amcatnlo",
            "tb_2q_tbar_schannel_4fs_amcatnlo",
            "tw_2l2nu_t_powheg",
            "tw_lnu2q_t_powheg",
            "tw_4q_t_powheg",
            "tw_2l2nu_tbar_powheg",
            "tw_lnu2q_tbar_powheg",
            "tw_4q_tbar_powheg",
        ]

    # Z datasets
    z_2e_2mu_datasets = []
    z_2tau_datasets = []
    if campaign_inst.x.year in [2022, 2023]:
        z_2e_2mu_datasets = [
            "z_2l_m10to50_amcatnlo",
            "z_2l_m50_0j_amcatnlo",
            "z_2l_m50_1j_amcatnlo",
            "z_2l_m50_2j_amcatnlo",
        ]
        z_2tau_datasets = [
            "z_2tau_m50_0j_amcatnlo",
            "z_2tau_m50_1j_amcatnlo",
            "z_2tau_m50_2j_amcatnlo",
        ]
    elif campaign_inst.x.year in [2024, 2025]:
        z_2e_2mu_datasets = [
            "z_2e_m10to50_amcatnlo",
            "z_2e_m50_0j_amcatnlo",
            "z_2e_m50_1j_amcatnlo",
            "z_2e_m50_2j_amcatnlo",
            "z_2mu_m10to50_amcatnlo",
            "z_2mu_m50_0j_amcatnlo",
            "z_2mu_m50_1j_amcatnlo",
            "z_2mu_m50_2j_amcatnlo",
        ]
        z_2tau_datasets = [
            "z_2tau_m10to50_amcatnlo",
            "z_2tau_m50_0j_amcatnlo",
            "z_2tau_m50_1j_amcatnlo",
            "z_2tau_m50_2j_amcatnlo",
        ]

    # W datasets
    w_datasets = []
    if campaign_inst.x.year in [2022, 2023]:
        w_datasets = [
            "w_lnu_0j_amcatnlo",
            "w_lnu_1j_amcatnlo",
            "w_lnu_2j_amcatnlo",
        ]
    elif campaign_inst.x.year in [2024, 2025]:
        w_datasets = [
            "w_enu_amcatnlo",
            "w_munu_amcatnlo",
            "w_taunu_amcatnlo",
        ]

    # VV datasets
    vv_datasets = [
        "ww_2l2nu_powheg",
        "ww_lnu2q_powheg",
        "ww_4q_powheg",
        "wz_3lnu_powheg",
        "wz_lnu2q_powheg",
        "wz_2l2q_powheg",
        "zz_4l_powheg",
        "zz_2l2nu_powheg",
        "zz_2l2q_powheg",
        "zz_2nu2q_powheg",
    ]

    # H -> tau tau datasets
    h_2tau_datasets = []
    if campaign_inst.x.year in [2022, 2023]:
        h_2tau_datasets = [
            "gg_h_2tau_powheg",
            "vbf_h_2tau_powheg",
        ]
    elif campaign_inst.x.year in [2024, 2025]:
        h_2tau_datasets = [
            "gg_h_2tau_powheg",
        ]

    # H -> bb datasets
    h_2b_datasets = [
        "gg_h_2b_powheg",
        "vbf_h_2b_powheg",
    ]

    # ttH datasets
    tth_datasets = [
        "tth_h_2b_powheg",
        "tth_h_non2b_powheg",
    ]

    # HH -> bbtautau datasets
    hh_2b2tau_datasets = []
    if campaign_inst.x.year == 2022:
        hh_2b2tau_datasets = [
            "gg_hh_2b2tau_powheg",
            "vbf_hh_2b2tau_powheg",
        ]
    elif campaign_inst.x.year in [2023, 2024, 2025]:
        hh_2b2tau_datasets = ["gg_hh_2b2tau_powheg"]

    # Set up the process-datasets map for signals
    xyh_process_datasets_map = {
        f"xyh_{y_decay_mode}_{h_decay_mode}_{m_x}_{m_y}": [
            f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph",
        ]
        for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(
            get_profile().decay_modes, get_profile().xy_masses
        )
        if ((y_decay_mode, h_decay_mode), (m_x, m_y))
        not in get_profile().missing_signal_samples[campaign_inst.name]
    }

    # Helper function to unroll dictionary keys and clone corresponding
    # values
    def _unroll(d):
        new = {}
        for k, v in d.items():
            if isinstance(k, tuple):
                for _k in k:
                    if _k in new:
                        raise ValueError(f"Key {k} defined multiple times")
                    new[_k] = v
            else:
                if k in new:
                    raise KeyError(f"Key {k} defined multiple times")
                new[k] = v
        return new

    # Define a mapping of processes to datasets for the analysis
    process_datasets_map = _unroll(
        {
            # ----------------------------------------------------------------------
            "data": data_datasets,
            # ----------------------------------------------------------------------
            **xyh_process_datasets_map,
            # ----------------------------------------------------------------------
            ("tt_jetfakes", "tt_rem", "tt_tautau"): tt_datasets,
            (
                "single_t_jetfakes",
                "single_t_rem",
                "single_t_tautau",
            ): single_t_datasets,
            (
                "z_2e_2mu_tautau",
                "z_2e_2mu_jetfakes",
                "z_2e_2mu_rem",
            ): z_2e_2mu_datasets,
            ("z_2tau_tautau", "z_2tau_jetfakes", "z_2tau_rem"): z_2tau_datasets,
            ("w_lnu_jetfakes", "w_lnu_rem", "w_lnu_tautau"): w_datasets,
            ("vv_tautau", "vv_jetfakes", "vv_rem"): vv_datasets,
            ("h_2tau_jetfakes", "h_2tau_tautau", "h_2tau_rem"): h_2tau_datasets,
            ("h_2b_jetfakes", "h_2b_tautau", "h_2b_rem"): h_2b_datasets,
            ("tth_jetfakes", "tth_rem", "tth_tautau"): tth_datasets,
            "gg_hh_2b2tau": hh_2b2tau_datasets,
            "jetfakes": [],  # data-driven estimate, dataset list stays empty
        }
    )

    return process_datasets_map

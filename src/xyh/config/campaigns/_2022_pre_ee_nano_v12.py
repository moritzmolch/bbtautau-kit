"""
2022preEE data-taking era, nanoAOD v12
"""

from order import Campaign

from xyh.config.profiles import get_profile

from ._util import add_dataset

# ------------------------------------------------------------------------------
# Campaign definition
# ------------------------------------------------------------------------------


# Campaign 2022preEE, NanoAOD v12
cpn_2022_pre_ee_nano_v12 = Campaign(
    name="2022_pre_ee_nano_v12",
    id="+",
    ecm=13.6,
    aux={
        "year": 2022,
        "postfix": "preEE",
        "lumi": 7.989513666,  # fb^-1
        "runs": {
            "C": [355794, 357486],
            "D": [357487, 359021],
        },
        "nano_version": "v12",
    },
)


# ------------------------------------------------------------------------------
# Dataset names and nicks
# ------------------------------------------------------------------------------


signal_v3 = {
    # (m_x, m_y) of signal samples whose dataset uses nanoAOD version v3
    "y2b": {
        (2000, 60),
    },
    "y2tau":     set(),
}

# Function to derive name of a signal sample from the signal parameters
def xyh_name(
    y_decay_mode: str,
    h_decay_mode: str,
    m_x: int,
    m_y: int,
) -> str:
    decay_mode = (
        f"2{y_decay_mode[2:].capitalize()}2{h_decay_mode[2:].capitalize()}"
    )
    version = "v3" if (m_x, m_y) in signal_v3[y_decay_mode] else "v2"
    return f"NMSSM_XtoYHto{decay_mode}_MX-{m_x}_MY-{m_y}_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-{version}"


# Map of dataset names to their corresponding nicks in the sample database
dataset_nicks = {
    # --- Data -----------------------------------------------------------------
    "egamma_2022_cd": [
        "EGamma_Run2022C-22Sep2023-v1",
        "EGamma_Run2022D-22Sep2023-v1",
    ],
    "muon_2022_cd": [
        "Muon_Run2022C-22Sep2023-v1",
        "Muon_Run2022D-22Sep2023-v1",
    ],
    "tau_2022_cd": [
        "Tau_Run2022C-22Sep2023-v1",
        "Tau_Run2022D-22Sep2023-v1",
    ],
    # --- Signals --------------------------------------------------------------
    **{
        f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph": xyh_name(
            y_decay_mode, h_decay_mode, m_x, m_y
        )
        for (y_decay_mode, h_decay_mode), (
            m_x,
            m_y,
        ) in get_profile().iterate_signal_parameters(
            campaign=cpn_2022_pre_ee_nano_v12.name
        )
    },
    # --- Top quark pair production --------------------------------------------
    "tt_4q_powheg": [
        "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tt_lnu2q_powheg": [
        "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tt_2l2nu_powheg": [
        "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    # --- Single top quark production ------------------------------------------
    "tbq_t_tchannel_powheg": "TBbarQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "tbq_tbar_tchannel_powheg": "TbarBQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "tb_lnub_t_schannel_4fs_amcatnlo": "TBbartoLplusNuBbar-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "tb_lnub_tbar_schannel_4fs_amcatnlo": "TbarBtoLminusNuB-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "tw_2l2nu_t_powheg": [
        "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tw_lnu2q_t_powheg": [
        "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tw_4q_t_powheg": "TWminusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "tw_2l2nu_tbar_powheg": [
        "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tw_lnu2q_tbar_powheg": [
        "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2",
    ],
    "tw_4q_tbar_powheg": "TbarWplusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    # --- Z + jets production --------------------------------------------------
    "z_2l_m10to50_amcatnlo": [
        "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
        "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v1",
    ],
    "z_2l_m50_0j_amcatnlo": "DYto2L-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "z_2l_m50_1j_amcatnlo": "DYto2L-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "z_2l_m50_2j_amcatnlo": "DYto2L-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "z_2tau_m50_0j_amcatnlo": "DYto2Tau-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v1",
    "z_2tau_m50_1j_amcatnlo": "DYto2Tau-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v1",
    "z_2tau_m50_2j_amcatnlo": "DYto2Tau-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v1",
    # --- W + jets production --------------------------------------------------
    "w_lnu_0j_amcatnlo": "WtoLNu-2Jets_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3",
    "w_lnu_1j_amcatnlo": "WtoLNu-2Jets_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "w_lnu_2j_amcatnlo": "WtoLNu-2Jets_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    # --- Diboson production ---------------------------------------------------
    "ww_2l2nu_powheg": "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "ww_lnu2q_powheg": "WWtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "ww_4q_powheg": "WWto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "wz_3lnu_powheg": "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "wz_lnu2q_powheg": "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "wz_2l2q_powheg": "WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "zz_4l_powheg": "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "zz_2l2nu_powheg": "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "zz_2l2q_powheg": "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "zz_2nu2q_powheg": "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    # --- H -> tau tau production ----------------------------------------------
    "gg_h_2tau_powheg": "GluGluHToTauTau_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "vbf_h_2tau_powheg": "VBFHToTauTau_M125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    # --- H -> b b production --------------------------------------------------
    "gg_h_2b_powheg": "GluGluHto2B_M-125_TuneCP5_13p6TeV_powheg-minlo-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "vbf_h_2b_powheg": "VBFHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3",
    # --- ttH production -------------------------------------------------------
    "tth_h_2b_powheg": "TTH_Hto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3",
    "tth_h_non2b_powheg": "TTHtoNon2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v4",
    # --- HH -> b b tau tau production -----------------------------------------
    "gg_hh_2b2tau": "GluGlutoHHto2B2Tau_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "vbf_hh_2b2tau": "VBFHHto2B2Tau_CV-1_C2V-1_C3-1_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
}


# ------------------------------------------------------------------------------
# Dataset registration
# ------------------------------------------------------------------------------


# Add datasets to the campaign
for name, nicks in dataset_nicks.items():
    add_dataset(cpn_2022_pre_ee_nano_v12, name, nicks)

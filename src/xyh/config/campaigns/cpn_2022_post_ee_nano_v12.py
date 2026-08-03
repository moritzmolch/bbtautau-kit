"""
2022postEE data-taking era, nanoAOD v12
"""

from order import Campaign
from .util import add_dataset


# ------------------------------------------------------------------------------
# Campaign definition
# ------------------------------------------------------------------------------


# Campaign 2022postEE, NanoAOD v12
cpn_2022_post_ee_nano_v12 = Campaign(
    name="2022_post_ee_nano_v12",
    id="+",
    ecm=13.6,
    aux=dict(
        year=2022,
        postfix="postEE",
        lumi=26.674924045,  # fb^-1
        runs={
            "E": [359022, 360331],
            "F": [360332, 362180],
            "G": [362350, 362760],
        },
        nano_version="v12",
    ),
)


# ------------------------------------------------------------------------------
# Dataset names and nicks
# ------------------------------------------------------------------------------


# Function to derive name of a signal sample from the signal parameters
def xyh_name(
    *,
    y_decay_mode: str,
    h_decay_mode: str,
    m_x: int,
    m_y: int,
) -> str:
    decay_mode = (
        f"2{y_decay_mode[2:].capitalize()}{h_decay_mode[2:].capitalize()}"
    )
    return f"NMSSM_XtoYHto{decay_mode}_MX-{m_x}_MY-{m_y}_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer22EENanoAODv12-130X"


# Map of dataset names to their corresponding nicks in the sample database
dataset_nicks = {
    # --- Data -----------------------------------------------------------------
    "egamma_2022_efg": [
        "EGamma_Run2022E-16Dec2023-v1",
        "EGamma_Run2022E-22Sep2023-v1",
        "EGamma_Run2022F-19Dec2023-v1",
        "EGamma_Run2022F-22Sep2023-v1",
        "EGamma_Run2022G-16Dec2023-v1",
        "EGamma_Run2022G-22Sep2023-v2",
    ],
    "muon_2022_efg": [
        "Muon_Run2022E-16Dec2023-v1",
        "Muon_Run2022E-22Sep2023-v1",
        "Muon_Run2022F-19Dec2023-v1",
        "Muon_Run2022F-22Sep2023-v2",
        "Muon_Run2022G-19Dec2023-v2",
        "Muon_Run2022G-22Sep2023-v1",
    ],
    "tau_2022_efg": [
        "Tau_Run2022E-22Sep2023-v1",
        "Tau_Run2022F-22Sep2023-v1",
        "Tau_Run2022G-22Sep2023-v1",
    ],
    # --- signal ---------------------------------------------------------------
    "xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph": xyh_name,
    # --- Top quark pair production --------------------------------------------
    "tt_4q_powheg": [
        "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tt_2l2q_powheg": [
        "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tt_2l2nu_powheg": [
        "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    # --- Single top quark production ------------------------------------------
    "tbq_t_tchannel_powheg": "TBbarQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer22EENanoAODv12-130X",
    "tbq_tbar_tchannel_powheg": "TbarBQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer22EENanoAODv12-130X",
    "tb_lnub_t_schannel_4fs_amcatnlo": "TBbartoLplusNuBbar-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer22EENanoAODv12-130X",
    "tb_lnub_tbar_schannel_4fs_amcatnlo": "TbarBtoLminusNuB-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer22EENanoAODv12-130X",
    "tw_2l2nu_t_powheg": [
        "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tw_lnu2q_t_powheg": [
        "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tw_4q_t_powheg": "TWminusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "tw_2l2nu_tbar_powheg": [
        "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tw_lnu2q_tbar_powheg": [
        "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "tw_4q_tbar_powheg": "TbarWplusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- Z + jets production --------------------------------------------------
    "z_2l_m10to50_amcatnlo": [
        "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
        "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "z_2l_m50_0j_amcatnlo": "DYto2L-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "z_2l_m50_1j_amcatnlo": "DYto2L-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "z_2l_m50_2j_amcatnlo": "DYto2L-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "z_2tau_m50_0j_amcatnlo": "DYto2Tau-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "z_2tau_m50_1j_amcatnlo": "DYto2Tau-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "z_2tau_m50_2j_amcatnlo": "DYto2Tau-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- W + jets production --------------------------------------------------
    "w_lnu_0j_amcatnlo": "WtoLNu-2Jets_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "w_lnu_1j_amcatnlo": "WtoLNu-2Jets_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    "w_lnu_2j_amcatnlo": "WtoLNu-2Jets_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- Diboson production ---------------------------------------------------
    "ww_2l2nu_powheg": [
        "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "ww_lnu2q_powheg": "WWtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "ww_4q_powheg": "WWto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "wz_3lnu_powheg": [
        "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "wz_lnu2q_powheg": [
        "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "wz_2l2q_powheg": "WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "zz_4l_powheg": [
        "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "zz_2l2nu_powheg": [
        "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "zz_2l2q_powheg": [
        "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    "zz_2nu2q_powheg": [
        "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
        "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X_ext1",
    ],
    # --- H -> tau tau production ----------------------------------------------
    "gg_h_2tau_powheg": "GluGluHTo2TauUncorrelatedDecay_M-125_CP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "vbf_h_2tau_powheg": "VBFHTo2TauUncorrelatedDecay_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- H -> b b production --------------------------------------------------
    "gg_h_2b_powheg": "GluGluHto2B_M-125_TuneCP5_13p6TeV_powheg-minlo-pythia8_Run3Summer22EENanoAODv12-130X",
    "vbf_h_2b_powheg": "VBFHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- ttH production -------------------------------------------------------
    "tth_h_2b_powheg": "TTH_Hto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "tth_h_non2b_powheg": "TTHtoNon2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    # --- HH -> b b tau tau production -----------------------------------------
    "gg_hh_2b2tau": "GluGlutoHHto2B2Tau_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer22EENanoAODv12-130X",
    "vbf_hh_2b2tau": "VBFHHto2B2Tau_CV_1_C2V_1_C3_1_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer22EENanoAODv12-130X",
}


# Add datasets to the campaign
for name, nicks in dataset_nicks.items():
    add_dataset(cpn_2022_post_ee_nano_v12, name, nicks)

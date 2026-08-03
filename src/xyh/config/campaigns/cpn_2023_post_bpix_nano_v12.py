"""
2023postBPix data-taking era, nanoAOD v12
"""

from order import Campaign
from xyh.campaigns.util import add_dataset


# ------------------------------------------------------------------------------
# Campaign definition
# ------------------------------------------------------------------------------


# 2023postBPix, NanoAOD v12
cpn_2023_post_bpix_nano_v12 = Campaign(
    name="2023_post_bpix_nano_v12",
    id="+",
    ecm=13.6,
    lumi=9.676737966,  # fb^-1
    aux=dict(
        year=2023,
        postfix="postBPix",
        runs={
            "D": [369803, 372415],
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
    return f"NMSSM_XtoYHto{decay_mode}_MX-{m_x}_MY-{m_y}_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer23BPixNanoAODv12-130X"


# Map of dataset names to their corresponding nicks in the sample database
dataset_nicks = {
    # --- Data -----------------------------------------------------------------
    "egamma_2023_d": [
        "EGamma0_Run2023D-22Sep2023_v1-v1",
        "EGamma0_Run2023D-22Sep2023_v2-v1",
        "EGamma1_Run2023D-22Sep2023_v1-v1",
        "EGamma1_Run2023D-22Sep2023_v2-v1",
    ],
    "muon_2023_d": [
        "Muon0_Run2023D-22Sep2023_v1-v1",
        "Muon0_Run2023D-22Sep2023_v2-v1",
        "Muon1_Run2023D-22Sep2023_v1-v1",
        "Muon1_Run2023D-22Sep2023_v2-v1",
    ],
    "tau_2023_d": [
        "Tau_Run2023D-22Sep2023_v1-v1",
        "Tau_Run2023D-22Sep2023_v2-v1",
    ],
    # --- TODO signal ----------------------------------------------------------
    "xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph": xyh_name,
    # --- Top quark pair production --------------------------------------------
    "tt_4q_powheg": "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tt_lnu2q_powheg": "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tt_2l2nu_powheg": "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- Single top quark production ------------------------------------------
    "tbq_t_tchannel_powheg": "TBbarQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tbq_tbar_tchannel_powheg": "TbarBQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tb_lnub_t_schannel_4fs_amcatnlo": "TBbartoLplusNuBbar-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tb_lnub_tbar_schannel_4fs_amcatnlo": "TbarBtoLminusNuB-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_2l2nu_t_powheg": "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_lnu2q_t_powheg": "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_4q_t_powheg": "TWminusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_2l2nu_tbar_powheg": "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_lnu2q_tbar_powheg": "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tw_4q_tbar_powheg": "TbarWplusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- Z + jets production --------------------------------------------------
    "z_2l_m10to50_amcatnlo": "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_ext1",
    "z_2l_m50_0j_amcatnlo": "DYto2L-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "z_2l_m50_1j_amcatnlo": "DYto2L-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "z_2l_m50_2j_amcatnlo": "DYto2L-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "z_2tau_m50_0j_amcatnlo": "DYto2Tau-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "z_2tau_m50_1j_amcatnlo": "DYto2Tau-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "z_2tau_m50_2j_amcatnlo": "DYto2Tau-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- W + jets production --------------------------------------------------
    "w_lnu_0j_amcatnlo": "WtoLNu-2Jets_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "w_lnu_1j_amcatnlo": "WtoLNu-2Jets_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "w_lnu_2j_amcatnlo": "WtoLNu-2Jets_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- Diboson production ---------------------------------------------------
    "ww_2l2nu_powheg": "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "ww_lnu2q_powheg": "WWtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "ww_4q_powheg": "WWto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "wz_3lnu_powheg": "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "wz_lnu2q_powheg": "WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "wz_2l2q_powheg": "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "zz_4l_powheg": "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "zz_2l2nu_powheg": "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "zz_2l2q_powheg": "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "zz_2nu2q_powheg": "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- H -> tau tau production ----------------------------------------------
    "gg_h_2tau_powheg": "GluGluHTo2TauUncorrelatedDecay_M-125_CP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "vbf_h_2tau_powheg": "VBFHTo2TauUncorrelatedDecay_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- H -> b b production --------------------------------------------------
    "gg_h_2b_powheg": "GluGluHto2B_M-125_TuneCP5_13p6TeV_powheg-minlo-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "vbf_h_2b_powheg": "VBFHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- ttH production -------------------------------------------------------
    "tth_h_2b_powheg": "TTHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    "tth_h_non2b_powheg": "TTHtoNon2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X",
    # --- HH -> b b tau tau production -----------------------------------------
    "gg_hh_2b2tau": "GluGlutoHHto2B2Tau_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-tsg",
    # "vbf_hh_2b2tau": ,  # no NanoAOD v12 sample available
}


# Add datasets to the campaign
for name, nicks in dataset_nicks.items():
    add_dataset(cpn_2023_post_bpix_nano_v12, name, nicks)

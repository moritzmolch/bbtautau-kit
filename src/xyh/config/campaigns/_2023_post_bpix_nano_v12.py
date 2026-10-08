"""
2023postBPix data-taking era, nanoAOD v12
"""

from order import Campaign

from xyh.config.profiles import get_profile

from ._util import add_dataset

# ------------------------------------------------------------------------------
# Campaign definition
# ------------------------------------------------------------------------------


# 2023postBPix, NanoAOD v12
cpn_2023_post_bpix_nano_v12 = Campaign(
    name="2023_post_bpix_nano_v12",
    id="+",
    ecm=13.6,
    aux={
        "year": 2023,
        "postfix": "postBPix",
        "lumi": 9.676737966,  # fb^-1
        "runs": {
            "D": [369803, 372415],
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
        (1600, 60),
    },
    "y2tau": {
        (550, 400),
        (650, 60),
        (700, 200),
        (800, 300),
        (1000, 95),
        (1200, 100),
        (1400, 300),
        (1600, 1000),
        (1600, 1200),
        (1800, 1600),
        (2000, 95),
        (2000, 1000),
        (2000, 1600),
        (2500, 800),
        (3000, 95),
        (3500, 60),
        (3500, 400),
        (3500, 1400),
        (4000, 600),
    },
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
    return f"NMSSM_XtoYHto{decay_mode}_MX-{m_x}_MY-{m_y}_TuneCP5_13p6TeV_madgraph-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-{version}"


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
    # --- Signals --------------------------------------------------------------
    **{
        f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph": xyh_name(
            y_decay_mode, h_decay_mode, m_x, m_y
        )
        for (y_decay_mode, h_decay_mode), (
            m_x,
            m_y,
        ) in get_profile().iterate_signal_parameters(
            campaign=cpn_2023_post_bpix_nano_v12.name
        )
    },
    # --- Top quark pair production --------------------------------------------
    "tt_4q_powheg": "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tt_lnu2q_powheg": "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tt_2l2nu_powheg": "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    # --- Single top quark production ------------------------------------------
    "tbq_t_tchannel_powheg": "TBbarQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tbq_tbar_tchannel_powheg": "TbarBQ_t-channel_4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tb_lnub_t_schannel_4fs_amcatnlo": "TBbartoLplusNuBbar-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tb_lnub_tbar_schannel_4fs_amcatnlo": "TbarBtoLminusNuB-s-channel-4FS_TuneCP5_13p6TeV_amcatnlo-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tw_2l2nu_t_powheg": "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tw_lnu2q_t_powheg": "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tw_4q_t_powheg": "TWminusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tw_2l2nu_tbar_powheg": "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tw_lnu2q_tbar_powheg": "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    "tw_4q_tbar_powheg": "TbarWplusto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
    # --- Z + jets production --------------------------------------------------
    "z_2l_m10to50_amcatnlo": "DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2_ext1-v3",
    "z_2l_m50_0j_amcatnlo": "DYto2L-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "z_2l_m50_1j_amcatnlo": "DYto2L-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "z_2l_m50_2j_amcatnlo": "DYto2L-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "z_2tau_m50_0j_amcatnlo": "DYto2Tau-2Jets_MLL-50_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v1",
    "z_2tau_m50_1j_amcatnlo": "DYto2Tau-2Jets_MLL-50_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v1",
    "z_2tau_m50_2j_amcatnlo": "DYto2Tau-2Jets_MLL-50_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v1",
    # --- W + jets production --------------------------------------------------
    "w_lnu_0j_amcatnlo": "WtoLNu-2Jets_0J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "w_lnu_1j_amcatnlo": "WtoLNu-2Jets_1J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "w_lnu_2j_amcatnlo": "WtoLNu-2Jets_2J_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    # --- Diboson production ---------------------------------------------------
    "ww_2l2nu_powheg": "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "ww_lnu2q_powheg": "WWtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "ww_4q_powheg": "WWto4Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "wz_3lnu_powheg": "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "wz_lnu2q_powheg": "WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "wz_2l2q_powheg": "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "zz_4l_powheg": "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "zz_2l2nu_powheg": "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "zz_2l2q_powheg": "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "zz_2nu2q_powheg": "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    # --- H -> tau tau production ----------------------------------------------
    "gg_h_2tau_powheg": "GluGluHTo2TauUncorrelatedDecay_M-125_CP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "vbf_h_2tau_powheg": "VBFHTo2TauUncorrelatedDecay_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    # --- H -> b b production --------------------------------------------------
    "gg_h_2b_powheg": "GluGluHto2B_M-125_TuneCP5_13p6TeV_powheg-minlo-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    "vbf_h_2b_powheg": "VBFHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    # --- ttH production -------------------------------------------------------
    "tth_h_2b_powheg": "TTHto2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v3",
    "tth_h_non2b_powheg": "TTHtoNon2B_M-125_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2",
    # --- HH -> b b tau tau production -----------------------------------------
    "gg_hh_2b2tau": "GluGlutoHHto2B2Tau_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8_Run3Summer23BPixNanoAODv12-tsg_130X_mcRun3_2023_realistic_postBPix_v6-v2",
    # "vbf_hh_2b2tau": ,  # no NanoAOD v12 sample available
}


# Add datasets to the campaign
for name, nicks in dataset_nicks.items():
    add_dataset(cpn_2023_post_bpix_nano_v12, name, nicks)

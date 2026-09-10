"""
2025 data-taking era, nanoAOD v15
"""

from itertools import product

from order import Campaign

from xyh.config.profiles import get_profile

from ._util import add_dataset

# ------------------------------------------------------------------------------
# Campaign definition
# ------------------------------------------------------------------------------


# 2025, NanoAOD v15
cpn_2025_nano_v15 = Campaign(
    name="2025_nano_v15",
    id="+",
    ecm=13.6,
    aux={
        "year": 2025,
        "postfix": None,
        "lumi": 109.898115287,  # fb^-1
        "runs": {
            "C": [392159, 393609],
            "D": [394286, 395967],
            "E": [395968, 396597],
            "F": [396598, 397853],
            "G": [397854, 398903],
        },
        "nano_version": "v15",
    },
)


# ------------------------------------------------------------------------------
# Dataset names and nicks
# ------------------------------------------------------------------------------


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
    return f"NMSSM-XtoYHto{decay_mode}_Par-MX-{m_x}-MY-{m_y}_TuneCP5_13p6TeV_madgraph-pythia8_RunIII2025Summer24NanoAODv15-150X"


# Map of dataset names to their corresponding nicks in the sample database
dataset_nicks = {
    # --- Data -----------------------------------------------------------------
    "egamma_2025_cdefg": [
        "EGamma0_Run2025C-PromptReco-v1",
        "EGamma0_Run2025C-PromptReco-v2",
        "EGamma0_Run2025D-PromptReco-v1",
        "EGamma0_Run2025E-PromptReco-v1",
        "EGamma0_Run2025F-PromptReco-v1",
        "EGamma0_Run2025F-PromptReco-v2",
        "EGamma0_Run2025G-PromptReco-v1",
        "EGamma1_Run2025C-PromptReco-v1",
        "EGamma1_Run2025C-PromptReco-v2",
        "EGamma1_Run2025D-PromptReco-v1",
        "EGamma1_Run2025E-PromptReco-v1",
        "EGamma1_Run2025F-PromptReco-v1",
        "EGamma1_Run2025F-PromptReco-v2",
        "EGamma1_Run2025G-PromptReco-v1",
        "EGamma2_Run2025C-PromptReco-v1",
        "EGamma2_Run2025C-PromptReco-v2",
        "EGamma2_Run2025D-PromptReco-v1",
        "EGamma2_Run2025E-PromptReco-v1",
        "EGamma2_Run2025F-PromptReco-v1",
        "EGamma2_Run2025F-PromptReco-v2",
        "EGamma2_Run2025G-PromptReco-v1",
        "EGamma3_Run2025C-PromptReco-v1",
        "EGamma3_Run2025C-PromptReco-v2",
        "EGamma3_Run2025D-PromptReco-v1",
        "EGamma3_Run2025E-PromptReco-v1",
        "EGamma3_Run2025F-PromptReco-v1",
        "EGamma3_Run2025F-PromptReco-v2",
        "EGamma3_Run2025G-PromptReco-v1",
    ],
    "muon_2025_cdefg": [
        "Muon0_Run2025C-PromptReco-v1",
        "Muon0_Run2025C-PromptReco-v2",
        "Muon0_Run2025D-PromptReco-v1",
        "Muon0_Run2025E-PromptReco-v1",
        "Muon0_Run2025F-PromptReco-v1",
        "Muon0_Run2025F-PromptReco-v2",
        "Muon0_Run2025G-PromptReco-v1",
        "Muon1_Run2025C-PromptReco-v1",
        "Muon1_Run2025C-PromptReco-v2",
        "Muon1_Run2025D-PromptReco-v1",
        "Muon1_Run2025E-PromptReco-v1",
        "Muon1_Run2025F-PromptReco-v1",
        "Muon1_Run2025F-PromptReco-v2",
        "Muon1_Run2025G-PromptReco-v1",
    ],
    "tau_2025_cdefg": [
        "Tau_Run2025C-PromptReco-v1",
        "Tau_Run2025C-PromptReco-v2",
        "Tau_Run2025D-PromptReco-v1",
        "Tau_Run2025E-PromptReco-v1",
        "Tau_Run2025F-PromptReco-v1",
        "Tau_Run2025F-PromptReco-v2",
        "Tau_Run2025G-PromptReco-v1",
    ],
    # --- Signals --------------------------------------------------------------
    **{
        f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph": xyh_name(
            y_decay_mode, h_decay_mode, m_x, m_y
        )
        for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(
            get_profile().decay_modes, get_profile().xy_masses
        )
        if ((y_decay_mode, h_decay_mode), (m_x, m_y))
        not in get_profile().missing_signal_samples[cpn_2025_nano_v15.name]
    },
    # --- Top quark pair production --------------------------------------------
    "tt_4q_powheg": "TTto4Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tt_lnu2q_powheg": "TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tt_2l2nu_powheg": "TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- Single top quark production ------------------------------------------
    "tbq_lnu_t_tchannel_powheg": "TBbarQtoLNu-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tbq_2q_t_tchannel_powheg": "TBbarQto2Q-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tbq_lnu_tbar_tchannel_powheg": "TbarBQtoLNu-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tbq_2q_tbar_tchannel_powheg": "TbarBQto2Q-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tb_lnub_t_schannel_4fs_amcatnlo": "TBbartoLNu-s-channel_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tb_2q_t_schannel_4fs_amcatnlo": "TBbarto2Q-s-channel_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tb_lnub_tbar_schannel_4fs_amcatnlo": "TbarBtoLNu-s-channel_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tb_2q_tbar_schannel_4fs_amcatnlo": "TbarBto2Q-s-channel_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_2l2nu_t_powheg": "TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_lnu2q_t_powheg": "TWminustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_4q_t_powheg": "TWminusto4Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_2l2nu_tbar_powheg": "TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_lnu2q_tbar_powheg": "TbarWplustoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tw_4q_tbar_powheg": "TbarWplusto4Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- Z + jets production --------------------------------------------------
    "z_2e_m10to50_amcatnlo": "DYto2E-2Jets_Bin-MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2e_m50_0j_amcatnlo": "DYto2E-2Jets_Bin-0J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2e_m50_1j_amcatnlo": "DYto2E-2Jets_Bin-1J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2e_m50_2j_amcatnlo": "DYto2E-2Jets_Bin-2J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2mu_m10to50_amcatnlo": "DYto2Mu-2Jets_Bin-MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2mu_m50_0j_amcatnlo": "DYto2Mu-2Jets_Bin-0J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2mu_m50_1j_amcatnlo": "DYto2Mu-2Jets_Bin-1J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2mu_m50_2j_amcatnlo": "DYto2Mu-2Jets_Bin-2J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2tau_m10to50_amcatnlo": "DYto2Tau-2Jets_Bin-MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2tau_m50_0j_amcatnlo": "DYto2Tau-2Jets_Bin-0J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2tau_m50_1j_amcatnlo": "DYto2Tau-2Jets_Bin-1J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "z_2tau_m50_2j_amcatnlo": "DYto2Tau-2Jets_Bin-2J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- W + jets production --------------------------------------------------
    "w_enu_amcatnlo": "WtoENu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "w_munu_amcatnlo": "WtoMuNu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "w_taunu_amcatnlo": "WtoTauNu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- Diboson production ---------------------------------------------------
    "ww_2l2nu_powheg": "WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "ww_lnu2q_powheg": "WWtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "ww_4q_powheg": "WWto4Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "wz_3lnu_powheg": "WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "wz_lnu2q_powheg": "WZtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "wz_2l2q_powheg": "WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "zz_4l_powheg": "ZZto4L_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "zz_2l2nu_powheg": "ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "zz_2l2q_powheg": "ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "zz_2nu2q_powheg": "ZZto2Nu2Q_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- H -> tau tau production ----------------------------------------------
    "gg_h_2tau_powheg": "GluGluH-Hto2TauUncorrelatedDecay_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # "vbf_h_2tau_powheg": ,  no sample added yet to the sample database
    # --- H -> b b production --------------------------------------------------
    "gg_h_2b_powheg": [
        "GluGluH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8_RunIII2025Summer24NanoAODv15-150X",
        "GluGluH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powhegMINLO-pythia8_RunIII2025Summer24NanoAODv15-150X_ext1",
    ],
    "vbf_h_2b_powheg": [
        "VBFH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
        "VBFH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X_ext1",
    ],
    # --- ttH production -------------------------------------------------------
    "tth_h_2b_powheg": "TTH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    "tth_h_non2b_powheg": "TTH-HtoNon2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-150X",
    # --- HH -> b b tau tau production -----------------------------------------
    "gg_hh_2b2tau_powheg": [
        "GluGluHHto2B2Tau_Par-c2-0p00-kl-1p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-PowhegBugFix",
        "GluGluHHto2B2Tau_Par-c2-0p00-kl-1p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8_RunIII2025Summer24NanoAODv15-PowhegBugFix_ext1",
    ],
    # "vbf_hh_2b2tau": ,  # no sample added yet to the sample database
}


# Add datasets to the campaign
for name, nicks in dataset_nicks.items():
    add_dataset(cpn_2025_nano_v15, name, nicks)

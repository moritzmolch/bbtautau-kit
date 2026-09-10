from order import Analysis, Campaign, Category, UniqueObjectIndex, Variable

from ._util import PI, arange, binning, cat


def get_variables(
    analysis_inst: Analysis,
    campaign_inst: Campaign,
    category_inst: Category,
) -> UniqueObjectIndex:
    # Get the channel of this category
    channel_inst = category_inst.channel

    # Define the variable labels for each channel
    labels = {
        "pt_1": {
            "et": r"Electron $p_{\text{T}}$",
            "mt": r"Muon $p_{\text{T}}$",
            "tt": r"Leading hadronic $\tau$ $p_{\text{T}}$",
            "em": r"Electron $p_{\text{T}}$",
            "ee": r"Leading electron $p_{\text{T}}$",
            "mm": r"Leading muon $p_{\text{T}}$",
        },
        "pt_2": {
            "et": r"Hadronic $\tau$ $p_{\text{T}}$",
            "mt": r"Hadronic $\tau$ $p_{\text{T}}$",
            "tt": r"Subleading hadronic $\tau$ $p_{\text{T}}$",
            "em": r"Muon $p_{\text{T}}$",
            "ee": r"Subleading electron $p_{\text{T}}$",
            "mm": r"Subleading muon $p_{\text{T}}$",
        },
        "eta_1": {
            "et": r"Electron $\eta$",
            "mt": r"Muon $\eta$",
            "tt": r"Leading hadronic $\tau$ $\eta$",
            "em": r"Electron $\eta$",
            "ee": r"Leading electron $\eta$",
            "mm": r"Leading muon $\eta$",
        },
        "eta_2": {
            "et": r"Hadronic $\tau$ $\eta$",
            "mt": r"Hadronic $\tau$ $\eta$",
            "tt": r"Subeading hadronic $\tau$ $\eta$",
            "em": r"Muon $\eta$",
            "ee": r"Subleading electron $\eta$",
            "mm": r"Subleading muon $\eta$",
        },
        "phi_1": {
            "et": r"Electron $\phi$",
            "mt": r"Muon $\phi$",
            "tt": r"Leading hadronic $\tau$ $\phi$",
            "em": r"Electron $\phi$",
            "ee": r"Leading electron $\phi$",
            "mm": r"Leading muon $\phi$",
        },
        "phi_2": {
            "et": r"Hadronic $\tau$ $\phi$",
            "mt": r"Hadronic $\tau$ $\phi$",
            "tt": r"Subeading hadronic $\tau$ $\phi$",
            "em": r"Muon $\phi$",
            "ee": r"Subleading electron $\phi$",
            "mm": r"Subleading muon $\phi$",
        },
        "mass_1": {
            "et": r"Electron mass",
            "mt": r"Muon mass",
            "tt": r"Leading hadronic $\tau$ mass",
            "em": r"Electron mass",
            "ee": r"Leading electron mass",
            "mm": r"Leading muon mass",
        },
        "mass_2": {
            "et": r"Hadronic $\tau$ mass",
            "mt": r"Hadronic $\tau$ mass",
            "tt": r"Subeading hadronic $\tau$ mass",
            "em": r"Muon mass",
            "ee": r"Subleading electron mass",
            "mm": r"Subleading muon mass",
        },
        "iso_1": {
            "et": r"Electron $I_{\text{rel}}^{\text{e}}$",
            "mt": r"Muon $I_{\text{rel}}^{\mu}$",
            "tt": r"Leading hadronic $\tau$ DeepTau vs. jets score",
            "em": r"Electron $I_{\text{rel}}^{\text{e}}$",
            "ee": r"Leading electron $I_{\text{rel}}^{\text{e}}$",
            "mm": r"Leading muon $I_{\text{rel}}^{\mu}$",
        },
        "iso_2": {
            "et": r"Hadronic $\tau$ DeepTau vs. jets score",
            "mt": r"Hadronic $\tau$ DeepTau vs. jets score",
            "tt": r"Subleading hadronic $\tau$ DeepTau vs. jets score",
            "em": r"Muon $I_{\text{rel}}^{\mu}$",
            "ee": r"Subleading electron $I_{\text{rel}}^{\text{e}}$",
            "mm": r"Subleading muon $I_{\text{rel}}^{\mu}$",
        },
        "tau_decaymode_1": {
            "et": "",
            "mt": "",
            "tt": r"Leading hadronic $\tau$ decay mode",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "tau_decaymode_2": {
            "et": r"Hadronic $\tau$ decay mode",
            "mt": r"Hadronic $\tau$ decay mode",
            "tt": r"Subleading hadronic $\tau$ decay mode",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "m_vis": {
            "et": r"Visible di-$\tau$ mass $m_{\text{vis}}$",
            "mt": r"Visible di-$\tau$ mass $m_{\text{vis}}$",
            "tt": r"Visible di-$\tau$ mass $m_{\text{vis}}$",
            "em": r"Dilepton mass $m_{\ell\ell}$",
            "ee": r"Dilepton mass $m_{\ell\ell}$",
            "mm": r"Dilepton mass $m_{\ell\ell}$",
        },
        "pt_vis": {
            "et": r"Visible di-$\tau$ $p_{\text{T}}$",
            "mt": r"Visible di-$\tau$ $p_{\text{T}}$",
            "tt": r"Visible di-$\tau$ $p_{\text{T}}$",
            "em": r"Dilepton $p_{\text{T}}$",
            "ee": r"Dilepton $p_{\text{T}}$",
            "mm": r"Dilepton $p_{\text{T}}$",
        },
        "deltaR_ditaupair": {
            "et": r"$\Delta R(\text{e}, \tau_{\text{h}})$",
            "mt": r"$\Delta R(\mu, \tau_{\text{h}})$",
            "tt": r"$\Delta R(\tau_{\text{h}}^{\text{lead}}, \tau_{\text{h}}^{\text{sub}})$",
            "em": r"$\Delta R(\text{e}, \mu)$",
            "ee": r"$\Delta R(\text{e}^{\text{lead}}, \text{e}^{\text{sub}})$",
            "mm": r"$\Delta R(\mu^{\text{lead}}, \mu^{\text{sub}})$",
        },
        "met": {
            "et": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
            "mt": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
            "tt": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
            "em": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
            "ee": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
            "mm": r"PUPPI MET $p_{\mathrm{T}}^{\mathrm{miss}}$",
        },
        "metphi": {
            "et": r"PUPPI MET $\phi$",
            "mt": r"PUPPI MET $\phi$",
            "tt": r"PUPPI MET $\phi$",
            "em": r"PUPPI MET $\phi$",
            "ee": r"PUPPI MET $\phi$",
            "mm": r"PUPPI MET $\phi$",
        },
        "metSumEt": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Scalar transverse energy sum",
        ),
        "mt_1": {
            "et": r"Transverse mass $m_{\text{T}}(\text{e}, p_{\text{T}}^{\text{miss}})$",
            "mt": r"Transverse mass $m_{\text{T}}(\mu, p_{\text{T}}^{\text{miss}})$",
            "tt": r"Transverse mass $m_{\text{T}}(\tau_{\text{h}}^{\text{lead}}, p_{\text{T}}^{\text{miss}})$",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "mt_2": {
            "et": r"Transverse mass $m_{\text{T}}(\tau_{\text{h}}, p_{\text{T}}^{\text{miss}})$",
            "mt": r"Transverse mass $m_{\text{T}}(\tau_{\text{h}}, p_{\text{T}}^{\text{miss}})$",
            "tt": r"Transverse mass $m_{\text{T}}(\tau_{\text{h}}^{\text{sub}}, p_{\text{T}}^{\text{miss}})$",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "mt_tot": {
            "et": r"Transverse mass $m_{\text{T}}^{\text{tot}}$",
            "mt": r"Transverse mass $m_{\text{T}}^{\text{tot}}$",
            "tt": r"Transverse mass $m_{\text{T}}^{\text{tot}}$",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "jpt_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Leading jet $p_{\text{T}}$"
        ),
        "jpt_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Subleading jet $p_{\text{T}}$",
        ),
        "jeta_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Leading jet $\eta$"
        ),
        "jeta_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Subleading jet $\eta$"
        ),
        "jphi_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Leading jet $\phi$"
        ),
        "jphi_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Subleading jet $\phi$"
        ),
        "jtag_value_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Leading jet b tagging score"
        ),
        "jtag_value_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Subleading jet b tagging score",
        ),
        "mjj": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Leading dijet system mass"
        ),
        "pt_dijet": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Leading dijet system $p_{\text{T}}$",
        ),
        "bpair_pt_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"First b candidate $p_{\text{T}}$",
        ),
        "bpair_pt_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Second b candidate $p_{\text{T}}$",
        ),
        "bpair_eta_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"First b candidate $\eta$"
        ),
        "bpair_eta_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Second b candidate $\eta$"
        ),
        "bpair_phi_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"First b candidate $\phi$"
        ),
        "bpair_phi_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Second b candidate $\phi$"
        ),
        "bpair_btag_value_1": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"First b candidate tagging score",
        ),
        "bpair_btag_value_2": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"Second b candidate tagging score",
        ),
        "bpair_m_inv": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"bb candidate mass"
        ),
        "bpair_pt_dijet": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"bb candidate $p_{\text{T}}$"
        ),
        "bpair_deltaR": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"],
            r"$\Delta R(\text{b}_1, \text{b}_2)$",
        ),
        "mass_tautaubb": {
            "et": r"bb$\tau\tau$ mass (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "mt": r"bb$\tau\tau$ mass (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "tt": r"bb$\tau\tau$ mass (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "pt_tautaubb": {
            "et": r"bb$\tau\tau$ $p_{\text{T}}$ (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "mt": r"bb$\tau\tau$ $p_{\text{T}}$ (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "tt": r"bb$\tau\tau$ $p_{\text{T}}$ (bb+$\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "pt_tautau": {
            "et": r"$\tau\tau$ $p_{\text{T}}$ ($\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "mt": r"$\tau\tau$ $p_{\text{T}}$ ($\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "tt": r"$\tau\tau$ $p_{\text{T}}$ ($\tau\tau$+$\vec{p}_{\text{T}}^{\text{miss}}$)",
            "em": "",
            "ee": "",
            "mm": "",
        },
        "n_jets": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Number of jets"
        ),
        "n_bjets": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"Number of b-tagged jets"
        ),
        "max_score": dict.fromkeys(
            ["et", "mt", "tt", "em", "ee", "mm"], r"NN output score"
        ),
    }

    binnings = {
        "pt_1": {
            "et": cat([0, 32], arange(35, 185, 5)),
            "mt": cat([0, 26], arange(30, 185, 5)),
            "tt": cat([0, 40], arange(50, 190, 10)),
            "em": cat([0, 32], arange(35, 185, 5)),
            "ee": cat([0, 32], arange(35, 185, 5)),
            "mm": cat([0, 26], arange(30, 185, 5)),
        },
        "pt_2": {
            "et": cat([0, 20], arange(30, 185, 5)),
            "mt": cat([0, 20], arange(30, 185, 5)),
            "tt": cat([0, 40], arange(50, 190, 10)),
            "em": cat([0, 26], arange(30, 185, 5)),
            "ee": cat([0, 20], arange(25, 185, 5)),
            "mm": cat([0, 20], arange(25, 185, 5)),
        },
        "eta_1": {
            "et": binning(-2.5, 2.5, 40),
            "mt": binning(-2.4, 2.4, 40),
            "tt": binning(-2.5, 2.5, 20),
            "em": binning(-2.5, 2.5, 40),
            "ee": binning(-2.5, 2.5, 40),
            "mm": binning(-2.4, 2.4, 40),
        },
        "eta_2": {
            "et": binning(-2.5, 2.5, 40),
            "mt": binning(-2.5, 2.5, 40),
            "tt": binning(-2.5, 2.5, 20),
            "em": binning(-2.4, 2.4, 40),
            "ee": binning(-2.5, 2.5, 40),
            "mm": binning(-2.4, 2.4, 40),
        },
        "phi_1": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "phi_2": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "mass_1": {
            "et": binning(0, 0.001, 40),
            "mt": binning(0, 0.2, 40),
            "tt": binning(0, 2, 20),
            "em": binning(0, 0.001, 40),
            "ee": binning(0, 0.001, 40),
            "mm": binning(0, 0.2, 40),
        },
        "mass_2": {
            "et": binning(0, 2, 40),
            "mt": binning(0, 2, 40),
            "tt": binning(0, 2, 20),
            "em": binning(0, 0.2, 40),
            "ee": binning(0, 0.001, 40),
            "mm": binning(0, 0.2, 40),
        },
        "iso_1": {
            "et": arange(0, 0.155, 0.005),
            "mt": arange(0, 0.155, 0.005),
            "tt": arange(0.9, 1.005, 0.005),
            "em": arange(0, 0.155, 0.005),
            "ee": arange(0, 0.155, 0.005),
            "mm": arange(0, 0.155, 0.005),
        },
        "iso_2": {
            "et": arange(0.9, 1.005, 0.005),
            "mt": arange(0.9, 1.005, 0.005),
            "tt": arange(0.9, 1.005, 0.005),
            "em": arange(0, 0.155, 0.005),
            "ee": arange(0, 0.155, 0.005),
            "mm": arange(0, 0.155, 0.005),
        },
        "tau_decaymode_1": {
            "et": [],
            "mt": [],
            "tt": arange(-0.5, 12.5, 1.0),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "tau_decaymode_2": {
            "et": arange(-0.5, 12.5, 1.0),
            "mt": arange(-0.5, 12.5, 1.0),
            "tt": arange(-0.5, 12.5, 1.0),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "m_vis": {
            "et": arange(0, 205, 5),
            "mt": arange(0, 205, 5),
            "tt": arange(0, 210, 10),
            "em": arange(0, 205, 5),
            "ee": arange(0, 205, 5),
            "mm": arange(0, 205, 5),
        },
        "pt_vis": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": arange(0, 185, 5),
            "ee": arange(0, 185, 5),
            "mm": arange(0, 185, 5),
        },
        "deltaR_ditaupair": {
            "et": arange(0, 6.2, 0.2),
            "mt": arange(0, 6.2, 0.2),
            "tt": arange(0, 6.4, 0.4),
            "em": arange(0, 6.2, 0.2),
            "ee": arange(0, 6.2, 0.2),
            "mm": arange(0, 6.2, 0.2),
        },
        "met": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": arange(0, 185, 5),
            "ee": arange(0, 185, 5),
            "mm": arange(0, 185, 5),
        },
        "metphi": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "metSumEt": {
            "et": arange(0, 1010, 10),
            "mt": arange(0, 1010, 10),
            "tt": arange(0, 1020, 20),
            "em": arange(0, 1010, 10),
            "ee": arange(0, 1010, 10),
            "mm": arange(0, 1010, 10),
        },
        "mt_1": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "mt_2": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "mt_tot": {
            "et": arange(0, 410, 10),
            "mt": arange(0, 410, 10),
            "tt": arange(0, 420, 20),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "jpt_1": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": arange(0, 185, 5),
            "ee": arange(0, 185, 5),
            "mm": arange(0, 185, 5),
        },
        "jpt_2": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": arange(0, 185, 5),
            "ee": arange(0, 185, 5),
            "mm": arange(0, 185, 5),
        },
        "jeta_1": {
            "et": binning(-4.7, 4.7, 40),
            "mt": binning(-4.7, 4.7, 40),
            "tt": binning(-4.7, 4.7, 20),
            "em": binning(-4.7, 4.7, 40),
            "ee": binning(-4.7, 4.7, 40),
            "mm": binning(-4.7, 4.7, 40),
        },
        "jeta_2": {
            "et": binning(-4.7, 4.7, 40),
            "mt": binning(-4.7, 4.7, 40),
            "tt": binning(-4.7, 4.7, 20),
            "em": binning(-4.7, 4.7, 40),
            "ee": binning(-4.7, 4.7, 40),
            "mm": binning(-4.7, 4.7, 40),
        },
        "jphi_1": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "jphi_2": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "jtag_value_1": {
            "et": arange(0.0, 1.025, 0.025),
            "mt": arange(0.0, 1.025, 0.025),
            "tt": arange(0.0, 1.05, 0.05),
            "em": arange(0.0, 1.025, 0.025),
            "ee": arange(0.0, 1.025, 0.025),
            "mm": arange(0.0, 1.025, 0.025),
        },
        "jtag_value_2": {
            "et": arange(0.0, 1.025, 0.025),
            "mt": arange(0.0, 1.025, 0.025),
            "tt": arange(0.0, 1.05, 0.05),
            "em": arange(0.0, 1.025, 0.025),
            "ee": arange(0.0, 1.025, 0.025),
            "mm": arange(0.0, 1.025, 0.025),
        },
        "mjj": {
            "et": arange(0, 1050, 50),
            "mt": arange(0, 1050, 50),
            "tt": arange(0, 1100, 100),
            "em": arange(0, 1050, 50),
            "ee": arange(0, 1050, 50),
            "mm": arange(0, 1050, 50),
        },
        "pt_dijet": {
            "et": arange(0, 510, 10),
            "mt": arange(0, 510, 10),
            "tt": arange(0, 520, 20),
            "em": arange(0, 510, 10),
            "ee": arange(0, 510, 10),
            "mm": arange(0, 510, 10),
        },
        "bpair_pt_1": {
            "et": arange(0, 265, 5),
            "mt": arange(0, 265, 5),
            "tt": arange(0, 270, 10),
            "em": arange(0, 265, 5),
            "ee": arange(0, 265, 5),
            "mm": arange(0, 265, 5),
        },
        "bpair_pt_2": {
            "et": arange(0, 265, 5),
            "mt": arange(0, 265, 5),
            "tt": arange(0, 270, 10),
            "em": arange(0, 265, 5),
            "ee": arange(0, 265, 5),
            "mm": arange(0, 265, 5),
        },
        "bpair_eta_1": {
            "et": binning(-2.5, 2.5, 40),
            "mt": binning(-2.5, 2.5, 40),
            "tt": binning(-2.5, 2.5, 20),
            "em": binning(-2.5, 2.5, 40),
            "ee": binning(-2.5, 2.5, 40),
            "mm": binning(-2.5, 2.5, 40),
        },
        "bpair_eta_2": {
            "et": binning(-4.7, 4.7, 40),
            "mt": binning(-4.7, 4.7, 40),
            "tt": binning(-4.7, 4.7, 20),
            "em": binning(-4.7, 4.7, 40),
            "ee": binning(-4.7, 4.7, 40),
            "mm": binning(-4.7, 4.7, 40),
        },
        "bpair_phi_1": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "bpair_phi_2": {
            "et": binning(-PI, PI, 40),
            "mt": binning(-PI, PI, 40),
            "tt": binning(-PI, PI, 20),
            "em": binning(-PI, PI, 40),
            "ee": binning(-PI, PI, 40),
            "mm": binning(-PI, PI, 40),
        },
        "bpair_btag_value_1": {
            "et": arange(0.0, 1.025, 0.025),
            "mt": arange(0.0, 1.025, 0.025),
            "tt": arange(0.0, 1.05, 0.05),
            "em": arange(0.0, 1.025, 0.025),
            "ee": arange(0.0, 1.025, 0.025),
            "mm": arange(0.0, 1.025, 0.025),
        },
        "bpair_btag_value_2": {
            "et": arange(0.0, 1.025, 0.025),
            "mt": arange(0.0, 1.025, 0.025),
            "tt": arange(0.0, 1.05, 0.05),
            "em": arange(0.0, 1.025, 0.025),
            "ee": arange(0.0, 1.025, 0.025),
            "mm": arange(0.0, 1.025, 0.025),
        },
        "bpair_m_inv": {
            "et": arange(0, 1050, 50),
            "mt": arange(0, 1050, 50),
            "tt": arange(0, 1100, 100),
            "em": arange(0, 1050, 50),
            "ee": arange(0, 1050, 50),
            "mm": arange(0, 1050, 50),
        },
        "bpair_pt_dijet": {
            "et": arange(0, 550, 50),
            "mt": arange(0, 550, 50),
            "tt": arange(0, 600, 100),
            "em": arange(0, 550, 50),
            "ee": arange(0, 550, 50),
            "mm": arange(0, 550, 50),
        },
        "bpair_deltaR": {
            "et": arange(0, 6.2, 0.2),
            "mt": arange(0, 6.2, 0.2),
            "tt": arange(0, 6.4, 0.4),
            "em": arange(0, 6.2, 0.2),
            "ee": arange(0, 6.2, 0.2),
            "mm": arange(0, 6.2, 0.2),
        },
        "mass_tautaubb": {
            "et": arange(0, 1010, 10),
            "mt": arange(0, 1010, 10),
            "tt": arange(0, 1020, 20),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "pt_tautaubb": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "pt_tautau": {
            "et": arange(0, 185, 5),
            "mt": arange(0, 185, 5),
            "tt": arange(0, 190, 10),
            "em": [],
            "ee": [],
            "mm": [],
        },
        "n_jets": {
            c: arange(-0.5, 8.5, 1.0)
            for c in ["et", "mt", "tt", "em", "ee", "mm"]
        },
        "n_bjets": {
            c: arange(-0.5, 5.5, 1.0)
            for c in ["et", "mt", "tt", "em", "ee", "mm"]
        },
        "max_score": {
            c: arange(0.0, 1.05, 0.05)
            for c in ["et", "mt", "tt", "em", "ee", "mm"]
        },
    }

    units = {
        "pt_1": "GeV",
        "pt_2": "GeV",
        "eta_1": None,
        "eta_2": None,
        "phi_1": None,
        "phi_2": None,
        "mass_1": "GeV",
        "mass_2": "GeV",
        "iso_1": None,
        "iso_2": None,
        "tau_decaymode_1": None,
        "tau_decaymode_2": None,
        "m_vis": "GeV",
        "pt_vis": "GeV",
        "deltaR_ditaupair": None,
        "met": "GeV",
        "metphi": None,
        "metSumEt": "GeV",
        "mt_1": "GeV",
        "mt_2": "GeV",
        "mt_tot": "GeV",
        "jpt_1": "GeV",
        "jpt_2": "GeV",
        "jeta_1": None,
        "jeta_2": None,
        "jphi_1": None,
        "jphi_2": None,
        "jtag_value_1": None,
        "jtag_value_2": None,
        "mjj": "GeV",
        "pt_dijet": "GeV",
        "bpair_pt_1": "GeV",
        "bpair_pt_2": "GeV",
        "bpair_eta_1": None,
        "bpair_eta_2": None,
        "bpair_phi_1": None,
        "bpair_phi_2": None,
        "bpair_btag_value_1": None,
        "bpair_btag_value_2": None,
        "bpair_m_inv": "GeV",
        "bpair_pt_dijet": "GeV",
        "bpair_deltaR": None,
        "mass_tautaubb": "GeV",
        "pt_tautaubb": "GeV",
        "pt_tautau": "GeV",
        "n_jets": None,
        "n_bjets": None,
        "max_score": None,
    }

    # Fill the index with variable objects generated with the information above
    variable_insts = UniqueObjectIndex(Variable, [])

    for name in labels:
        # If an empty list of bin edges is provided, the variable is not
        # considered for this channel.
        if len(binnings[name][channel_inst.name]) == 0:
            continue

        # Add variable with values given in the dictionaries above.
        variable_insts.add(
            name=name,
            id="+",
            x_title=labels[name][channel_inst.name],
            unit=units[name],
            unit_format="{title} ({unit})",
            binning=binnings[name][channel_inst.name],
        )

    return variable_insts

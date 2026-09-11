from collections import OrderedDict

from xyh.core.wrapper import Wrapper


@Wrapper.wrap
def normalization(self) -> OrderedDict[str, str]:
    """
    Calculate weights to normalize MC histograms to the integrated luminosity
    and the expected theory cross section.
    """

    # Empty storage for new weights
    weights = OrderedDict()

    # TODO make this function dataset-dependent to be able to inject cross
    # section from dataset object.

    # Set the luminosity weight depending on the era
    lumi = self.campaign_inst.x.lumi

    xsec = self.dataset_inst.x.xsec
    generator_weight = self.dataset_inst.x.generator_weight
    n_events = self.dataset_inst.n_events

    # Set normalization, cross section, and lumi weights
    # section value right here
    weights["lumi_weight"] = f"{lumi} * 1000"
    weights["n_gen_weight"] = f"1 / {n_events}"
    weights["gen_weight"] = f"""
        ( 1.0 / {generator_weight}) * (
            (genWeight > 0) - (genWeight < 0)
        )
    """
    weights["xsec_weight"] = f"{xsec}"

    return weights


@Wrapper.wrap
def pileup_weights(self) -> OrderedDict[str, str]:
    """Add pileup weight."""
    return OrderedDict([("pileup_weight", "puweight")])

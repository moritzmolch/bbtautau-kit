"""Write a datacard with CombineHarvester from a JSON spec.

Standalone script: it must not import ``xyh``. Run it inside the CMSSW
environment, in the directory that contains the spec and the input shapes::

    python3 write_datacard.py datacard_spec.json
"""

import json
import sys


def main(spec_file: str) -> None:
    import CombineHarvester.CombineTools.ch as ch

    with open(spec_file) as f:
        spec = json.load(f)

    # "*" makes the datacard mass independent (no mass placeholder in paths)
    mass = ["*"]
    analysis = [spec["analysis"]]

    cb = ch.CombineHarvester()
    for i, b in enumerate(spec["bins"]):
        era, channel = [b["era"]], [b["channel"]]
        cats = [(i, b["name"])]
        cb.AddObservations(mass, analysis, era, channel, cats)
        if b["backgrounds"]:
            cb.AddProcesses(
                mass, analysis, era, channel, b["backgrounds"], cats, False
            )
        if b["signals"]:
            cb.AddProcesses(
                mass, analysis, era, channel, b["signals"], cats, True
            )

    # Systematics from the spec (reserved, none so far)
    for syst in spec.get("systematics", []):
        cb.cp().process(syst["processes"]).AddSyst(
            cb, syst["name"], syst["type"], ch.SystMap()(syst["value"])
        )

    cb.cp().ExtractShapes(
        spec["shapes_in_file"], "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC"
    )

    if spec.get("auto_mc_stats") is not None:
        cb.SetAutoMCStats(cb, spec["auto_mc_stats"])

    cb.WriteDatacard(spec["datacard_file"], spec["shapes_out_file"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_datacard.py <datacard_spec.json>")
    main(sys.argv[1])

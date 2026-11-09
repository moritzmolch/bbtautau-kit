"""Plot the NN scores of all output classes from the shapes of a fit point.

Reads ``shapes.root`` of a mass point directory of the fit stage and draws,
for each campaign and channel, the four output classes next to each other in
one figure. Data is blinded in the signal class ``xyh``.

Usage
-----
    bin/plot_nn_scores --point-dir data/output/fit/<tag>/<scope>/<data_mode>/\\
<decay_mode>/mx<X>_my<Y> --output-dir plots
"""

import argparse
import logging
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--point-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: <point-dir>/plots/nn_scores",
    )
    parser.add_argument("--extensions", nargs="+", default=["png"])
    parser.add_argument(
        "--data-mode",
        default=None,
        help="Default: the name of the grandparent directory of the point",
    )
    parser.add_argument(
        "--inventory-factory-fn",
        default="xyh.config.inventory.create_inventory",
    )
    parser.add_argument("--process-set", default="default")
    parser.add_argument(
        "--profile",
        default="FULL",
        help="XYH_PROFILE, unless set in the environment",
    )
    parser.add_argument("--combine-channels", action="store_true")
    parser.add_argument("--linear-y", action="store_true")
    args = parser.parse_args()

    # The profile defines the signal process groups of the inventory
    os.environ.setdefault("XYH_PROFILE", args.profile)
    logging.basicConfig(level=logging.INFO)

    # Import after the environment is set up
    from xyh.core.plotting.nn_score_plots import plot_nn_scores

    point_dir = args.point_dir.resolve()
    if args.data_mode is not None:
        data_mode = args.data_mode
    else:
        # .../<data_mode>/<decay_mode>/mx<X>_my<Y>
        data_mode = point_dir.parents[1].name

    plot_nn_scores(
        point_dir=point_dir,
        output_dir=args.output_dir or point_dir / "plots" / "nn_scores",
        extensions=args.extensions,
        inventory_factory_fn_path=args.inventory_factory_fn,
        inventory_factory_kwargs={"process_set": args.process_set},
        data_mode=data_mode,
        combine_channels=args.combine_channels,
        log_y=not args.linear_y,
    )


if __name__ == "__main__":
    main()

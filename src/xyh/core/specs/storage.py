from xyh.core.specs.specs import (
    Context,
    Dataset,
    Filter,
    FiltersAndWeights,
    Histogram,
    Weight,
)


class SpecStorage:
    """
    Storage for specifications related to datasets, filters, weights, and
    histograms.

    This class provides an interface to retrieve specifications based on a given
    analysis context.
    """

    def __init__(
        self,
        dataset_specs: list[Dataset],
        filters_and_weights_specs: list[FiltersAndWeights],
        histogram_specs: list[Histogram],
    ):
        self._dataset_specs_lookup = {
            (s.campaign, s.channel, s.dataset): s for s in dataset_specs
        }
        self._filters_specs_lookup = {
            (
                s.campaign,
                s.channel,
                s.category,
                s.dataset,
                s.process,
                s.variation,
            ): s.filters
            for s in filters_and_weights_specs
        }
        self._weights_specs_lookup = {
            (
                s.campaign,
                s.channel,
                s.category,
                s.dataset,
                s.process,
                s.variation,
            ): s.weights
            for s in filters_and_weights_specs
        }
        self._histogram_specs_lookup = {
            (
                s.campaign,
                s.channel,
                s.category,
                s.dataset,
                s.process,
                s.variation,
                s.variable,
            ): s
            for s in histogram_specs
        }

    def get_dataset_spec(self, context: Context) -> Dataset:
        """
        Get dataset specification for a given context.

        The method returns the dataset specification for a given campaign,
        channel, and dataset.

        Parameters
        ----------
        context : Context
            The analysis context.

        Returns
        -------
        Dataset
            The dataset specification corresponding to the given context.
        """

        return self._dataset_specs_lookup[
            (
                context.campaign,
                context.channel,
                context.dataset,
            )
        ]

    def get_filters_specs(self, context: Context) -> list[Filter]:
        """
        Get filter specifications for a given context.

        The method returns the list of filter specifications for a given
        campaign, channel, category, dataset, process, and variation.

        Parameters
        ----------
        context : Context
            The analysis context.

        Returns
        -------
        list[Filter]
            The list of filter specifications corresponding to the given
            context.
        """

        return self._filters_specs_lookup[
            (
                context.campaign,
                context.channel,
                context.category,
                context.dataset,
                context.process,
                context.variation,
            )
        ]

    def get_weights_specs(self, context: Context) -> list[Weight]:
        """
        Get weight specifications for a given context.

        The method returns the list of weight specifications for a given
        campaign, channel, category, dataset, process, and variation.

        Parameters
        ----------
        context : Context
            The analysis context.

        Returns
        -------
        list[Weight]
            The list of weight specifications corresponding to the given
            context.
        """

        return self._weights_specs_lookup[
            (
                context.campaign,
                context.channel,
                context.category,
                context.dataset,
                context.process,
                context.variation,
            )
        ]

    def get_histogram_specs(self, context: Context, variable: str) -> Histogram:
        """
        Get histogram specification for a given context and variable.

        The method returns the histogram specification for a given campaign,
        channel, category, dataset, process, variation, and variable.

        Parameters
        ----------
        context: Context
            The analysis context.

        variable: str
            The variable for which the histogram specification is requested.

        Returns
        -------
        Histogram
            The histogram specification corresponding to the given context and
            variable.
        """

        return self._histogram_specs_lookup[
            (
                context.campaign,
                context.channel,
                context.category,
                context.dataset,
                context.process,
                context.variation,
                variable,
            )
        ]

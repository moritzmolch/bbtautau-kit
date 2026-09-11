from order import (
    Category,
)

from xyh.config.campaigns._util import get_format_string_parameters


class CategoryProxy(Category):
    def __init__(
        self,
        name,
        id,
        channel=None,
        categories=None,
        label=None,
        label_short=None,
        selection=None,
        str_selection_mode=None,
        tags=None,
        aux=None,
    ):
        # Initialize base class
        super().__init__(
            name=name,
            id=id,
            channel=channel,
            categories=categories,
            label=label,
            label_short=label_short,
            selection=selection,
            str_selection_mode=str_selection_mode,
            tags=tags,
            aux=aux,
        )

        # Extract the parameters from the name
        self._parameters = get_format_string_parameters(name)

    def eval(self, **kwargs) -> Category:
        # Check if all required parameters are provided
        missing_parameters = self._parameters - set(kwargs.keys())
        if missing_parameters:
            raise ValueError(
                f"Missing parameters for category '{self.name}': {missing_parameters}"
            )

        return self.copy(name=self.name.format(**kwargs))

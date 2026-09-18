import inspect
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from collections.abc import Callable

# ------------------------------------------------------------------------------
# OrderedDict manipulation functions
# ------------------------------------------------------------------------------


def replace(
    expression_dict: OrderedDict[str, str],
    key_to_replace: str,
    key: str,
    expression: str,
):
    """
    Replace the expression in the expression_dict with the given key_to_replace
    with the new expression and key. If the key_to_replace is not found, raise a
    KeyError.
    """
    # Raise exception if key cannot be found
    if key_to_replace not in expression_dict:
        raise KeyError(f"Key '{key_to_replace}' not found in expression_dict.")

    # Get index of key to replace
    index = list(expression_dict.keys()).index(key_to_replace)

    # Insert the new key and expression at the index of the key to replace
    expression_list = list(expression_dict.items())
    expression_list[index] = (key, expression)
    expression_dict = OrderedDict(expression_list)

    return expression_dict


def append(
    expression_dict: OrderedDict[str, str],
    key: str,
    expression: str,
):
    """
    Append the new expression and key to the end of the expression_dict.

    Parameters
    ----------
    expression_dict : OrderedDict[str, str]
        The dictionary to which the new expression and key will be appended.

    key : str
        The key for the new expression.

    expression : str
        The new expression to be appended.
    """

    # Copy to prevent modifying the original dictionary
    expression_dict = expression_dict.copy()
    expression_dict[key] = expression

    return expression_dict


# ------------------------------------------------------------------------------
# Variation class and class creation
# ------------------------------------------------------------------------------


class BaseVariation(metaclass=ABCMeta):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        # Store the arguments and keyword arguments for later use
        self._args = args
        self._kwargs = kwargs

        # Set the attributes of the instance based on the keyword arguments
        for name, value in kwargs.items():
            setattr(self, name, value)

    def skip(self) -> bool:
        """
        Determine whether to skip the variation given the context of the
        variation object.
        """
        return False

    @abstractmethod
    def apply(
        self,
        filters: OrderedDict[str, str],
        weights: OrderedDict[str, str],
    ) -> tuple[OrderedDict[str, str], OrderedDict[str, str]]:
        """
        Apply the variation to the given expression dictionary.

        The method modifies the nominal `filters` and `weights` expression based
        on the specific variations defined by the subclasses. The modified
        expressions are returned as ordered dictionary as well.

        Parameters
        ----------
        expression_dict : OrderedDict[str, str]
            The dictionary of expressions to which the variation will be applied.

        Returns
        -------
        OrderedDict[str, str], OrderedDict[str, str]
            The modified expression dictionaries for filters and weights after applying the variation.
        """
        return NotImplemented


def variation(
    fn: (
        Callable[
            [BaseVariation, OrderedDict[str, str], OrderedDict[str, str]],
            tuple[OrderedDict[str, str], OrderedDict[str, str]],
        ]
        | None
    ) = None,
    skip_fn: Callable[[BaseVariation], bool] | None = None,
):
    def decorate(func: Callable):
        # Get the first element in the stack, i.e., the module before entering
        # the parent module
        frame = inspect.stack()[1]
        module = inspect.getmodulename(frame.filename)

        # Derive the class name from the function name
        cls_name = func.__name__

        # Create a dictionary to hold the class attributes and methods
        cls_dict = {
            "__module__": module,
            "apply": func,
            "name": cls_name,
        }

        # If a skip function is provided, add it to the class dictionary
        if skip_fn is not None:
            cls_dict["skip"] = skip_fn

        # Define the base classes

        # Create a new subclass
        subcls: type[BaseVariation] = BaseVariation.__class__(
            cls_name,
            (BaseVariation,),
            cls_dict,
        )

        return subcls

    return decorate(fn) if fn is not None else decorate

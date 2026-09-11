import numpy as np
from order import Variable

PI = np.pi


def arange(*args, **kwargs):
    return np.arange(*args, **kwargs).tolist()


def linspace(*args, **kwargs):
    return np.linspace(*args, **kwargs).tolist()


def binning(start, stop, bins):
    return linspace(start, stop, bins + 1, endpoint=True)


def cat(*args, **kwargs):
    if "axis" in kwargs:
        raise ValueError("cat: keyword argument axis not allowed")
    return np.concatenate(args, axis=0, **kwargs).tolist()


def add_variable(
    variables: list[Variable],
    *args,
    **kwargs,
):
    """
    Create a new `Variable` and add it to the list `variables`.

    Parameters
    ----------
    variables : list[Variable]
        List of variables to which the new variable will be added.

    *args:
        Positional arguments to be passed to the `Variable` constructor.

    **kwargs:
        Keyword arguments to be passed to the `Variable` constructor.
    """
    variables.append(Variable(*args, **kwargs))

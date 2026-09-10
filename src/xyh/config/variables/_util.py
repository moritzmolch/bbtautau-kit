import numpy as np

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

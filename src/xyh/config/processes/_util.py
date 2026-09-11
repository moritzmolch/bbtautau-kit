from order import Process


def add_process(
    processes: list[Process],
    *args,
    **kwargs,
):
    """
    Create a new `Process` and add it to the list `processes`.

    Parameters
    ----------
    processes : list[Process]
        List of processes to which the new process will be added.

    *args:
        Positional arguments to be passed to the `Process` constructor.

    **kwargs:
        Keyword arguments to be passed to the `Process` constructor.
    """
    processes.append(Process(*args, **kwargs))

import logging
import multiprocessing
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any


def _capture_logging_config() -> dict[str, Any]:
    """Snapshot the root logger's configuration for replay in workers.

    The configuration is returned as a plain dictionary so that it can be
    pickled and shipped to the worker processes of the process pool.
    """
    root = logging.getLogger()
    config = {"level": root.getEffectiveLevel(), "handlers": []}
    for handler in root.handlers:
        config["handlers"].append(
            {
                "level": handler.level,
                "format": getattr(handler.formatter, "_fmt", None),
                "file": (
                    handler.baseFilename
                    if isinstance(handler, logging.FileHandler)
                    else None
                ),
            }
        )
    return config


def _init_worker_logging(config: dict[str, Any]) -> None:
    """Replay the parent's logging configuration in a spawned worker.

    With the `spawn` multiprocessing context, workers start from a fresh
    interpreter and inherit neither the parent's handlers nor its log level.
    Without this initializer, records emitted by the parallel processing would
    be dropped or printed by the unformatted "handler of last resort".
    """
    root = logging.getLogger()
    root.setLevel(config["level"])
    for handler_config in config["handlers"]:
        if handler_config.get("file"):
            handler: logging.Handler = logging.FileHandler(
                handler_config["file"]
            )
        else:
            handler = logging.StreamHandler()
        handler.setLevel(handler_config["level"])
        if handler_config.get("format"):
            handler.setFormatter(logging.Formatter(handler_config["format"]))
        root.addHandler(handler)


@contextmanager
def _process_pool(max_workers: int, mp_context=None):
    """Context manager around a pool of worker processes.

    ROOT keeps its worker processes alive during interpreter shutdown (e.g. via
    its global state or background threads), so the graceful shutdown triggered
    by `ProcessPoolExecutor.__exit__` can block forever once all tasks have been
    processed. This context manager therefore tears the workers down explicitly
    when the pool is left, while keeping the idiomatic `with` usage.

    The parent's logging configuration is replayed in each worker so that log
    records emitted during parallel processing remain visible.
    """
    if mp_context is None:
        mp_context = multiprocessing.get_context("spawn")
    pool = ProcessPoolExecutor(
        max_workers=max_workers,
        mp_context=mp_context,
        # Replay the parent's logging configuration in each spawned worker so
        # that log records emitted during parallel processing remain visible.
        initializer=_init_worker_logging,
        initargs=(_capture_logging_config(),),
    )
    try:
        yield pool
    finally:
        # Terminate the worker processes explicitly instead of relying on the
        # graceful shutdown of the `with` statement (see docstring).
        pool.shutdown(wait=False, cancel_futures=True)
        process_values = pool._processes
        if process_values is not None:
            for process in process_values.values():
                process.terminate()
            for process in process_values.values():
                process.join()


def run_in_parallel(
    fn: Callable,
    tasks: Iterable,
    num_workers: int,
) -> list[Any]:
    """Execute `fn` on each of the independent `tasks`.

    The tasks are processed in the current process for `num_workers == 1`.
    Otherwise, they are distributed across a pool of worker processes, which
    requires `fn` and the tasks to be picklable since a `spawn` multiprocessing
    context is used. The results are returned in the order the tasks complete.
    """
    if num_workers == 1:
        return [fn(task) for task in tasks]

    with _process_pool(num_workers) as pool:
        futures = [pool.submit(fn, task) for task in tasks]
        return [future.result() for future in as_completed(futures)]

"""Unit tests for the shared parallel processing helpers."""

from contextlib import contextmanager

from xyh.core.parallel import run_in_parallel


def test_run_in_parallel_serial_processes_tasks_in_order():
    tasks = [{"value": i} for i in range(3)]

    results = run_in_parallel(lambda task: task["value"] * 2, tasks, 1)

    assert results == [0, 2, 4]


def test_run_in_parallel_parallel_distributes_over_pool(monkeypatch):
    submitted = {}

    class _SyncPool:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, fn, task):
            from concurrent.futures import Future

            future = Future()
            future.set_result(fn(task))
            return future

    @contextmanager
    def _fake_process_pool(max_workers, mp_context=None):
        submitted["max_workers"] = max_workers
        submitted["mp_context"] = mp_context
        yield _SyncPool()

    monkeypatch.setattr("xyh.core.parallel._process_pool", _fake_process_pool)

    tasks = [{"value": i} for i in range(5)]
    results = run_in_parallel(lambda task: task["value"] + 1, tasks, 3)

    assert sorted(results) == [1, 2, 3, 4, 5]
    assert submitted["max_workers"] == 3
    assert submitted["mp_context"] is None

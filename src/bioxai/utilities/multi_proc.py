import multiprocessing
from collections.abc import Callable
from typing import Any

from bioxai.logger.log import setup_logger

logger = setup_logger()


def run_multiprocessing(
    func: Callable[[Any], Any],
    inputs: list[Any],
    num_workers: int | None = None,
) -> list[Any]:
    """
    Runs a given function in parallel using multiprocessing.

    Args:
        func (Callable): The function to execute in parallel.
        inputs (list[Any]): A list of inputs to process.
        num_workers (int | None): Number of parallel processes. Defaults to available CPU cores.

    Returns:
        list[Any]: A list of results from the function executions.
    """
    num_workers = num_workers or multiprocessing.cpu_count() - 1

    with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(func, inputs)

    return results

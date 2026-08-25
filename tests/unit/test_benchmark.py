from pathlib import Path

import pytest

from rental_platform.benchmark import run_index_benchmark
from rental_platform.config import Settings


@pytest.mark.parametrize("iterations", [0, 2, 51])
def test_benchmark_rejects_unreliable_iteration_counts(iterations: int, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 3 and 50"):
        run_index_benchmark(
            Settings(_env_file=None),
            output_path=tmp_path / "result.json",
            iterations=iterations,
        )

import pytest

from app.limits import plot_limiter, scan_limiter, solve_limiter


@pytest.fixture(autouse=True)
def reset_limiters():
    """Los limitadores son globales: cada test empieza con los contadores a cero."""
    for lim in (scan_limiter, solve_limiter, plot_limiter):
        lim.reset()
    yield
    for lim in (scan_limiter, solve_limiter, plot_limiter):
        lim.reset()

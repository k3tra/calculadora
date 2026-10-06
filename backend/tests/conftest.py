import pytest

from app.limits import scan_limiter, solve_limiter


@pytest.fixture(autouse=True)
def reset_limiters():
    """Los limitadores son globales: cada test empieza con los contadores a cero."""
    scan_limiter.reset()
    solve_limiter.reset()
    yield
    scan_limiter.reset()
    solve_limiter.reset()

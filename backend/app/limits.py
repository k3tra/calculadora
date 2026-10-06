"""Límite de gasto para las rutas que llaman a la API de pago (/api/scan y /api/solve).

Es global, no por IP: detrás del proxy de Next (y de cualquier túnel) el backend siempre ve la misma
dirección, así que un límite por IP no protegería nada. Cada Limiter combina un cupo por minuto y un
tope de peticiones simultáneas; al pasarse responde 429 con Retry-After en vez de encolar.
"""

import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException

from .config import settings


class Limiter:
    def __init__(self, name: str, per_minute: int, max_concurrent: int,
                 clock: Callable[[], float] = time.monotonic):
        self.name = name
        self.per_minute = per_minute
        self.max_concurrent = max_concurrent
        self.clock = clock
        self._hits: deque[float] = deque()
        self._inflight = 0

    def reset(self) -> None:
        self._hits.clear()
        self._inflight = 0

    def acquire(self) -> None:
        # Sin awaits: en el bucle de asyncio esta sección es atómica, no hace falta un lock.
        now = self.clock()
        while self._hits and now - self._hits[0] >= 60:
            self._hits.popleft()
        if self._inflight >= self.max_concurrent:
            raise HTTPException(429, "Hay demasiadas peticiones en curso, espera unos segundos",
                                headers={"Retry-After": "5"})
        if len(self._hits) >= self.per_minute:
            wait = max(1, math.ceil(60 - (now - self._hits[0])))
            raise HTTPException(429, f"Límite de peticiones alcanzado, inténtalo en {wait} s",
                                headers={"Retry-After": str(wait)})
        self._hits.append(now)
        self._inflight += 1

    def release(self) -> None:
        self._inflight = max(0, self._inflight - 1)

    def dependency(self):
        """Dependencia de FastAPI: ocupa un hueco mientras dura la petición."""

        async def dep():
            self.acquire()
            try:
                yield
            finally:
                self.release()

        return dep


scan_limiter = Limiter("scan", settings.scan_per_minute, settings.max_concurrent_scan)
solve_limiter = Limiter("solve", settings.solve_per_minute, settings.max_concurrent_solve)
plot_limiter = Limiter("plot", settings.plot_per_minute, settings.max_concurrent_plot)

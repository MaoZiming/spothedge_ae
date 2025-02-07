import random
import time


class Backoff:
    """Exponential backoff with jittering."""

    MULTIPLIER = 1.6
    JITTER = 0.4

    def __init__(
        self, seed: int, initial_backoff: int = 5, max_backoff_factor: int = 5
    ):
        self._initial = True
        self._backoff = 0.0
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff_factor * self._initial_backoff
        # Use a separate engine to avoid interference with the start index generator.
        self._random_engine = random.Random()
        self._random_engine.seed(int(time.time()) + seed)

    # https://github.com/grpc/grpc/blob/2d4f3c56001cd1e1f85734b2f7c5ce5f2797c38a/doc/connection-backoff.md
    # https://github.com/grpc/grpc/blob/5fc3ff82032d0ebc4bf252a170ebe66aacf9ed9d/src/core/lib/backoff/backoff.cc

    def current_backoff(self) -> float:
        """Backs off once and returns the current backoff in seconds."""
        if self._initial:
            self._initial = False
            self._backoff = min(self._initial_backoff, self._max_backoff)
        else:
            self._backoff = min(self._backoff * self.MULTIPLIER, self._max_backoff)
        self._backoff += self._random_engine.uniform(
            -self.JITTER * self._backoff, self.JITTER * self._backoff
        )
        return self._backoff

"""Browser runtime configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

DEFAULT_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)
DEFAULT_INTERACTION_DELAY_RANGE_SECONDS = (2.0, 5.0)


@dataclass(frozen=True, slots=True)
class BrowserProfile:
    user_agents: tuple[str, ...] = DEFAULT_USER_AGENTS
    interaction_delay_range_seconds: tuple[float, float] = DEFAULT_INTERACTION_DELAY_RANGE_SECONDS

    def __post_init__(self) -> None:
        if not self.user_agents:
            raise ValueError("BrowserProfile requires at least one user agent.")

        lower_bound, upper_bound = self.interaction_delay_range_seconds
        if lower_bound < 0:
            raise ValueError("Interaction delay lower bound cannot be negative.")
        if upper_bound < lower_bound:
            raise ValueError("Interaction delay upper bound must be greater than or equal to the lower bound.")

    def choose_user_agent(self, index: int | None = None) -> str:
        # O(1) selection from a bounded user-agent catalog.
        if index is None:
            return Random().choice(self.user_agents)

        return self.user_agents[index % len(self.user_agents)]

    def sample_interaction_delay(self, random_source: Random | None = None) -> float:
        # O(1) bounded sampling of a single interaction delay value.
        lower_bound, upper_bound = self.interaction_delay_range_seconds
        source = random_source or Random()
        return source.uniform(lower_bound, upper_bound)

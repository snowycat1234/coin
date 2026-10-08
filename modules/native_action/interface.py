"""Stable adapter type for both imported and python -m runner entry points."""
from dataclasses import dataclass
from typing import Callable
from scripts.investment.resumable_perpetual import NativeDailySimulator
from .teacher import DayContext,Mapper,Proposal


@dataclass
class NativeExperiment:
    simulator: NativeDailySimulator
    context_at: Callable[[int],DayContext]
    mapper: Mapper
    baseline_at: Callable[[NativeDailySimulator,DayContext],Proposal] | None=None
    binding: dict | None=None

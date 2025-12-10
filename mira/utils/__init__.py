"""Utility functions for the Mira platform."""
from mira.utils.metrics import (
    get_metrics_collector,
    record_latency,
    increment_error_counter,
    get_latency_stats,
    get_error_count,
    get_all_metrics,
    reset_metrics,
    timer,
    timed
)

__all__ = [
    'get_metrics_collector',
    'record_latency',
    'increment_error_counter',
    'get_latency_stats',
    'get_error_count',
    'get_all_metrics',
    'reset_metrics',
    'timer',
    'timed'
]

"""Deterministic CSV quality contracts; no runtime dependencies."""
from .engine import ConfigError, InputError, evaluate

__all__ = ['ConfigError', 'InputError', 'evaluate']

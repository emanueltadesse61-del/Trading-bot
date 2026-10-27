"""Auditable synthetic runs and pre-registration; real execution is disabled."""

from .descriptor import RunDescriptor, build_generator
from .errors import RegistryError
from .exceptions_file import read_exceptions
from .ops import (
    SUPPORTED_REAL_SCHEMAS,
    register_hypothesis,
    run_registered,
    run_synthetic,
)
from .prereg import parse_preregistration, resolve_descriptors
from .store import init_registry, verify_registry
from .summary import registry_summary

__all__ = [
    "RunDescriptor",
    "build_generator",
    "RegistryError",
    "read_exceptions",
    "SUPPORTED_REAL_SCHEMAS",
    "register_hypothesis",
    "run_registered",
    "run_synthetic",
    "parse_preregistration",
    "resolve_descriptors",
    "init_registry",
    "verify_registry",
    "registry_summary",
]

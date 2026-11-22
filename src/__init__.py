"""Paquete principal del Contador Combinatorio con Funciones Generadoras (Tema 10)."""

from .formal_series import FormalPowerSeries, ntt_convolve_exact, karatsuba_convolve
from .combinatorics_engine import (
    VariableConstraint,
    CombinatorialCounter,
    CountResult,
)

__all__ = [
    "FormalPowerSeries",
    "ntt_convolve_exact",
    "karatsuba_convolve",
    "VariableConstraint",
    "CombinatorialCounter",
    "CountResult",
]

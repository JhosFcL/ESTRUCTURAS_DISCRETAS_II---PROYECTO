"""
Motor de Conteo Combinatorio basado en Funciones Generadoras (Tema 10).

Modela problemas combinatorios clásicos e informáticos mediante la correspondencia
entre operaciones combinatorias (elección independiente, suma de pesos,
permutación etiquetada) y el álgebra de series formales de potencias (FGO y FGE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import math
from typing import Dict, List, Optional, Sequence, Tuple

from .formal_series import FormalPowerSeries, product_tree


@dataclass(frozen=True)
class VariableConstraint:
    """
    Especifica los valores permitidos para una variable entera x_i >= 0 en una
    ecuación combinatoria x_1 + x_2 + ... + x_m = n (o frecuencia de símbolo en FGE).

    Ejemplos:
      - VariableConstraint("x1", min_val=2, max_val=5)          -> {2, 3, 4, 5}
      - VariableConstraint("x2", min_val=0, step=2)             -> pares: {0, 2, 4, ...}
      - VariableConstraint("x3", min_val=1, step=2)             -> impares: {1, 3, 5, ...}
      - VariableConstraint("x4", allowed=(0, 3, 5, 7))          -> conjunto explícito
    """

    name: str
    min_val: int = 0
    max_val: Optional[int] = None
    step: int = 1
    allowed: Optional[Tuple[int, ...]] = None

    def __post_init__(self) -> None:
        if self.allowed is None:
            if self.min_val < 0:
                raise ValueError(f"{self.name}: min_val debe ser >= 0.")
            if self.step <= 0:
                raise ValueError(f"{self.name}: step debe ser >= 1.")
            if self.max_val is not None and self.max_val < self.min_val:
                raise ValueError(f"{self.name}: max_val no puede ser menor que min_val.")
        else:
            if any(v < 0 for v in self.allowed):
                raise ValueError(f"{self.name}: los valores permitidos deben ser >= 0.")

    def exponents_up_to(self, n: int) -> List[int]:
        """Retorna la lista ordenada de exponentes permitidos <= n."""
        if self.allowed is not None:
            return sorted(set(v for v in self.allowed if 0 <= v <= n))
        upper = n if self.max_val is None else min(n, self.max_val)
        if self.min_val > upper:
            return []
        return list(range(self.min_val, upper + 1, self.step))

    def is_arithmetic_progression(self) -> bool:
        """Indica si el factor admite forma cerrada racional x^l (1 - x^{d(q+1)}) / (1 - x^d)."""
        return self.allowed is None

    def symbolic_factor(self, exponential: bool = False) -> str:
        """Representación algebraica simbólica del factor generador."""
        if self.allowed is not None:
            vals = sorted(set(self.allowed))
            if exponential:
                terms = [f"x^{v}/{v}!" if v > 1 else ("x" if v == 1 else "1") for v in vals]
            else:
                terms = [f"x^{v}" if v > 1 else ("x" if v == 1 else "1") for v in vals]
            return "(" + " + ".join(terms) + ")" if terms else "0"

        if exponential:
            if self.max_val is None and self.min_val == 0 and self.step == 1:
                return "e^x"
            if self.max_val is None and self.min_val == 0 and self.step == 2:
                return "cosh(x)"
            if self.max_val is None and self.min_val == 1 and self.step == 2:
                return "sinh(x)"
            upper_str = "inf" if self.max_val is None else str(self.max_val)
            return f"sum_{{k={self.min_val}, step {self.step}}}^{{{upper_str}}} x^k/k!"

        # FGO en forma cerrada racional
        prefix = "" if self.min_val == 0 else ("x" if self.min_val == 1 else f"x^{self.min_val}")
        denom = f"(1 - x)" if self.step == 1 else f"(1 - x^{self.step})"
        if self.max_val is None:
            num = prefix if prefix else "1"
            return f"{num}/{denom}"
        count = (self.max_val - self.min_val) // self.step + 1
        span = count * self.step
        num = f"(1 - x^{span})"
        if prefix:
            num = f"{prefix}{num}"
        return f"{num}/{denom}"


@dataclass
class CountResult:
    """Resultado estructurado de un problema de conteo combinatorio."""

    problem_type: str
    target_n: int
    count: int
    symbolic_gf: str
    series_coeffs: List[int]
    method_used: str
    metadata: Dict[str, object] = field(default_factory=dict)


class CombinatorialCounter:
    """
    Contador Combinatorio basado en Funciones Generadoras Ordinarias (FGO) y
    Funciones Generatrices Exponenciales (FGE).
    """

    def count_constrained_compositions(
        self,
        constraints: Sequence[VariableConstraint],
        target_n: int,
        method: str = "auto",
    ) -> CountResult:
        """
        Cuenta el número de soluciones enteras no negativas de:
            x_1 + x_2 + ... + x_m = target_n
        sujetas a las restricciones individuales en `constraints`.

        Métodos:
          - 'structured': usa operadores racionales O(N) por factor aritmético (óptimo O(m*N)).
          - 'schoolbook': producto de Cauchy clásico O(m*N^2).
          - 'ntt': árbol de productos + convolución exacta NTT+CRT O(m*N log N).
          - 'karatsuba': árbol de productos + Karatsuba.
          - 'auto': elige 'structured' si todas las restricciones son progresiones aritméticas,
                    o 'ntt' con product_tree en caso general.
        """
        if target_n < 0:
            raise ValueError("target_n debe ser >= 0.")

        symbolic = " * ".join(c.symbolic_factor(exponential=False) for c in constraints) or "1"

        use_structured = method == "structured" or (
            method == "auto" and all(c.is_arithmetic_progression() for c in constraints)
        )

        if use_structured and all(c.is_arithmetic_progression() for c in constraints):
            series = self._solve_structured_arithmetic(constraints, target_n)
            used = "structured_rational_O(mN)"
        else:
            effective = "auto" if method in ("auto", "structured") else method
            factors = [
                FormalPowerSeries.from_exponents(c.exponents_up_to(target_n), max_degree=target_n)
                for c in constraints
            ]
            if effective == "schoolbook":
                series = FormalPowerSeries.one(target_n)
                for f in factors:
                    series = series.multiply(f, method="schoolbook")
            else:
                series = product_tree(factors, max_degree=target_n, method=effective)
            used = f"product_{effective}"

        coeffs = [int(v) for v in series.coeffs]
        return CountResult(
            problem_type="constrained_compositions_OGF",
            target_n=target_n,
            count=coeffs[target_n],
            symbolic_gf=symbolic,
            series_coeffs=coeffs,
            method_used=used,
            metadata={"num_variables": len(constraints)},
        )

    def _solve_structured_arithmetic(
        self,
        constraints: Sequence[VariableConstraint],
        target_n: int,
    ) -> FormalPowerSeries:
        """
        Evalúa prod_i x^{l_i} * (1 - x^{d_i(q_i+1)}) / (1 - x^{d_i}) en O(m * N) exacto.
        """
        shift = sum(c.min_val for c in constraints)
        if shift > target_n:
            return FormalPowerSeries.zero(target_n)

        rem = target_n - shift
        series = FormalPowerSeries.one(rem)
        for c in constraints:
            # Dividir por (1 - x^{step})
            series = series.div_one_minus_monomial(1, c.step)
            # Si tiene límite superior, multiplicar por (1 - x^{count * step})
            if c.max_val is not None:
                count = (c.max_val - c.min_val) // c.step + 1
                span = count * c.step
                if span <= rem:
                    series = series.mul_binomial_factor(-1, span)

        shifted_coeffs = [0] * shift + [int(v) for v in series.coeffs]
        return FormalPowerSeries(shifted_coeffs, max_degree=target_n)

    def count_coin_change(
        self,
        denominations: Sequence[int],
        target_amount: int,
        limits: Optional[Sequence[Optional[int]]] = None,
        method: str = "structured",
    ) -> CountResult:
        """
        Cuenta el número de formas de representar `target_amount` usando monedas con
        denominaciones `denominations` y stock opcional `limits` (None = ilimitado).

        FGO: G(x) = prod_i (1 - x^{d_i (q_i + 1)}) / (1 - x^{d_i})  (o 1/(1 - x^{d_i}) si q_i=None)
        """
        if target_amount < 0:
            raise ValueError("target_amount debe ser >= 0.")
        if any(d <= 0 for d in denominations):
            raise ValueError("Todas las denominaciones deben ser enteros positivos.")
        if limits is not None and len(limits) != len(denominations):
            raise ValueError("limits debe tener la misma longitud que denominations.")

        constraints: List[VariableConstraint] = []
        for idx, d in enumerate(denominations):
            lim = None if limits is None else limits[idx]
            max_val = None if lim is None else d * lim
            constraints.append(
                VariableConstraint(
                    name=f"coin_{d}",
                    min_val=0,
                    max_val=max_val,
                    step=d,
                )
            )
        res = self.count_constrained_compositions(constraints, target_amount, method=method)
        res.problem_type = "coin_change_OGF"
        res.metadata["denominations"] = list(denominations)
        res.metadata["limits"] = list(limits) if limits is not None else None
        return res

    def count_partitions(
        self,
        n: int,
        variant: str = "unrestricted",
        max_part: Optional[int] = None,
    ) -> CountResult:
        """
        Cuenta particiones de un entero n mediante productos infinitos truncados de Euler:
          - 'unrestricted': prod_{k=1}^{K} 1 / (1 - x^k)
          - 'distinct':     prod_{k=1}^{K} (1 + x^k)
          - 'odd':          prod_{k impar <= K} 1 / (1 - x^k)
        """
        if n < 0:
            raise ValueError("n debe ser >= 0.")
        k_max = n if max_part is None else min(n, max_part)
        series = FormalPowerSeries.one(n)

        if variant == "unrestricted":
            for k in range(1, k_max + 1):
                series = series.div_one_minus_monomial(1, k)
            sym = f"prod_{{k=1}}^{{{k_max}}} 1/(1 - x^k)"
        elif variant == "distinct":
            for k in range(1, k_max + 1):
                series = series.mul_binomial_factor(1, k)
            sym = f"prod_{{k=1}}^{{{k_max}}} (1 + x^k)"
        elif variant == "odd":
            for k in range(1, k_max + 1, 2):
                series = series.div_one_minus_monomial(1, k)
            sym = f"prod_{{k impar <= {k_max}}} 1/(1 - x^k)"
        else:
            raise ValueError(f"Variante de partición desconocida: {variant}")

        coeffs = [int(v) for v in series.coeffs]
        return CountResult(
            problem_type=f"integer_partitions_{variant}",
            target_n=n,
            count=coeffs[n],
            symbolic_gf=sym,
            series_coeffs=coeffs,
            method_used="euler_product_O(n^2)",
            metadata={"variant": variant, "max_part": k_max},
        )

    def count_restricted_permutations_egf(
        self,
        symbol_constraints: Sequence[VariableConstraint],
        length_n: int,
    ) -> CountResult:
        """
        Cuenta el número de palabras/secuencias ordenadas de longitud `length_n`
        sobre m símbolos distinguibles donde el símbolo i aparece c_i veces según
        su restricción en `symbol_constraints`.

        FGE: A(x) = prod_{i=1}^m ( sum_{c in S_i} x^c / c! ),  a_n = n! * [x^n] A(x).
        """
        if length_n < 0:
            raise ValueError("length_n debe ser >= 0.")

        symbolic = " * ".join(c.symbolic_factor(exponential=True) for c in symbol_constraints) or "1"
        factors = [
            FormalPowerSeries.from_exponents(
                c.exponents_up_to(length_n),
                max_degree=length_n,
                exponential=True,
            )
            for c in symbol_constraints
        ]
        series = FormalPowerSeries.one(length_n, rational=True)
        for f in factors:
            series = series.multiply(f, method="schoolbook")

        counts: List[int] = []
        fact = 1
        for k in range(length_n + 1):
            if k > 0:
                fact *= k
            val = series.coeffs[k] * fact
            assert isinstance(val, Fraction) and val.denominator == 1, "El coeficiente FGE * k! debe ser entero."
            counts.append(val.numerator)

        return CountResult(
            problem_type="restricted_permutations_EGF",
            target_n=length_n,
            count=counts[length_n],
            symbolic_gf=symbolic,
            series_coeffs=counts,
            method_used="EGF_exact_Q[[x]]",
            metadata={"num_symbols": len(symbol_constraints)},
        )

    def expand_rational_gf(
        self,
        numerator: Sequence[int],
        denominator: Sequence[int],
        max_degree: int,
    ) -> CountResult:
        """
        Expande una función generatriz racional G(x) = P(x) / Q(x) hasta grado max_degree.
        Útil para verificar relaciones de recurrencia lineales y funciones cerradas.
        """
        p = FormalPowerSeries(numerator, max_degree=max_degree)
        q = FormalPowerSeries(denominator, max_degree=max_degree)
        g = p.divide(q)
        coeffs = [int(v) if not isinstance(v, Fraction) or v.denominator == 1 else v for v in g.coeffs]
        return CountResult(
            problem_type="rational_GF_expansion",
            target_n=max_degree,
            count=int(coeffs[max_degree]),
            symbolic_gf=f"({p.pretty()}) / ({q.pretty()})",
            series_coeffs=[int(v) for v in coeffs],
            method_used="formal_series_inversion",
            metadata={"numerator": list(numerator), "denominator": list(denominator)},
        )


def exact_stars_and_bars(num_vars: int, total: int, lower_bounds: Optional[Sequence[int]] = None) -> int:
    """Fórmula cerrada analítica C(n' + m - 1, m - 1) cuando solo hay cotas inferiores."""
    shift = sum(lower_bounds) if lower_bounds else 0
    rem = total - shift
    if rem < 0 or num_vars <= 0:
        return 0
    return math.comb(rem + num_vars - 1, num_vars - 1)


def exact_bounded_inclusion_exclusion(num_vars: int, total: int, upper_bound: int) -> int:
    """
    Fórmula cerrada mediante Principio de Inclusión-Exclusión para
    x_1 + ... + x_m = total con 0 <= x_i <= upper_bound (idéntico en todas las variables):
      sum_{j=0}^{m} (-1)^j C(m, j) C(total - j*(u+1) + m - 1, m - 1).
    """
    if total < 0 or num_vars <= 0 or upper_bound < 0:
        return 0
    acc = 0
    step = upper_bound + 1
    for j in range(num_vars + 1):
        rem = total - j * step
        if rem < 0:
            break
        term = math.comb(num_vars, j) * math.comb(rem + num_vars - 1, num_vars - 1)
        acc += -term if (j % 2 == 1) else term
    return acc

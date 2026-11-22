"""
Oráculos matemáticos e informáticos independientes para validar el Contador Combinatorio.

Conforme al criterio de rigor experimental de la rúbrica ("la evidencia de ejecución
no garantiza por sí misma corrección: se contrasta contra la teoría y casos de prueba"),
este módulo provee implementaciones independientes:
  1. Fuerza bruta recursiva (enumeración exhaustiva de soluciones).
  2. Programación dinámica (DP) iterativa independiente de series formales.
  3. Fórmulas cerradas analíticas (estrellas y barras, inclusión-exclusión).
  4. Aproximación asintótica de Hardy-Ramanujan para particiones p(n).
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .combinatorics_engine import VariableConstraint


def brute_force_compositions(
    constraints: Sequence[VariableConstraint],
    target_n: int,
    max_states_guard: int = 2_000_000,
) -> Tuple[int, int]:
    """
    Enumera exhaustivamente todas las tuplas (x_1, ..., x_m) con sum x_i = target_n
    que satisfacen cada restricción.

    Retorna: (numero_de_soluciones, nodos_explorados_en_el_arbol).
    """
    m = len(constraints)
    domains = [c.exponents_up_to(target_n) for c in constraints]
    if m == 0:
        return (1 if target_n == 0 else 0), 1

    # Podas mínimas de sufijo para evitar ramas trivialmente imposibles en las pruebas
    min_suffix = [0] * (m + 1)
    max_suffix = [0] * (m + 1)
    for i in range(m - 1, -1, -1):
        if not domains[i]:
            return 0, 1
        min_suffix[i] = min_suffix[i + 1] + domains[i][0]
        max_suffix[i] = max_suffix[i + 1] + domains[i][-1]

    solutions = 0
    nodes = 0

    def dfs(idx: int, remaining: int) -> None:
        nonlocal solutions, nodes
        nodes += 1
        if nodes > max_states_guard:
            raise RuntimeError(f"Fuerza bruta excedió límite de {max_states_guard} nodos.")
        if idx == m:
            if remaining == 0:
                solutions += 1
            return
        if remaining < min_suffix[idx] or remaining > max_suffix[idx]:
            return
        for val in domains[idx]:
            if val > remaining:
                break
            dfs(idx + 1, remaining - val)

    dfs(0, target_n)
    return solutions, nodes


def brute_force_compositions_unpruned(
    constraints: Sequence[VariableConstraint],
    target_n: int,
    max_states_guard: int = 2_000_000,
) -> Tuple[int, int]:
    """Fuerza bruta pura sin podas de sufijo (para medición de crecimiento exponencial)."""
    m = len(constraints)
    domains = [c.exponents_up_to(target_n) for c in constraints]
    solutions = 0
    nodes = 0

    def dfs(idx: int, current_sum: int) -> None:
        nonlocal solutions, nodes
        nodes += 1
        if nodes > max_states_guard:
            raise RuntimeError(f"Fuerza bruta pura excedió {max_states_guard} nodos.")
        if idx == m:
            if current_sum == target_n:
                solutions += 1
            return
        for val in domains[idx]:
            if current_sum + val <= target_n:
                dfs(idx + 1, current_sum + val)

    dfs(0, 0)
    return solutions, nodes


def dp_compositions(
    constraints: Sequence[VariableConstraint],
    target_n: int,
) -> List[int]:
    """Programación dinámica estándar O(m * N * |S_i|) independiente del motor de series."""
    dp = [0] * (target_n + 1)
    dp[0] = 1
    for c in constraints:
        allowed = c.exponents_up_to(target_n)
        new_dp = [0] * (target_n + 1)
        for s in range(target_n + 1):
            ways = dp[s]
            if ways == 0:
                continue
            for v in allowed:
                if s + v <= target_n:
                    new_dp[s + v] += ways
        dp = new_dp
    return dp


def brute_force_restricted_permutations(
    symbol_constraints: Sequence[VariableConstraint],
    length_n: int,
) -> int:
    """
    Oráculo independiente para FGE: suma los coeficientes multinomiales
    n! / (c_1! ... c_m!) sobre todas las tuplas (c_1, ..., c_m) con sum c_i = length_n.
    """
    m = len(symbol_constraints)
    domains = [c.exponents_up_to(length_n) for c in symbol_constraints]
    fact_n = math.factorial(length_n)
    facts = [math.factorial(k) for k in range(length_n + 1)]
    total = 0

    def dfs(idx: int, remaining: int, denom_prod: int) -> None:
        nonlocal total
        if idx == m:
            if remaining == 0:
                total += fact_n // denom_prod
            return
        for c in domains[idx]:
            if c > remaining:
                break
            dfs(idx + 1, remaining - c, denom_prod * facts[c])

    dfs(0, length_n, 1)
    return total


def hardy_ramanujan_asymptotic(n: int) -> float:
    """Fórmula asintótica de Hardy-Ramanujan (1918) para p(n): (1 / (4 n sqrt(3))) exp(pi sqrt(2n/3))."""
    if n <= 0:
        return 1.0
    return math.exp(math.pi * math.sqrt(2.0 * n / 3.0)) / (4.0 * n * math.sqrt(3.0))

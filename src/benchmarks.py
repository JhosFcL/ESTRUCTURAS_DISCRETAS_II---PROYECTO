"""
Suite reproducible de experimentos y benchmarks para el informe técnico (Tema 10).

Ejecuta mediciones empíricas reales de tiempo de ejecución, precisión exacta
frente a oráculos matemáticos y escalabilidad asintótica, guardando los resultados
en results/benchmark_results.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List

from .combinatorics_engine import (
    CombinatorialCounter,
    VariableConstraint,
    exact_bounded_inclusion_exclusion,
)
from .formal_series import FormalPowerSeries
from .validators import (
    brute_force_compositions,
    brute_force_restricted_permutations,
    dp_compositions,
    hardy_ramanujan_asymptotic,
)


def _time_callable(fn, repeats: int = 3) -> float:
    """Retorna el menor tiempo (en milisegundos) entre `repeats` ejecuciones."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        dt = (time.perf_counter() - t0) * 1000.0
        if dt < best:
            best = dt
    return best


def run_all_benchmarks(output_path: Path | None = None) -> Dict[str, Any]:
    """Ejecuta todos los experimentos del proyecto y opcionalmente los guarda en JSON."""
    counter = CombinatorialCounter()
    results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Experimento 1: Multiplicación de dos series densas (O(N^2) vs Karatsuba vs NTT)
    # ------------------------------------------------------------------
    poly_sizes = [64, 128, 256, 512, 1024, 2048, 4096]
    exp1_rows: List[Dict[str, Any]] = []
    for n in poly_sizes:
        a = FormalPowerSeries([(k % 7) + 1 for k in range(n + 1)], max_degree=n)
        b = FormalPowerSeries([((3 * k + 1) % 11) + 1 for k in range(n + 1)], max_degree=n)

        t_school = _time_callable(lambda: a.multiply(b, method="schoolbook"), repeats=3 if n <= 1024 else 1)
        t_kara = _time_callable(lambda: a.multiply(b, method="karatsuba"), repeats=3 if n <= 1024 else 1)
        t_ntt = _time_callable(lambda: a.multiply(b, method="ntt"), repeats=3 if n <= 1024 else 1)

        # Verificación exacta de igualdad de los tres métodos
        r_s = a.multiply(b, method="schoolbook")
        r_k = a.multiply(b, method="karatsuba")
        r_n = a.multiply(b, method="ntt")
        assert r_s.coeffs == r_k.coeffs == r_n.coeffs, f"Discrepancia en N={n}"

        exp1_rows.append(
            {
                "N": n,
                "schoolbook_ms": round(t_school, 3),
                "karatsuba_ms": round(t_kara, 3),
                "ntt_ms": round(t_ntt, 3),
                "speedup_ntt_vs_schoolbook": round(t_school / t_ntt, 2) if t_ntt > 0 else 0.0,
                "exact_match": True,
            }
        )
    results["exp1_series_multiplication"] = exp1_rows

    # ------------------------------------------------------------------
    # Experimento 2: Fuerza bruta vs DP vs FGO (schoolbook, NTT, estructurada)
    # Problema: x_1 + x_2 + x_3 + x_4 + x_5 + x_6 = N
    # con restricciones realistas de asignación de cargas en 6 nodos de cómputo
    # ------------------------------------------------------------------
    m_vars = 6
    exp2_ns = [10, 16, 22, 28, 34, 60, 120, 250, 500, 1000]
    exp2_rows: List[Dict[str, Any]] = []
    for n in exp2_ns:
        # Cota superior proporcional u = max(6, n // 3) para evidenciar O(mN) vs O(mN^2)
        u = max(6, n // 3)
        constraints = [
            VariableConstraint(f"nodo_{i+1}", min_val=0, max_val=u, step=1)
            for i in range(m_vars)
        ]

        exact_ie = exact_bounded_inclusion_exclusion(m_vars, n, u)
        res_struct = counter.count_constrained_compositions(constraints, n, method="structured")
        assert res_struct.count == exact_ie

        t_struct = _time_callable(
            lambda: counter.count_constrained_compositions(constraints, n, method="structured"),
            repeats=5 if n <= 250 else 3,
        )
        t_ntt = _time_callable(
            lambda: counter.count_constrained_compositions(constraints, n, method="ntt"),
            repeats=3 if n <= 250 else 2,
        )
        t_school = _time_callable(
            lambda: counter.count_constrained_compositions(constraints, n, method="schoolbook"),
            repeats=3 if n <= 250 else 1,
        )
        t_dp = _time_callable(
            lambda: dp_compositions(constraints, n),
            repeats=3 if n <= 250 else 1,
        )

        # Fuerza bruta solo hasta N <= 34 para evitar tiempos imprácticos
        bf_ms = None
        bf_nodes = None
        if n <= 34:
            t0 = time.perf_counter()
            bf_count, bf_nodes = brute_force_compositions(constraints, n, max_states_guard=5_000_000)
            bf_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            assert bf_count == exact_ie

        exp2_rows.append(
            {
                "N": n,
                "upper_bound": u,
                "exact_count": exact_ie,
                "brute_force_ms": bf_ms,
                "brute_force_nodes": bf_nodes,
                "dp_ms": round(t_dp, 3),
                "ogf_schoolbook_ms": round(t_school, 3),
                "ogf_ntt_ms": round(t_ntt, 3),
                "ogf_structured_ms": round(t_struct, 3),
            }
        )
    results["exp2_scalability_methods"] = exp2_rows

    # ------------------------------------------------------------------
    # Experimento 3: Distribución exacta de configuraciones de 5 servidores
    # Restricciones heterogéneas (mínimo, máximo, paridad, lotes de 3)
    # ------------------------------------------------------------------
    cluster_constraints = [
        VariableConstraint("S1_api", min_val=1, max_val=8, step=1),        # 1..8
        VariableConstraint("S2_worker", min_val=0, max_val=10, step=2),    # pares 0,2,4,6,8,10
        VariableConstraint("S3_gpu", min_val=1, max_val=9, step=2),        # impares 1,3,5,7,9
        VariableConstraint("S4_batch", min_val=0, max_val=12, step=3),     # múltiplos de 3: 0,3,6,9,12
        VariableConstraint("S5_cache", min_val=2, max_val=6, step=1),      # 2..6
    ]
    max_load = 45
    res_cluster = counter.count_constrained_compositions(cluster_constraints, max_load, method="structured")
    dp_cluster = dp_compositions(cluster_constraints, max_load)
    assert res_cluster.series_coeffs == dp_cluster

    # También comparamos con el caso sin cotas superiores ni pasos (solo 5 servidores con >= 0)
    unconstrained = [VariableConstraint(f"S{i+1}", min_val=0) for i in range(5)]
    res_unconstrained = counter.count_constrained_compositions(unconstrained, max_load, method="structured")

    results["exp3_cluster_distribution"] = {
        "symbolic_gf": res_cluster.symbolic_gf,
        "max_n": max_load,
        "restricted_coeffs": res_cluster.series_coeffs,
        "unrestricted_coeffs": res_unconstrained.series_coeffs,
        "peak_n": max(range(max_load + 1), key=lambda k: res_cluster.series_coeffs[k]),
        "peak_value": max(res_cluster.series_coeffs),
        "sum_all_configs": sum(res_cluster.series_coeffs),
        "theoretical_total_configs": 8 * 6 * 5 * 5 * 5,  # |S1|*|S2|*|S3|*|S4|*|S5| = G(1)
    }

    # ------------------------------------------------------------------
    # Experimento 4: Particiones de Euler (0..60) y verificación p_dist(n) = p_odd(n)
    # ------------------------------------------------------------------
    max_part_n = 60
    p_all = counter.count_partitions(max_part_n, variant="unrestricted")
    p_dist = counter.count_partitions(max_part_n, variant="distinct")
    p_odd = counter.count_partitions(max_part_n, variant="odd")
    assert p_dist.series_coeffs == p_odd.series_coeffs, "Fallo en identidad de Euler!"

    part_rows = []
    for n in range(0, max_part_n + 1):
        pn = p_all.series_coeffs[n]
        hr = hardy_ramanujan_asymptotic(n) if n > 0 else 1.0
        rel_err = abs(hr - pn) / pn * 100.0 if n > 0 else 0.0
        part_rows.append(
            {
                "n": n,
                "p_n": pn,
                "p_distinct": p_dist.series_coeffs[n],
                "p_odd": p_odd.series_coeffs[n],
                "euler_identity_holds": p_dist.series_coeffs[n] == p_odd.series_coeffs[n],
                "hardy_ramanujan": round(hr, 2),
                "hr_rel_error_pct": round(rel_err, 2),
            }
        )
    results["exp4_euler_partitions"] = part_rows

    # ------------------------------------------------------------------
    # Experimento 5: Cambio de moneda (Euro 100c y Sol peruano) + FGE de códigos
    # ------------------------------------------------------------------
    euro_denoms = [1, 2, 5, 10, 20, 50, 100]
    euro_100 = counter.count_coin_change(euro_denoms, 100)
    peru_denoms = [10, 20, 50, 100, 200, 500]  # en céntimos (S/0.10 a S/5.00)
    peru_500 = counter.count_coin_change(peru_denoms, 500)
    peru_500_limited = counter.count_coin_change(peru_denoms, 500, limits=[10, 8, 5, 4, 2, 1])

    # FGE: claves de longitud n sobre {A, B, C, D} donde A aparece >=1, B par, C <= 3, D libre
    egf_constraints = [
        VariableConstraint("A", min_val=1),
        VariableConstraint("B", min_val=0, step=2),
        VariableConstraint("C", min_val=0, max_val=3),
        VariableConstraint("D", min_val=0),
    ]
    egf_res = counter.count_restricted_permutations_egf(egf_constraints, 10)
    egf_oracle = [brute_force_restricted_permutations(egf_constraints, k) for k in range(11)]
    assert egf_res.series_coeffs == egf_oracle

    results["exp5_applications"] = {
        "euro_100c_ways": euro_100.count,
        "euro_symbolic_gf": euro_100.symbolic_gf,
        "peru_5soles_unlimited_ways": peru_500.count,
        "peru_5soles_limited_ways": peru_500_limited.count,
        "egf_symbolic": egf_res.symbolic_gf,
        "egf_counts_0_to_10": egf_res.series_coeffs,
        "egf_oracle_match": True,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    return results


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "results" / "benchmark_results.json"
    data = run_all_benchmarks(out)
    print(f"Benchmarks completados y guardados en: {out}")
    print(f"  - Euro (100 centimos, 7 monedas): {data['exp5_applications']['euro_100c_ways']} formas")
    print(f"  - S/ 5.00 ilimitado: {data['exp5_applications']['peru_5soles_unlimited_ways']} formas")
    print(f"  - S/ 5.00 stock limitado: {data['exp5_applications']['peru_5soles_limited_ways']} formas")
    print(f"  - p(60) = {data['exp4_euler_partitions'][60]['p_n']}, p_dist(60) = {data['exp4_euler_partitions'][60]['p_distinct']}")

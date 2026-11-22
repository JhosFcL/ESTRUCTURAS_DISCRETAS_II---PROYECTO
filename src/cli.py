"""
Interfaz de Línea de Comandos (CLI) del Contador Combinatorio con Funciones Generadoras.

Ejemplos de uso:
  python3 -m src.cli demo
  python3 -m src.cli coins --denoms 1,2,5,10,20,50,100 --target 100
  python3 -m src.cli compose --specs "1:8:1,0:10:2,1:9:2,0:12:3,2:6:1" --target 20 --verify
  python3 -m src.cli partitions --n 50 --variant all
  python3 -m src.cli benchmark
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time
from typing import List, Optional

from .benchmarks import run_all_benchmarks
from .combinatorics_engine import CombinatorialCounter, VariableConstraint
from .validators import brute_force_compositions, dp_compositions


def _parse_spec(token: str, idx: int) -> VariableConstraint:
    """
    Parsea una restricción en formato 'min:max:step' (usar '-' o '' para max infinito)
    o conjunto explícito '{0,3,5}'.
    """
    tok = token.strip()
    if tok.startswith("{") and tok.endswith("}"):
        vals = tuple(int(v.strip()) for v in tok[1:-1].split(",") if v.strip())
        return VariableConstraint(name=f"x_{idx+1}", allowed=vals)

    parts = tok.split(":")
    min_v = int(parts[0]) if len(parts) >= 1 and parts[0] else 0
    max_v: Optional[int] = None
    if len(parts) >= 2 and parts[1] not in ("", "-", "inf"):
        max_v = int(parts[1])
    step = int(parts[2]) if len(parts) >= 3 and parts[2] else 1
    return VariableConstraint(name=f"x_{idx+1}", min_val=min_v, max_val=max_v, step=step)


def cmd_demo() -> None:
    counter = CombinatorialCounter()
    print("=" * 76)
    print("  CONTADOR COMBINATORIO CON FUNCIONES GENERADORAS — ESTRUCTURAS DISCRETAS II")
    print("=" * 76)

    # Caso 1: Cambio de 1 Euro (ejemplo de la diapositiva 4 del curso)
    euro = counter.count_coin_change([1, 2, 5, 10, 20, 50, 100], 100)
    print("\n[1] Cambio de 1 Euro (100 céntimos) con {1, 2, 5, 10, 20, 50, 100}:")
    print(f"    FGO simbólica : G(x) = {euro.symbolic_gf}")
    print(f"    [x^100] G(x)  : {euro.count:,} formas distintas")

    # Caso 2: Asignación de tareas en 5 servidores con restricciones heterogéneas
    cluster = [
        VariableConstraint("S1_api", min_val=1, max_val=8, step=1),
        VariableConstraint("S2_worker", min_val=0, max_val=10, step=2),
        VariableConstraint("S3_gpu", min_val=1, max_val=9, step=2),
        VariableConstraint("S4_batch", min_val=0, max_val=12, step=3),
        VariableConstraint("S5_cache", min_val=2, max_val=6, step=1),
    ]
    t0 = time.perf_counter()
    res_c = counter.count_constrained_compositions(cluster, 20, method="structured")
    t_fg = (time.perf_counter() - t0) * 1000
    bf_cnt, bf_nodes = brute_force_compositions(cluster, 20)
    dp_cnt = dp_compositions(cluster, 20)[20]
    print("\n[2] Asignación de n=20 tareas en 5 servidores con restricciones heterogéneas:")
    print(f"    FGO simbólica : G(x) = {res_c.symbolic_gf}")
    print(f"    Conteo FGO    : {res_c.count:,} ({t_fg:.3f} ms)")
    print(f"    Oráculo DP    : {dp_cnt:,}  |  Fuerza bruta: {bf_cnt:,} ({bf_nodes:,} nodos)")
    print(f"    Validación    : {'EXACTA' if res_c.count == dp_cnt == bf_cnt else 'ERROR'}")

    # Caso 3: Particiones de Euler (verificación p_distintas = p_impares)
    p_all = counter.count_partitions(30, "unrestricted")
    p_dist = counter.count_partitions(30, "distinct")
    p_odd = counter.count_partitions(30, "odd")
    print("\n[3] Particiones de enteros para n = 30 (Teorema de Euler):")
    print(f"    p(30)           = {p_all.count:,}")
    print(f"    p_distintas(30) = {p_dist.count:,}")
    print(f"    p_impares(30)   = {p_odd.count:,}  (Identidad Euler: {p_dist.series_coeffs == p_odd.series_coeffs})")

    # Caso 4: FGE para códigos alfanuméricos restringidos
    egf_c = [
        VariableConstraint("A", min_val=1),
        VariableConstraint("B", min_val=0, step=2),
        VariableConstraint("C", min_val=0, max_val=3),
        VariableConstraint("D", min_val=0),
    ]
    egf_r = counter.count_restricted_permutations_egf(egf_c, 8)
    print("\n[4] Palabras de longitud n = 8 sobre {A,B,C,D} (A>=1, B par, C<=3, D libre) vía FGE:")
    print(f"    FGE simbólica : A(x) = {egf_r.symbolic_gf}")
    print(f"    8! [x^8] A(x) : {egf_r.count:,} secuencias válidas")

    # Caso 5: Resolución de recurrencia de la Práctica 14 (Ejercicio 14: a_k = 5a_{k-1} - 6a_{k-2}, a_0=6, a_1=30)
    # G(x) = 6 / (1 - 5x + 6x^2) = 18/(1 - 3x) - 12/(1 - 2x) -> a_k = 18*3^k - 12*2^k
    rec = counter.expand_rational_gf([6], [1, -5, 6], max_degree=8)
    closed = [18 * (3**k) - 12 * (2**k) for k in range(9)]
    print("\n[5] Verificación de recurrencia racional G(x) = 6 / (1 - 5x + 6x^2) (Ej. 14):")
    print(f"    Serie formal  : {rec.series_coeffs}")
    print(f"    Fórmula exacta: {closed}  (Coincidencia: {rec.series_coeffs == closed})")
    print("=" * 76)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Contador Combinatorio con Funciones Generadoras (Tema 10)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Ejecuta la demostración completa de todos los módulos.")

    p_coins = sub.add_parser("coins", help="Cuenta combinaciones de cambio de monedas.")
    p_coins.add_argument("--denoms", required=True, help="Denominaciones separadas por coma, ej: 1,2,5,10,20,50,100")
    p_coins.add_argument("--target", type=int, required=True, help="Monto objetivo entero.")
    p_coins.add_argument("--limits", default=None, help="Límites opcionales por moneda separados por coma (usar - para ilimitado).")

    p_comp = sub.add_parser("compose", help="Cuenta soluciones enteras x_1 + ... + x_m = n con restricciones.")
    p_comp.add_argument("--specs", required=True, help="Lista separada por coma de 'min:max:step' o '{v1,v2}'.")
    p_comp.add_argument("--target", type=int, required=True, help="Suma objetivo n.")
    p_comp.add_argument("--method", default="auto", choices=["auto", "structured", "schoolbook", "ntt", "karatsuba"])
    p_comp.add_argument("--verify", action="store_true", help="Contrasta el resultado contra DP.")

    p_part = sub.add_parser("partitions", help="Calcula particiones de enteros mediante productos de Euler.")
    p_part.add_argument("--n", type=int, required=True, help="Entero objetivo n.")
    p_part.add_argument("--variant", default="all", choices=["unrestricted", "distinct", "odd", "all"])

    sub.add_parser("benchmark", help="Ejecuta la suite de benchmarks y guarda results/benchmark_results.json.")

    args = parser.parse_args(argv)
    counter = CombinatorialCounter()

    if args.command == "demo":
        cmd_demo()
    elif args.command == "coins":
        denoms = [int(x) for x in args.denoms.split(",")]
        limits = None
        if args.limits:
            limits = [None if x.strip() in ("-", "", "inf") else int(x) for x in args.limits.split(",")]
        res = counter.count_coin_change(denoms, args.target, limits=limits)
        print(f"FGO: G(x) = {res.symbolic_gf}")
        print(f"Formas para n = {args.target}: {res.count:,}")
    elif args.command == "compose":
        # Separar respetando llaves {a,b}
        tokens: List[str] = []
        buf = ""
        depth = 0
        for ch in args.specs:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            if ch == "," and depth == 0:
                tokens.append(buf)
                buf = ""
            else:
                buf += ch
        if buf:
            tokens.append(buf)
        constraints = [_parse_spec(t, i) for i, t in enumerate(tokens)]
        res = counter.count_constrained_compositions(constraints, args.target, method=args.method)
        print(f"FGO: G(x) = {res.symbolic_gf}")
        print(f"Método: {res.method_used}")
        print(f"[x^{args.target}] G(x) = {res.count:,}")
        if args.verify:
            dp_v = dp_compositions(constraints, args.target)[args.target]
            print(f"Validación DP: {dp_v:,} -> {'OK' if dp_v == res.count else 'FALLO'}")
    elif args.command == "partitions":
        variants = ["unrestricted", "distinct", "odd"] if args.variant == "all" else [args.variant]
        for v in variants:
            r = counter.count_partitions(args.n, variant=v)
            print(f"{v:12s} | n={args.n} | count={r.count:,} | FGO={r.symbolic_gf}")
    elif args.command == "benchmark":
        root = Path(__file__).resolve().parent.parent
        run_all_benchmarks(root / "results" / "benchmark_results.json")
        print("Benchmarks guardados en results/benchmark_results.json")


if __name__ == "__main__":
    main()

"""
Suite de pruebas automatizadas para el Contador Combinatorio con Funciones Generadoras.

Ejecutar con:
    python3 -m unittest discover -s tests -v
"""

import math
import unittest

from src.combinatorics_engine import (
    CombinatorialCounter,
    VariableConstraint,
    exact_bounded_inclusion_exclusion,
    exact_stars_and_bars,
)
from src.formal_series import FormalPowerSeries
from src.validators import (
    brute_force_compositions,
    brute_force_restricted_permutations,
    dp_compositions,
)


class TestFormalPowerSeries(unittest.TestCase):
    def test_binomial_and_negative_binomial(self) -> None:
        # (1 + x)^8 = sum C(8, k) x^k
        one_plus_x = FormalPowerSeries([1, 1], max_degree=10)
        p = one_plus_x.pow(8)
        for k in range(11):
            self.assertEqual(p[k], math.comb(8, k))

        # 1 / (1 - x)^5 = sum C(5 + k - 1, k) x^k
        one_minus_x = FormalPowerSeries([1, -1], max_degree=12)
        neg_bin = one_minus_x.pow(5).inverse()
        for k in range(13):
            self.assertEqual(neg_bin[k], math.comb(5 + k - 1, k))

    def test_inverse_identity_and_non_invertible_error(self) -> None:
        a = FormalPowerSeries([1, -3, 2, 5, -1], max_degree=20)
        inv_a = a.inverse()
        prod = a.multiply(inv_a, method="schoolbook")
        self.assertEqual(prod[0], 1)
        for k in range(1, 21):
            self.assertEqual(prod[k], 0)

        with self.assertRaises(ZeroDivisionError):
            FormalPowerSeries([0, 1, 2], max_degree=5).inverse()

    def test_convolution_methods_exact_equivalence(self) -> None:
        n = 150
        a = FormalPowerSeries([(k * 5 + 3) % 19 - 7 for k in range(n + 1)], max_degree=n)
        b = FormalPowerSeries([(k * 7 + 1) % 23 - 10 for k in range(n + 1)], max_degree=n)
        r_school = a.multiply(b, method="schoolbook")
        r_kara = a.multiply(b, method="karatsuba")
        r_ntt = a.multiply(b, method="ntt")
        self.assertEqual(r_school.coeffs, r_kara.coeffs)
        self.assertEqual(r_school.coeffs, r_ntt.coeffs)

    def test_ntt_large_coeff_karatsuba_fallback(self) -> None:
        # Coeficientes > 10^15 cuyo producto supera P1*P2*P3/2 -> respaldo automático a Karatsuba
        big = 10**15
        n = 60
        a = FormalPowerSeries([big + k for k in range(n + 1)], max_degree=n)
        b = FormalPowerSeries([big + 2 * k for k in range(n + 1)], max_degree=n)
        r_school = a.multiply(b, method="schoolbook")
        r_ntt = a.multiply(b, method="ntt")
        self.assertEqual(r_school.coeffs, r_ntt.coeffs)


class TestCombinatorialCounter(unittest.TestCase):
    def setUp(self) -> None:
        self.counter = CombinatorialCounter()

    def test_stars_and_bars_and_inclusion_exclusion(self) -> None:
        # Sin cota superior: x1 + x2 + x3 + x4 = 25 con x1>=2, x2>=0, x3>=3, x4>=1
        lowers = [2, 0, 3, 1]
        cs = [VariableConstraint(f"x{i}", min_val=l) for i, l in enumerate(lowers)]
        res = self.counter.count_constrained_compositions(cs, 25, method="structured")
        self.assertEqual(res.count, exact_stars_and_bars(4, 25, lowers))

        # Cota superior uniforme: 5 variables en [0, 7] sumando 18
        cs_u = [VariableConstraint(f"x{i}", min_val=0, max_val=7) for i in range(5)]
        expected = exact_bounded_inclusion_exclusion(5, 18, 7)
        for m in ("structured", "schoolbook", "ntt", "karatsuba"):
            res_u = self.counter.count_constrained_compositions(cs_u, 18, method=m)
            self.assertEqual(res_u.count, expected)

    def test_heterogeneous_constraints_against_oracles(self) -> None:
        cs = [
            VariableConstraint("x1", min_val=1, max_val=6, step=1),
            VariableConstraint("x2", min_val=0, max_val=8, step=2),
            VariableConstraint("x3", min_val=1, max_val=9, step=2),
            VariableConstraint("x4", allowed=(0, 3, 4, 7)),
        ]
        n = 15
        res_ntt = self.counter.count_constrained_compositions(cs, n, method="ntt")
        res_school = self.counter.count_constrained_compositions(cs, n, method="schoolbook")
        dp = dp_compositions(cs, n)
        bf_count, _ = brute_force_compositions(cs, n)

        self.assertEqual(res_ntt.series_coeffs, dp)
        self.assertEqual(res_school.series_coeffs, dp)
        self.assertEqual(res_ntt.count, bf_count)

    def test_edge_cases(self) -> None:
        # Caso límite n = 0 con variables >= 0 -> 1 forma (todos 0)
        cs = [VariableConstraint("x1", 0, 5), VariableConstraint("x2", 0, 5)]
        self.assertEqual(self.counter.count_constrained_compositions(cs, 0).count, 1)

        # Caso imposible: suma mínima 10 > n = 7 -> 0
        cs_imp = [VariableConstraint("x1", 4, 10), VariableConstraint("x2", 6, 10)]
        self.assertEqual(self.counter.count_constrained_compositions(cs_imp, 7).count, 0)

        # Caso imposible por paridad: dos variables pares no pueden sumar 11
        cs_par = [VariableConstraint("x1", 0, None, 2), VariableConstraint("x2", 0, None, 2)]
        self.assertEqual(self.counter.count_constrained_compositions(cs_par, 11).count, 0)
        self.assertEqual(self.counter.count_constrained_compositions(cs_par, 10).count, 6)

        # Caso límite: stock máximo insuficiente en cambio de monedas
        res_coin = self.counter.count_coin_change([5, 10], 50, limits=[2, 2])
        self.assertEqual(res_coin.count, 0)  # máximo alcanzable es 2*5 + 2*10 = 30

        # Validación de entradas inválidas
        with self.assertRaises(ValueError):
            self.counter.count_coin_change([1, -5], 10)
        with self.assertRaises(ValueError):
            self.counter.count_partitions(-1)

    def test_coin_change_classic_euro_and_dp(self) -> None:
        # Cambio de 1 Euro (100 céntimos) con {1, 2, 5, 10, 20, 50, 100} = 4563 formas (resultado clásico conocido)
        euro = self.counter.count_coin_change([1, 2, 5, 10, 20, 50, 100], 100)
        self.assertEqual(euro.count, 4563)

        # Cambio con stock limitado contrastado con DP
        cs = [
            VariableConstraint("c1", 0, 10, 1),
            VariableConstraint("c5", 0, 20, 5),
            VariableConstraint("c10", 0, 30, 10),
        ]
        res_lim = self.counter.count_coin_change([1, 5, 10], 27, limits=[10, 4, 3])
        self.assertEqual(res_lim.count, dp_compositions(cs, 27)[27])

    def test_euler_partitions_and_theorem(self) -> None:
        # Valores exactos conocidos de OEIS A000041
        expected_p = {0: 1, 1: 1, 2: 2, 3: 3, 4: 5, 5: 7, 10: 42, 20: 627, 30: 5604}
        p_all = self.counter.count_partitions(50, variant="unrestricted")
        for k, val in expected_p.items():
            self.assertEqual(p_all.series_coeffs[k], val)

        # Teorema de Euler: p_distintas(n) == p_impares(n) para todo n >= 0
        p_dist = self.counter.count_partitions(50, variant="distinct")
        p_odd = self.counter.count_partitions(50, variant="odd")
        self.assertEqual(p_dist.series_coeffs, p_odd.series_coeffs)

    def test_egf_restricted_permutations(self) -> None:
        # Cadenas sobre {A, B} con número par de A's: a_0 = 1, a_n = 2^{n-1} para n >= 1
        cs_ab = [
            VariableConstraint("A", min_val=0, step=2),
            VariableConstraint("B", min_val=0, step=1),
        ]
        res_ab = self.counter.count_restricted_permutations_egf(cs_ab, 10)
        self.assertEqual(res_ab.series_coeffs[0], 1)
        for k in range(1, 11):
            self.assertEqual(res_ab.series_coeffs[k], 2 ** (k - 1))

        # Caso heterogéneo contrastado contra oráculo multinomial independiente
        cs_het = [
            VariableConstraint("A", min_val=1, max_val=4),
            VariableConstraint("B", min_val=0, step=2),
            VariableConstraint("C", allowed=(0, 1, 3)),
        ]
        res_het = self.counter.count_restricted_permutations_egf(cs_het, 8)
        for k in range(9):
            self.assertEqual(
                res_het.series_coeffs[k],
                brute_force_restricted_permutations(cs_het, k),
            )

    def test_course_practice_14_exercises_9_to_14(self) -> None:
        # Ej. 9: 2,2,2,2,2,2 -> G(x) = 2(1 - x^6)/(1 - x)
        ej9 = self.counter.expand_rational_gf([2, 0, 0, 0, 0, 0, -2], [1, -1], max_degree=8)
        self.assertEqual(ej9.series_coeffs, [2, 2, 2, 2, 2, 2, 0, 0, 0])

        # Ej. 10: 1,4,16,64,256 -> G(x) = (1 - 1024 x^5)/(1 - 4x)
        ej10 = self.counter.expand_rational_gf([1, 0, 0, 0, 0, -1024], [1, -4], max_degree=7)
        self.assertEqual(ej10.series_coeffs, [1, 4, 16, 64, 256, 0, 0, 0])

        # Ej. 11: a_k = 7 a_{k-1}, a_0 = 5 -> G(x) = 5/(1 - 7x), a_k = 5 * 7^k
        ej11 = self.counter.expand_rational_gf([5], [1, -7], max_degree=6)
        self.assertEqual(ej11.series_coeffs, [5 * (7**k) for k in range(7)])

        # Ej. 12: a_k = 3 a_{k-1} + 2, a_0 = 1 -> G(x) = (1 + x)/((1-x)(1-3x)), a_k = 2*3^k - 1
        ej12 = self.counter.expand_rational_gf([1, 1], [1, -4, 3], max_degree=8)
        self.assertEqual(ej12.series_coeffs, [2 * (3**k) - 1 for k in range(9)])

        # Ej. 13: a_k = 3 a_{k-1} + 4^{k-1}, a_0 = 1 -> G(x) = 1/(1 - 4x), a_k = 4^k
        ej13 = self.counter.expand_rational_gf([1], [1, -4], max_degree=8)
        self.assertEqual(ej13.series_coeffs, [4**k for k in range(9)])

        # Ej. 14: a_k = 5 a_{k-1} - 6 a_{k-2}, a_0 = 6, a_1 = 30 -> G(x) = 6/(1 - 5x + 6x^2)
        ej14 = self.counter.expand_rational_gf([6], [1, -5, 6], max_degree=8)
        self.assertEqual(ej14.series_coeffs, [18 * (3**k) - 12 * (2**k) for k in range(9)])


if __name__ == "__main__":
    unittest.main()

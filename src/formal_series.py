"""
Motor de Series Formales de Potencias Truncadas en Z[[x]] / (x^{N+1}) y Q[[x]] / (x^{N+1}).

Implementa operaciones algebraicas exactas sin dependencias externas:
- Suma, resta, multiplicación escalar.
- Producto de Cauchy clásico en O(N^2).
- Convolución exacta en O(N log N) mediante Transformada Teórica de Números (NTT)
  con Teorema Chino del Resto (CRT) sobre tres primos amigables para NTT,
  con respaldo automático a Karatsuba en O(N^{1.585}) para coeficientes arbitrariamente grandes.
- Inversión formal 1 / A(x) mod x^{N+1}.
- Operadores estructurados O(N) para factores racionales (1 + c x^r) y 1/(1 - c x^r).
- Exponenciación binaria A(x)^p y árbol de productos divide-y-vencerás.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable, List, Sequence, Union

Coeff = Union[int, Fraction]

# Tres primos NTT-amigables de 30 bits con raíz primitiva g = 3.
# Producto P1 * P2 * P3 ~= 7.86e25, suficiente para resultados enteros exactos enormes.
_NTT_PRIMES = (
    (998244353, 3),   # 119 * 2^23 + 1
    (167772161, 3),   # 5   * 2^25 + 1
    (469762049, 3),   # 7   * 2^26 + 1
)
_P1, _P2, _P3 = _NTT_PRIMES[0][0], _NTT_PRIMES[1][0], _NTT_PRIMES[2][0]
_P1_INV_P2 = pow(_P1, _P2 - 2, _P2)
_P1P2 = _P1 * _P2
_P1P2_INV_P3 = pow(_P1P2 % _P3, _P3 - 2, _P3)
_P1P2P3 = _P1P2 * _P3


def _ntt_inplace(a: List[int], invert: bool, mod: int, root: int) -> None:
    """Transformada Teórica de Números (Cooley-Tukey iterativa en orden bit-reverso)."""
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]

    length = 2
    while length <= n:
        wlen = pow(root, (mod - 1) // length, mod)
        if invert:
            wlen = pow(wlen, mod - 2, mod)
        half = length >> 1
        for i in range(0, n, length):
            w = 1
            for k in range(i, i + half):
                u = a[k]
                v = (a[k + half] * w) % mod
                a[k] = (u + v) % mod
                a[k + half] = (u - v) % mod
                w = (w * wlen) % mod
        length <<= 1

    if invert:
        inv_n = pow(n, mod - 2, mod)
        for i in range(n):
            a[i] = (a[i] * inv_n) % mod


def _ntt_convolve_mod(a: Sequence[int], b: Sequence[int], mod: int, root: int) -> List[int]:
    """Convolución exacta módulo un primo NTT-amigable."""
    need = len(a) + len(b) - 1
    size = 1
    while size < need:
        size <<= 1
    fa = [x % mod for x in a] + [0] * (size - len(a))
    fb = [x % mod for x in b] + [0] * (size - len(b))
    _ntt_inplace(fa, False, mod, root)
    _ntt_inplace(fb, False, mod, root)
    for i in range(size):
        fa[i] = (fa[i] * fb[i]) % mod
    _ntt_inplace(fa, True, mod, root)
    return fa[:need]


def schoolbook_convolve(a: Sequence[Coeff], b: Sequence[Coeff], max_degree: int) -> List[Coeff]:
    """Producto de Cauchy clásico en O(N^2) truncado a grado max_degree."""
    zero: Coeff = Fraction(0) if (a and isinstance(a[0], Fraction)) or (b and isinstance(b[0], Fraction)) else 0
    la = min(len(a), max_degree + 1)
    lb = min(len(b), max_degree + 1)
    out_len = min(la + lb - 1, max_degree + 1) if la > 0 and lb > 0 else 0
    res: List[Coeff] = [zero] * out_len
    for i in range(la):
        ai = a[i]
        if ai == 0:
            continue
        limit = min(lb, max_degree + 1 - i)
        for j in range(limit):
            bj = b[j]
            if bj != 0:
                res[i + j] += ai * bj
    return res


def karatsuba_convolve(a: Sequence[int], b: Sequence[int]) -> List[int]:
    """Multiplicación exacta de polinomios enteros mediante Karatsuba en O(N^{log2 3})."""
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return []
    if min(na, nb) <= 32:
        res = [0] * (na + nb - 1)
        for i, ai in enumerate(a):
            if ai:
                for j, bj in enumerate(b):
                    if bj:
                        res[i + j] += ai * bj
        return res

    n = max(na, nb)
    m = n // 2
    a_low = a[:m]
    a_high = a[m:]
    b_low = b[:m]
    b_high = b[m:]

    z0 = karatsuba_convolve(a_low, b_low)
    z2 = karatsuba_convolve(a_high, b_high)

    a_sum = [
        (a_low[i] if i < len(a_low) else 0) + (a_high[i] if i < len(a_high) else 0)
        for i in range(max(len(a_low), len(a_high)))
    ]
    b_sum = [
        (b_low[i] if i < len(b_low) else 0) + (b_high[i] if i < len(b_high) else 0)
        for i in range(max(len(b_low), len(b_high)))
    ]
    z1 = karatsuba_convolve(a_sum, b_sum)

    res = [0] * (na + nb - 1)
    for i, val in enumerate(z0):
        res[i] += val
    for i, val in enumerate(z2):
        res[i + 2 * m] += val
    for i in range(len(z1)):
        mid = z1[i]
        if i < len(z0):
            mid -= z0[i]
        if i < len(z2):
            mid -= z2[i]
        if mid and i + m < len(res):
            res[i + m] += mid
    return res


def ntt_convolve_exact(a: Sequence[int], b: Sequence[int], max_degree: int) -> List[int]:
    """
    Convolución exacta en Z[x] truncada a grado max_degree en O(N log N)
    usando NTT en 3 primos + reconstrucción exacta vía Teorema Chino del Resto (CRT).
    Si el rango de coeficientes puede exceder P1*P2*P3/2, delega automáticamente a Karatsuba.
    """
    a_tr = list(a[: max_degree + 1])
    b_tr = list(b[: max_degree + 1])
    if not a_tr or not b_tr:
        return []
    if min(len(a_tr), len(b_tr)) <= 32:
        return [int(v) for v in schoolbook_convolve(a_tr, b_tr, max_degree)]

    max_a = max(abs(x) for x in a_tr)
    max_b = max(abs(x) for x in b_tr)
    if max_a == 0 or max_b == 0:
        return [0]

    upper_bound = max_a * max_b * min(len(a_tr), len(b_tr))
    if upper_bound >= _P1P2P3 // 2:
        return karatsuba_convolve(a_tr, b_tr)[: max_degree + 1]

    c1 = _ntt_convolve_mod(a_tr, b_tr, _P1, 3)
    c2 = _ntt_convolve_mod(a_tr, b_tr, _P2, 3)
    c3 = _ntt_convolve_mod(a_tr, b_tr, _P3, 3)

    out_len = min(len(c1), max_degree + 1)
    half_mod = _P1P2P3 // 2
    res: List[int] = [0] * out_len
    for i in range(out_len):
        r1, r2, r3 = c1[i], c2[i], c3[i]
        # Combinar r1 (mod P1) y r2 (mod P2)
        k1 = ((r2 - r1) * _P1_INV_P2) % _P2
        x12 = r1 + _P1 * k1
        # Combinar x12 (mod P1*P2) y r3 (mod P3)
        k2 = ((r3 - x12 % _P3) * _P1P2_INV_P3) % _P3
        val = x12 + _P1P2 * k2
        if val > half_mod:
            val -= _P1P2P3
        res[i] = val
    return res


class FormalPowerSeries:
    """
    Representa una serie formal de potencias truncada:
        A(x) = sum_{k=0}^{N} a_k x^k  (mod x^{N+1})
    sobre Z (int) o Q (Fraction).
    """

    def __init__(
        self,
        coeffs: Iterable[Coeff],
        max_degree: int,
        rational: bool = False,
    ) -> None:
        if max_degree < 0:
            raise ValueError("max_degree debe ser no negativo.")
        self.max_degree = max_degree
        raw = list(coeffs)[: max_degree + 1]
        self.rational = rational or any(isinstance(c, Fraction) for c in raw)
        if self.rational:
            self.coeffs: List[Coeff] = [Fraction(c) for c in raw]
            while len(self.coeffs) <= max_degree:
                self.coeffs.append(Fraction(0))
        else:
            self.coeffs = [int(c) for c in raw]
            while len(self.coeffs) <= max_degree:
                self.coeffs.append(0)

    @classmethod
    def one(cls, max_degree: int, rational: bool = False) -> "FormalPowerSeries":
        return cls([Fraction(1) if rational else 1], max_degree=max_degree, rational=rational)

    @classmethod
    def zero(cls, max_degree: int, rational: bool = False) -> "FormalPowerSeries":
        return cls([], max_degree=max_degree, rational=rational)

    @classmethod
    def from_exponents(
        cls,
        exponents: Iterable[int],
        max_degree: int,
        exponential: bool = False,
    ) -> "FormalPowerSeries":
        """Construye sum_{c in exponents} x^c (FGO) o sum_{c in exponents} x^c / c! (FGE)."""
        if exponential:
            coeffs: List[Coeff] = [Fraction(0)] * (max_degree + 1)
            fact = 1
            facts = [1] * (max_degree + 1)
            for k in range(1, max_degree + 1):
                fact *= k
                facts[k] = fact
            for c in exponents:
                if 0 <= c <= max_degree:
                    coeffs[c] += Fraction(1, facts[c])
            return cls(coeffs, max_degree=max_degree, rational=True)

        coeffs_int: List[int] = [0] * (max_degree + 1)
        for c in exponents:
            if 0 <= c <= max_degree:
                coeffs_int[c] += 1
        return cls(coeffs_int, max_degree=max_degree, rational=False)

    def coeff(self, k: int) -> Coeff:
        """Retorna el coeficiente [x^k] A(x)."""
        if k < 0 or k > self.max_degree:
            return Fraction(0) if self.rational else 0
        return self.coeffs[k]

    def __getitem__(self, k: int) -> Coeff:
        return self.coeff(k)

    def _promote_rational(self) -> "FormalPowerSeries":
        if self.rational:
            return self
        return FormalPowerSeries(self.coeffs, max_degree=self.max_degree, rational=True)

    def __add__(self, other: "FormalPowerSeries") -> "FormalPowerSeries":
        deg = min(self.max_degree, other.max_degree)
        rat = self.rational or other.rational
        return FormalPowerSeries(
            [self.coeffs[i] + other.coeffs[i] for i in range(deg + 1)],
            max_degree=deg,
            rational=rat,
        )

    def __sub__(self, other: "FormalPowerSeries") -> "FormalPowerSeries":
        deg = min(self.max_degree, other.max_degree)
        rat = self.rational or other.rational
        return FormalPowerSeries(
            [self.coeffs[i] - other.coeffs[i] for i in range(deg + 1)],
            max_degree=deg,
            rational=rat,
        )

    def scale(self, scalar: Coeff) -> "FormalPowerSeries":
        rat = self.rational or isinstance(scalar, Fraction)
        return FormalPowerSeries(
            [c * scalar for c in self.coeffs],
            max_degree=self.max_degree,
            rational=rat,
        )

    def multiply(
        self,
        other: "FormalPowerSeries",
        method: str = "auto",
    ) -> "FormalPowerSeries":
        """
        Multiplica dos series truncadas usando:
        - 'schoolbook': producto de Cauchy clásico en O(N^2).
        - 'ntt': convolución exacta NTT+CRT en O(N log N) (solo enteros; respalda a Karatsuba).
        - 'karatsuba': multiplicación Karatsuba en O(N^{1.585}).
        - 'auto': usa NTT para enteros con N >= 48 y schoolbook en caso contrario o racionales.
        """
        deg = min(self.max_degree, other.max_degree)
        rat = self.rational or other.rational

        # Recortar ceros finales para acelerar multiplicaciones de polinomios cortos
        a = list(self.coeffs[: deg + 1])
        b = list(other.coeffs[: deg + 1])
        while len(a) > 1 and a[-1] == 0:
            a.pop()
        while len(b) > 1 and b[-1] == 0:
            b.pop()

        if rat:
            res = schoolbook_convolve(
                [Fraction(x) for x in a],
                [Fraction(x) for x in b],
                deg,
            )
            return FormalPowerSeries(res, max_degree=deg, rational=True)

        a_int = [int(x) for x in a]
        b_int = [int(x) for x in b]

        if method == "schoolbook":
            res_int = [int(x) for x in schoolbook_convolve(a_int, b_int, deg)]
        elif method == "ntt":
            res_int = ntt_convolve_exact(a_int, b_int, deg)
        elif method == "karatsuba":
            res_int = karatsuba_convolve(a_int, b_int)[: deg + 1]
        elif method == "auto":
            if min(len(a_int), len(b_int)) >= 48:
                res_int = ntt_convolve_exact(a_int, b_int, deg)
            else:
                res_int = [int(x) for x in schoolbook_convolve(a_int, b_int, deg)]
        else:
            raise ValueError(f"Método de multiplicación desconocido: {method}")

        return FormalPowerSeries(res_int, max_degree=deg, rational=False)

    def __mul__(self, other: "FormalPowerSeries") -> "FormalPowerSeries":
        return self.multiply(other, method="auto")

    def inverse(self) -> "FormalPowerSeries":
        """
        Calcula B(x) = 1 / A(x) mod x^{N+1} cuando a_0 != 0.
        Si a_0 es +1 o -1 y la serie es entera, mantiene aritmética entera exacta.
        """
        a0 = self.coeffs[0]
        if a0 == 0:
            raise ZeroDivisionError("Una serie formal es invertible si y solo si a_0 != 0.")

        n = self.max_degree
        if not self.rational and a0 in (1, -1):
            b_int = [0] * (n + 1)
            b_int[0] = int(a0)  # 1/1 = 1, 1/(-1) = -1
            nz = [(j, int(self.coeffs[j])) for j in range(1, n + 1) if self.coeffs[j] != 0]
            for k in range(1, n + 1):
                acc = 0
                for j, aj in nz:
                    if j > k:
                        break
                    acc += aj * b_int[k - j]
                b_int[k] = -acc if a0 == 1 else acc
            return FormalPowerSeries(b_int, max_degree=n, rational=False)

        b_rat = [Fraction(0)] * (n + 1)
        inv_a0 = Fraction(1, a0)
        b_rat[0] = inv_a0
        nz_r = [(j, Fraction(self.coeffs[j])) for j in range(1, n + 1) if self.coeffs[j] != 0]
        for k in range(1, n + 1):
            acc_r = Fraction(0)
            for j, aj in nz_r:
                if j > k:
                    break
                acc_r += aj * b_rat[k - j]
            b_rat[k] = -acc_r * inv_a0
        return FormalPowerSeries(b_rat, max_degree=n, rational=True)

    def divide(self, other: "FormalPowerSeries", method: str = "auto") -> "FormalPowerSeries":
        """Retorna self / other mod x^{N+1}."""
        return self.multiply(other.inverse(), method=method)

    def pow(self, exponent: int, method: str = "auto") -> "FormalPowerSeries":
        """Calcula A(x)^exponent mediante exponenciación binaria en O(log exponent) productos."""
        if exponent < 0:
            return self.inverse().pow(-exponent, method=method)
        result = FormalPowerSeries.one(self.max_degree, rational=self.rational)
        base = self
        e = exponent
        while e > 0:
            if e & 1:
                result = result.multiply(base, method=method)
            e >>= 1
            if e > 0:
                base = base.multiply(base, method=method)
        return result

    def mul_binomial_factor(self, coeff: int, power: int) -> "FormalPowerSeries":
        """Multiplica in-place conceptualmente por (1 + coeff * x^power) en O(N)."""
        if power <= 0:
            raise ValueError("power debe ser >= 1.")
        out = list(self.coeffs)
        for k in range(self.max_degree, power - 1, -1):
            out[k] = out[k] + coeff * out[k - power]
        return FormalPowerSeries(out, max_degree=self.max_degree, rational=self.rational)

    def div_one_minus_monomial(self, coeff: int, power: int) -> "FormalPowerSeries":
        """Divide por (1 - coeff * x^power) en O(N): b_k = a_k + coeff * b_{k - power}."""
        if power <= 0:
            raise ValueError("power debe ser >= 1.")
        out = list(self.coeffs)
        for k in range(power, self.max_degree + 1):
            out[k] = out[k] + coeff * out[k - power]
        return FormalPowerSeries(out, max_degree=self.max_degree, rational=self.rational)

    def derivative(self) -> "FormalPowerSeries":
        """Derivada formal A'(x) = sum_{k=1}^N k * a_k * x^{k-1}."""
        res = [k * self.coeffs[k] for k in range(1, self.max_degree + 1)]
        return FormalPowerSeries(res, max_degree=max(0, self.max_degree - 1), rational=self.rational)

    def pretty(self, max_terms: int = 8) -> str:
        """Representación legible de los primeros términos no nulos."""
        terms: List[str] = []
        shown = 0
        for k, c in enumerate(self.coeffs):
            if c == 0:
                continue
            if shown >= max_terms:
                terms.append("...")
                break
            if k == 0:
                terms.append(f"{c}")
            elif k == 1:
                terms.append("x" if c == 1 else f"{c}x")
            else:
                terms.append(f"x^{k}" if c == 1 else f"{c}x^{k}")
            shown += 1
        return " + ".join(terms) if terms else "0"


def product_tree(
    factors: Sequence[FormalPowerSeries],
    max_degree: int,
    method: str = "auto",
) -> FormalPowerSeries:
    """
    Multiplica m series formales usando un árbol binario equilibrado (divide y vencerás).
    Reduce el grado intermedio al multiplicar primero polinomios pequeños antes de combinarlos.
    """
    if not factors:
        return FormalPowerSeries.one(max_degree)
    if len(factors) == 1:
        return factors[0]
    mid = len(factors) // 2
    left = product_tree(factors[:mid], max_degree=max_degree, method=method)
    right = product_tree(factors[mid:], max_degree=max_degree, method=method)
    return left.multiply(right, method=method)

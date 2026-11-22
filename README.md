# Tema 10: Diseño de un Contador Combinatorio con Funciones Generadoras

**Curso:** Estructuras Discretas II — Ingeniería Informática (2026-II)  
**Institución:** Universidad Peruana Cayetano Heredia (UPCH) — Facultad de Ciencias e Ingeniería  
**Asesor:** Dr. Ing. CIP. Omar Felix Illesca Cangalaya

---

## Descripción del Proyecto

Este repositorio implementa y valida un **contador combinatorio exacto** basado en el álgebra de **series formales de potencias** ($\mathbb{Z}[[x]]$ y $\mathbb{Q}[[x]]$), completamente en **Python 3.12 estándar** (cero dependencias externas para el motor de cálculo, validación y pruebas).

### Capacidades implementadas
1. **Composiciones y selección con restricciones heterogéneas** ($x_1 + \dots + x_m = n$ con rangos $[l_i, u_i]$, paridad, múltiplos $d_i$ o conjuntos explícitos $S_i$).
2. **Cambio de monedas** (inventario ilimitado y con stock finito $q_i$).
3. **Particiones de enteros de Euler** ($p(n)$, $p_{\text{distintas}}(n)$, $p_{\text{impares}}(n)$) y verificación empírica de $p_{\text{dist}}(n) = p_{\text{imp}}(n)$ y contraste con Hardy-Ramanujan.
4. **Permutaciones con repetición restringida mediante FGE** (Funciones Generatrices Exponenciales): $a_n = n! [x^n] \prod_i \sum_{c \in S_i} x^c / c!$.
5. **Resolución y expansión de relaciones de recurrencia racionales** $G(x) = P(x)/Q(x)$ mediante inversión formal de series.
6. **Tres estrategias exactas de multiplicación**:
   - Operadores racionales estructurados en $O(m \cdot N)$.
   - Convolución exacta mediante **Transformada Teórica de Números (NTT) + Teorema Chino del Resto (CRT)** sobre 3 primos en $O(N \log N)$ (con respaldo automático a Karatsuba para coeficientes $> 10^{25}$).
   - Producto de Cauchy clásico en $O(N^2)$ y Karatsuba en $O(N^{1.585})$.
7. **Validación cruzada independiente** (`src/validators.py`): fuerza bruta recursiva, programación dinámica, estrellas y barras, inclusión-exclusión y oráculo multinomial.

---

## Reproducción rápida

Solo se requiere **Python 3.12+**:

```bash
# 1. Ejecutar las 11 pruebas automatizadas (casos normales, límite y Ejercicios 9-14)
python3 -m unittest discover -s tests -v

# 2. Ejecutar demostración integral por CLI
python3 -m src.cli demo

# 3. Consultas personalizadas por CLI
python3 -m src.cli coins --denoms 1,2,5,10,20,50,100 --target 100
python3 -m src.cli coins --denoms 10,20,50,100,200,500 --target 500 --limits 10,8,5,4,2,1
python3 -m src.cli compose --specs "1:8:1,0:10:2,1:9:2,0:12:3,2:6:1" --target 20 --verify
python3 -m src.cli partitions --n 60 --variant all

# 4. Reejecutar la suite de benchmarks (guarda results/benchmark_results.json)
python3 -m src.benchmarks
```

### Regenerar gráficas e informe (`.docx` y `.pdf`)
```bash
python3 scripts/generate_charts.py
python3 scripts/build_report_docx.py
```

---

## Estructura del Repositorio

```text
├── README.md
├── src/
│   ├── formal_series.py          # Series formales truncadas, Cauchy, Karatsuba, NTT+CRT, 1/A(x)
│   ├── combinatorics_engine.py   # Contador combinatorio FGO y FGE
│   ├── validators.py             # Oráculos independientes (fuerza bruta, DP, Hardy-Ramanujan)
│   ├── benchmarks.py             # Benchmarks reproducibles
│   └── cli.py                    # Interfaz de línea de comandos
├── tests/
│   └── test_contador.py          # Suite de pruebas unitarias
├── scripts/
│   ├── generate_charts.py        # Genera las 4 figuras de 300 DPI
│   └── build_report_docx.py      # Genera el informe .docx/.pdf en formato UPCH
├── results/
│   └── benchmark_results.json    # Mediciones empíricas verificables
└── docs/
    ├── figures/                  # fig1..fig4 en alta resolución
    ├── Informe_Tema10_Contador_Combinatorio_FG.docx
    └── Informe_Tema10_Contador_Combinatorio_FG.pdf
```

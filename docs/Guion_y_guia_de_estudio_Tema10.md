# Guion y guía de estudio · Tema 10 · Contador combinatorio con funciones generadoras

Este documento contiene, diapositiva por diapositiva, **qué decir** (guion) y **qué debes entender** (explicación). Es el mismo texto que está en las *notas del orador* del archivo `.pptx`.

## Cómo estudiar con esto

1. **Primera vuelta (teoría, diapositivas 3–14):** lee solo las secciones «Para entender» y rehaz a mano los ejemplos (dados, monedas S/ 10, 3 servidores, Euler n = 5, palabras AAB/ABA/BAA, recurrencia Ej. 12).
2. **Segunda vuelta (diseño y resultados, 15–26):** repite en voz alta la idea de cada algoritmo con tus palabras.
3. **Tercera vuelta (defensa):** responde sin mirar las preguntas de las diapositivas 31 y 32.
4. **Ensayo:** cada integrante expone su bloque cronometrado y los demás hacen una pregunta.

## Quién expone y cuánto tiempo (aprox.)

| Bloque | Diapositivas | Expone | Tiempo aprox. |
|---|---|---|---|
| Intro y teoría I | 1–8, 28 | Aviles | ≈ 10 min |
| Teoría II (teoremas, FGE, recurrencias) | 9–14 | Chávez | ≈ 10 min |
| Diseño e implementación | 15–19 | Melgarejo | ≈ 8 min |
| Validación y exactitud | 20–22, 29 | Soriano | ≈ 6 min |
| Escalabilidad, discusión y conclusiones | 23–26 | Torres | ≈ 6 min |
| Equipo y cierre | 27, 30 | Todos | ≈ 2 min |

Tiempo total aproximado: **42 minutos** (sin contar el apéndice y las preguntas). Si el tiempo asignado es menor, se pueden resumir las diapositivas 4, 8, 13 y 28.

## Glosario rápido

- **Función generatriz ordinaria (FGO):** Serie Σ aₖ xᵏ que guarda la sucesión (aₖ) en sus coeficientes.
- **Función generatriz exponencial (FGE):** Serie Σ aₙ xⁿ/n!; se usa cuando el orden importa.
- **Serie formal:** Serie tratada como objeto algebraico: x no se evalúa y no se pide convergencia.
- **[xⁿ] G(x):** Coeficiente de xⁿ en G(x).
- **Producto de Cauchy:** Producto de series: cₖ = Σ_{j=0}^{k} aⱼ b_{k−j}.
- **Estrellas y barras:** Soluciones no negativas de x₁+…+xₙ = k: C(n+k−1, k).
- **Partición de n:** Forma de escribir n como suma de enteros positivos sin importar el orden.
- **NTT:** FFT en un cuerpo finito: usa enteros módulo un primo, sin redondeo.
- **CRT (teorema chino del resto):** Reconstruye un entero grande a partir de sus restos módulo varios primos.
- **Oráculo:** Método independiente (fuerza bruta, DP, fórmula cerrada) con el que se contrasta el resultado.

## Guion y explicación por diapositiva

### Diapositiva 1 · Portada
*Expone: Aviles · ≈ 0.5 min*

**Qué decir:** Buenas, profesor. Somos el equipo del Tema 10: «Diseño de un contador combinatorio con funciones generadoras». Vamos a empezar por la teoría desde cero, con ejemplos sencillos; luego veremos cómo la convertimos en un programa, cómo lo validamos y qué resultados obtuvimos.

**Para entender:** Esta lámina solo presenta el trabajo. Lo único que debes memorizar es la pregunta que responde todo el proyecto: ¿cómo contar EXACTAMENTE cuántas configuraciones cumplen varias restricciones, sin tener que listarlas una por una?

### Diapositiva 2 · Ruta de la exposición
*Expone: Aviles · ≈ 0.7 min*

**Qué decir:** La exposición sigue el orden del informe: primero el problema y la teoría; después el diseño del contador y sus algoritmos; luego la validación y los resultados; y cerramos con discusión y conclusiones. Cada integrante expone un bloque. Abajo ven los ocho criterios de la rúbrica, que suman 20 puntos: durante la exposición iremos mostrando dónde cumplimos cada uno.

**Para entender:** La rúbrica pesa así: Rigor y marco teórico 4, Diseño y simulación 4, Informe 2, Referencias 1, Exposición 3, Vestimenta 2, Trabajo en equipo 1, Defensa 3. Lo más pesado es lo técnico (8 de 20) y lo que depende de ustedes al hablar (exposición + defensa = 6). Por eso importa entender, no leer.

### Diapositiva 3 · El problema: contar sin tener que listar
*Expone: Aviles · ≈ 1.2 min*

**Qué decir:** Empecemos con un problema cotidiano: tenemos monedas de 1, 2 y 5 soles y queremos pagar 10 soles. Se pueden listar las formas a mano y salen 10. Pero si sumamos más monedas, más restricciones o una suma más grande, el número de configuraciones explota: con seis variables y suma 1000 hay más de dos billones, y listarlas a un millón por segundo tomaría casi un mes. Nuestra idea es no enumerar: traducir el problema a un polinomio y leer un solo coeficiente.

**Para entender:** Esto se llama explosión combinatoria: el número de casos crece tan rápido que enumerar deja de ser viable. La fuerza bruta de nuestro experimento ya necesitó 1,117,131 nodos para N = 34. Las funciones generatrices cambian el problema: en vez de recorrer casos, hacemos álgebra con polinomios.

### Diapositiva 4 · Antecedentes: de De Moivre a los algoritmos actuales
*Expone: Aviles · ≈ 1.2 min*

**Qué decir:** Esto no es nuevo ni aislado. De Moivre usó series para resolver recurrencias; Euler las aplicó a particiones y demostró que partes distintas y partes impares se cuentan igual; Laplace les dio el nombre de función generatriz; Pólya y Stanley las formalizaron sin pedir convergencia; Cooley, Tukey y Pollard hicieron rápida la multiplicación; y Wilf, Graham-Knuth-Patashnik y Flajolet-Sedgewick las llevaron a la informática. En cada tarjeta indicamos qué parte de nuestro trabajo usa ese aporte.

**Para entender:** Lo que pide el formato del informe es «conexión conceptual, no biografía aislada». Por eso cada autor se liga a algo que usamos: De Moivre → recurrencias; Euler → Teorema 4; Laplace → nombre y notación; Pólya/Stanley → series formales; Cooley-Tukey/Pollard → NTT; Wilf/Knuth/Flajolet → método simbólico y notación [xⁿ].

### Diapositiva 5 · Idea central: la sucesión «colgada» de un polinomio
*Expone: Aviles · ≈ 1.5 min*

**Qué decir:** La idea central es el «tendedero» de Wilf: una sucesión de números se cuelga de ganchos, que son las potencias de x. El coeficiente de x elevado a k guarda el término k de la sucesión. Por ejemplo, la sucesión 1, 1, 1, 1… es la serie 1 + x + x² + x³ + …, que se escribe como 1 sobre 1 menos x. Importante: x no es un número, solo marca la posición. Y la notación corchete x a la n de G(x) significa «dame el coeficiente de x a la n».

**Para entender:** Una función generatriz NO es una función que graficas: es una forma de empaquetar una sucesión en un solo objeto algebraico. Con ese objeto puedes sumar, multiplicar y dividir, y esas operaciones reflejan operaciones sobre la sucesión. Si entiendes «coeficiente = valor en esa posición» ya entendiste el 50 % del tema.

### Diapositiva 6 · La clave: multiplicar polinomios suma los exponentes
*Expone: Aviles · ≈ 1.8 min*

**Qué decir:** Aquí está la clave de todo: al multiplicar potencias, los exponentes se suman. Veámoslo con dos dados. Un dado es x + x² + … + x⁶: cada término es una cara posible. Al multiplicar dos dados, cada par de caras aporta una potencia cuyo exponente es la suma de las caras. El coeficiente de x⁷ cuenta cuántos pares suman 7: son (1,6), (2,5), (3,4), (4,3), (5,2) y (6,1), es decir, 6. En la tabla de la derecha, las casillas rojas son esas seis.

**Para entender:** Multiplicar polinomios = combinar elecciones independientes, y los exponentes llevan la «cuenta» de la suma. Cada factor representa una variable (un dado, una moneda, un servidor); el producto representa elegir un valor en cada una; el exponente total es la suma que nos interesa. Todo el trabajo es una aplicación grande de este truco.

### Diapositiva 7 · Series formales: el «tablero» donde ocurre todo
*Expone: Aviles · ≈ 1.5 min*

**Qué decir:** Formalmente trabajamos con series formales de potencias: la serie es solo una lista de coeficientes en Z o Q, y se suman término a término. El producto es el de Cauchy: el coeficiente de x^k es la suma de a_j por b_{k−j}, con j de 0 a k. En el ejemplo, (1+2x) por (3+x) da 3 + 7x + 2x². Como es álgebra, no importa si la serie converge: 1 sobre 1 menos x vale porque (1−x) por (1+x+x²+…) es 1 coeficiente a coeficiente. En la computadora truncamos en x^{N+1} y guardamos enteros exactos.

**Para entender:** «Formal» significa que no evaluamos x en ningún número; por eso no hay problema de convergencia. El producto de Cauchy es el «producto de polinomios de toda la vida» escrito con sumatoria: para el coeficiente k combinas los índices que suman k. Truncar en N+1 términos nos deja un objeto finito que la computadora puede guardar exactamente.

### Diapositiva 8 · Los bloques de construcción (piezas de Lego)
*Expone: Aviles · ≈ 1.5 min*

**Qué decir:** Estos son los bloques de construcción que usaremos, los de la Tabla 1 del informe. (1+x)^n representa elegir o no elegir cada uno de n objetos. 1 sobre 1 menos x^r es una moneda de valor r en cantidad ilimitada. (1 menos x^(n+1)) sobre (1 menos x) es una variable acotada entre 0 y n. 1 sobre (1−x)^n cuenta combinaciones con repetición. 1 sobre 1 menos a x es una recurrencia de primer orden. Y e^x o cosh(x) se usan cuando el orden importa.

**Para entender:** Aprende estos bloques como «piezas de Lego»: cada restricción de un problema se traduce a una pieza. «Variable entre 0 y n» → (1−x^{n+1})/(1−x). «Moneda de valor r ilimitada» → 1/(1−x^r). «Variable par» → 1/(1−x²). «Variable ≥ 1» → x/(1−x). El producto de las piezas es la función generatriz del problema.

### Diapositiva 9 · Ejemplo guiado: pagar S/ 10 con monedas de 1, 2 y 5
*Expone: Chávez · ≈ 2.0 min*

**Qué decir:** Resolvamos el ejemplo: pagar 10 soles con monedas de 1, 2 y 5. Cada moneda aporta un factor 1 sobre 1 menos x^d. Vamos construyendo la tabla por filas. Con solo monedas de 1, siempre hay 1 forma. Al agregar monedas de 2, cada casilla suma la de arriba más la que está dos lugares atrás: queda 1, 1, 2, 2, 3, 3… Al agregar monedas de 5, cada casilla suma la de arriba más la que está cinco lugares atrás. En n = 10 obtenemos 10 formas, que coincide con contarlas por cantidad de monedas de 5: 6 más 3 más 1. Esta regla de «sumar la casilla de d lugares atrás» es exactamente nuestro Algoritmo 1.

**Para entender:** Dividir una serie por (1 − x^d) equivale a la recurrencia b[n] = a[n] + b[n−d]. Esa es la razón de que nuestro algoritmo sea tan rápido: cada variable cuesta un solo barrido lineal. Si te piden «demuestra con un caso», usa esta tabla: es pequeña, se puede hacer en la pizarra y se verifica contando a mano (10 formas).

### Diapositiva 10 · Teoremas 1 y 2: inversión formal y binomio negativo
*Expone: Chávez · ≈ 1.8 min*

**Qué decir:** Teorema 1: una serie tiene inverso si y solo si su término constante no es cero. La demostración es un sistema triangular: a₀b₀ = 1 y cada b_k se despeja con los anteriores; si a₀ es cero, la primera ecuación no tiene solución. De aquí sale 1/(1−cx^r) = suma de c^m x^{mr}. Teorema 2, el binomio negativo: 1 sobre (1−x)^n tiene como coeficiente el binomial (n+k−1 sobre k). Se prueba por inducción multiplicando por 1/(1−x), que acumula coeficientes. Ejemplo: repartir 4 unidades entre 3 variables no negativas da binomial de 6 sobre 2, que es 15.

**Para entender:** Teorema 1 = «cuándo se puede dividir»: solo si el término constante no es 0 (como no se puede dividir entre 0 en los números). Teorema 2 = «estrellas y barras»: el número de soluciones no negativas de x₁+…+x_n = k es C(n+k−1, k). Para comprobarlo con n=3, k=4: C(6,2) = 15.

### Diapositiva 11 · Teorema 3: restricciones distintas → producto de factores
*Expone: Chávez · ≈ 1.8 min*

**Qué decir:** Teorema 3: si cada variable x_i toma valores en un conjunto S_i, el número de soluciones de la suma es el coeficiente de x^n en el producto de los polinomios que tienen un término por cada valor permitido. La demostración es expandir el producto: cada monomio sale de elegir un valor por factor, y sus exponentes se suman. Ejemplo con tres servidores: S₁ puede ser 1 o 2, S₂ es par (0 o 2) y S₃ es 0, 1 o 2. El producto da x + 2x² + 3x³ + 3x⁴ + 2x⁵ + x⁶. Para suma 4 hay 3 formas: (1,2,1), (2,0,2) y (2,2,0). Además, evaluar en x = 1 da 12, que es 2·2·3, todas las configuraciones.

**Para entender:** Este es el teorema «madre» del proyecto: cualquier restricción de rango, paridad o múltiplo se traduce a un factor. Si el conjunto es una progresión aritmética, el factor se escribe compacto como x^l (1 − x^{(q+1)d})/(1 − x^d); eso permite el Algoritmo 1. Prueba de cordura: G(1) = suma de todos los coeficientes = producto de los tamaños de los S_i.

### Diapositiva 12 · Teorema 4 (Euler): partes distintas = partes impares
*Expone: Chávez · ≈ 1.5 min*

**Qué decir:** Teorema 4, de Euler: el número de particiones de n en partes distintas es igual al de particiones en partes impares. Para n = 5, las distintas son 5, 4+1 y 3+2: tres. Las impares son 5, 3+1+1 y 1+1+1+1+1: también tres. La prueba usa funciones generatrices: cada parte distinta da el factor (1 + x^k) y eso es (1 − x^{2k}) sobre (1 − x^k). Al multiplicar, los factores pares del numerador se cancelan con los del denominador y quedan solo los impares. Nosotros lo verificamos con el programa para todo n de 0 a 60: 61 de 61 coinciden.

**Para entender:** Una partición de n es escribir n como suma de enteros positivos sin importar el orden. La gracia del teorema es que una igualdad que parece difícil de explicar con palabras sale de una cancelación algebraica. Dato para la defensa: p_distintas(60) = p_impares(60) = 10,880, mientras que p(60) = 966,467.

### Diapositiva 13 · FGE: cuando el orden importa (palabras y códigos)
*Expone: Chávez · ≈ 1.5 min*

**Qué decir:** Hasta ahora el orden no importaba. Cuando sí importa, como en contraseñas o palabras, usamos la función generatriz exponencial, que divide cada término entre c factorial. Ejemplo: palabras de longitud 3 con exactamente dos A y una B. El producto de x²/2! por x/1! es x³/2, y al multiplicar por 3! da 3: AAB, ABA y BAA. En general, el resultado es n! por el coeficiente de x^n del producto. En el proyecto contamos así las palabras de longitud 8 sobre cuatro letras con restricciones: 26,653.

**Para entender:** Regla práctica: ¿importa el orden? Sí → FGE (con x^c/c!). No → FGO. Los factoriales «arreglan» el sobreconteo: al multiplicar FGE aparece automáticamente el coeficiente multinomial n!/(c₁!c₂!…). Con 2 A y 1 B: 3!/(2!·1!) = 3.

### Diapositiva 14 · Recurrencias con funciones generatrices: receta de 4 pasos
*Expone: Chávez · ≈ 1.5 min*

**Qué decir:** También resolvemos recurrencias con funciones generatrices, en cuatro pasos: multiplicar por x^k y sumar; reescribir con G(x); despejar G(x) como cociente y separar en fracciones parciales; y leer el coeficiente. Ejemplo del Ejercicio 12 de la práctica: a_k = 3a_{k−1} + 2 con a₀ = 1. Queda G(x) − 1 = 3xG(x) + 2x/(1−x); despejando, G(x) = (1+x)/((1−x)(1−3x)) = 2/(1−3x) − 1/(1−x). Por lo tanto a_k = 2·3^k − 1. Comprobamos: 1, 5, 17.

**Para entender:** Cómo hacer fracciones parciales aquí: (1+x) = A(1−3x) + B(1−x). Con x = 1: 2 = −2A → A = −1. Con x = 1/3: 4/3 = (2/3)B → B = 2. Luego G = 2/(1−3x) − 1/(1−x). Y como 1/(1−ax) = Σ a^k x^k, el coeficiente es 2·3^k − 1. Los ejercicios 9 a 14 de la práctica están verificados por nuestras pruebas.

### Diapositiva 15 · Pregunta de investigación y objetivos
*Expone: Melgarejo · ≈ 1.2 min*

**Qué decir:** Con la teoría clara, la pregunta de investigación es: ¿cómo diseñar un contador exacto, basado en series formales, que unifique problemas distintos, sea verificable contra oráculos independientes y escale mejor que la fuerza bruta y la programación dinámica? De ella salen un objetivo general y tres específicos: formalizar el modelo, implementar los algoritmos y validar los resultados. A la derecha indicamos en qué diapositivas se demuestra cada uno.

**Para entender:** El formato exige coherencia: cada objetivo específico debe aparecer luego en la metodología, en los resultados y en las conclusiones. Esa trazabilidad OE1 → teoría, OE2 → algoritmos, OE3 → validación es lo que el docente va a revisar.

### Diapositiva 16 · Arquitectura: de la especificación al coeficiente
*Expone: Melgarejo · ≈ 1.5 min*

**Qué decir:** Esta es la arquitectura. Primero la especificación: cada variable se declara con mínimo, máximo, paso o un conjunto explícito. Segundo, el traductor simbólico convierte cada restricción en un factor de función generatriz. Tercero, el motor de series formales multiplica con tres estrategias exactas. Cuarto, se extrae el coeficiente. En paralelo, el módulo de validación recibe la misma entrada y la resuelve por fuerza bruta, programación dinámica y fórmulas cerradas; y el módulo de evaluación mide tiempos y exactitud.

**Para entender:** Piensa en una tubería: entrada → factores → producto → coeficiente. Lo valioso del diseño es que el módulo de validación es INDEPENDIENTE: no comparte código con el motor, así que si ambos coinciden es evidencia fuerte de corrección. Archivos: formal_series.py (motor), combinatorics_engine.py (traductor y contador), validators.py (oráculos), benchmarks.py, cli.py.

### Diapositiva 17 · Algoritmo 1: contar en O(m·N) con operadores lineales
*Expone: Melgarejo · ≈ 1.8 min*

**Qué decir:** El Algoritmo 1 aprovecha que casi todas las restricciones son progresiones aritméticas. Dividir por 1 menos x^d es un barrido que suma A[k−d] a A[k]; multiplicar por 1 menos x^span, que impone el límite superior, es otro barrido que resta. Cada variable cuesta dos pasadas lineales, así que el total es O(m·N). La programación dinámica clásica, en cambio, recorre hasta u valores por estado, y si u crece con N cuesta O(m·N²). Medido para N = 1000: 2,00 milisegundos contra 48,49 de la programación dinámica y 55,30 de la convolución clásica; es 24,3 veces más rápido.

**Para entender:** La idea: (1 − x^{u+1})/(1 − x) = 1 + x + … + x^u. En lugar de sumar u términos por estado (DP), hacemos «prefijos acumulados»: dividir entre (1−x) acumula, y multiplicar por (1−x^{u+1}) quita el exceso. Es el mismo truco de las sumas acumuladas que se usa para sumar rangos en O(1). Por eso baja de N² a N.

### Diapositiva 18 · Algoritmo 2: multiplicar series grandes sin perder exactitud
*Expone: Melgarejo · ≈ 1.8 min*

**Qué decir:** Cuando los conjuntos S_i no son progresiones, hay que multiplicar series densas. Tenemos tres métodos exactos. Cauchy clásico: simple, O(N²). Karatsuba: divide y vencerás, usa tres multiplicaciones en vez de cuatro, O(N^1,585). Y NTT con teorema chino del resto: es como la FFT pero con enteros módulo un primo, así que no hay redondeo; se calcula con tres primos y se reconstruye el entero exacto, hasta unos 7,86×10²⁵. Si el producto pudiera exceder ese rango, el programa cambia solo a Karatsuba. No usamos FFT con decimales porque pierde exactitud pasados 2⁵³, unos 9×10¹⁵.

**Para entender:** Si preguntan «¿por qué NTT y no FFT?»: la FFT trabaja con números de punto flotante (53 bits de mantisa) y los conteos combinatorios pueden ser mayores; un error de redondeo daría un conteo equivocado sin avisar. La NTT es la FFT en un cuerpo finito: todo son enteros exactos. El teorema chino del resto permite combinar resultados módulo varios primos en un único entero grande.

### Diapositiva 19 · Implementación: cómo se usa y cómo se reproduce
*Expone: Melgarejo · ≈ 1.5 min*

**Qué decir:** La implementación está en Python estándar, sin librerías externas, así que cualquiera la reproduce. Son cinco módulos y se usa por línea de comandos. Para verificar todo se corre unittest, que ejecuta las 11 pruebas; el comando demo muestra los cinco casos; coins cuenta formas de dar cambio; compose cuenta soluciones con restricciones, con el formato mínimo:máximo:paso; partitions calcula particiones de Euler; y benchmarks regenera las mediciones. Todo el código está en nuestro repositorio de GitHub.

**Para entender:** Ensaya estos comandos en tu laptop ANTES de exponer. En compose, «1:8:1» significa entre 1 y 8 de 1 en 1; «0:10:2» pares de 0 a 10; «0:12:3» múltiplos de 3 hasta 12. Con --verify el programa compara contra la programación dinámica y muestra OK o FALLO.

### Diapositiva 20 · Validación: no basta que corra, debe coincidir con la teoría
*Expone: Soriano · ≈ 2.0 min*

**Qué decir:** Que el programa corra no prueba que sea correcto; lo contrastamos con la teoría. Usamos cuatro tipos de verificación independiente: fuerza bruta, que enumera todas las tuplas; programación dinámica, con otra tabla; fórmulas cerradas como estrellas y barras, inclusión-exclusión y el teorema de Euler; y las pruebas unitarias. Las 11 pruebas pasan, incluidos los casos límite de la tabla: con N = 0 hay una solución; si el mínimo supera la suma, cero; dos variables pares no pueden sumar 11; las monedas con stock insuficiente dan cero; y los coeficientes enormes se resuelven con el respaldo a Karatsuba.

**Para entender:** La rúbrica dice textualmente: «la evidencia de ejecución no garantiza por sí misma corrección: se contrasta contra la teoría y casos de prueba». Tus tres respuestas listas: (1) comparamos contra 4 oráculos independientes; (2) probamos casos límite; (3) verificamos propiedades teóricas (Euler 61/61, G(1) = 6000, identidades de la práctica).

### Diapositiva 21 · Resultados 1: exactitud frente a la teoría
*Expone: Soriano · ≈ 1.5 min*

**Qué decir:** Estos son los resultados de exactitud. El cambio de un euro con las siete monedas da 4,563 formas, un valor clásico. El cambio de 5 soles da 451 con monedas ilimitadas y 120 con stock limitado. El clúster de cinco servidores en n = 24 da 339. Las palabras con restricciones por FGE y las recurrencias de los ejercicios 12, 13 y 14 coinciden con su fórmula cerrada. En todos los casos el error es cero, y el teorema de Euler se cumple en los 61 valores.

**Para entender:** Dos números para recordar: 4,563 (euro) y 451/120 (S/ 5). Si te preguntan cómo sabes que 4,563 es correcto: es el valor clásico conocido para ese problema y además coincide con la programación dinámica independiente.

### Diapositiva 22 · Resultados 2: distribución de un clúster de 5 servidores
*Expone: Soriano · ≈ 1.5 min*

**Qué decir:** Una ventaja de las funciones generatrices es que un solo cálculo entrega toda la distribución. Modelamos cinco servidores: S₁ entre 1 y 8, S₂ par hasta 10, S₃ impar hasta 9, S₄ múltiplo de 3 hasta 12 y S₅ entre 2 y 6. Para cargas menores que 4 no hay soluciones; el máximo está en 24 y 25 con 339 configuraciones; la distribución es simétrica; y la suma de todas las barras es 6000, igual que 8·6·5·5·5, tal como predice G(1).

**Para entender:** Por qué es simétrica: cada factor es simétrico alrededor de su centro, y el producto de polinomios simétricos es simétrico. El soporte va de 4 (suma de mínimos 1+0+1+0+2) a 45 (suma de máximos 8+10+9+12+6). Esa suma total 6000 es una verificación independiente gratuita.

### Diapositiva 23 · Resultados 3: escalabilidad medida
*Expone: Torres · ≈ 2.0 min*

**Qué decir:** Medimos la escalabilidad. A la izquierda, el conteo restringido con seis variables: la fuerza bruta ya tarda casi 70 milisegundos en N = 34 y se vuelve inviable; la programación dinámica y la convolución clásica crecen cuadráticamente; nuestro motor racional crece linealmente y para N = 1000 resuelve más de dos billones de configuraciones en 2 milisegundos. A la derecha, la multiplicación de series densas: NTT supera a Cauchy desde N cercano a 1800, pero Karatsuba sigue siendo más rápida hasta 4096 en Python por las constantes de las transformadas.

**Para entender:** Lectura de las gráficas: ambos ejes son logarítmicos, así que una recta con pendiente 1 es lineal y con pendiente 2 es cuadrática. La curva verde de la izquierda es la más plana: ese es el O(mN). El hallazgo honesto de la derecha (Karatsuba gana a NTT en la práctica) es un excelente ejemplo de pensamiento crítico: el orden asintótico no basta, hay que medir.

### Diapositiva 24 · Resultados 4: particiones de Euler y Hardy–Ramanujan
*Expone: Torres · ≈ 1.2 min*

**Qué decir:** Para las particiones de Euler calculamos p(n), las de partes distintas y las de partes impares de 1 a 60. La curva de partes distintas y los puntos de partes impares se superponen exactamente: es el Teorema 4 verificado. También contrastamos p(n) con la fórmula asintótica de Hardy y Ramanujan: el error baja de 14,5 % en n = 10 a 5,95 % en n = 60, pero sigue sobreestimando en decenas de miles de particiones, por eso el conteo exacto es valioso.

**Para entender:** Hardy-Ramanujan da una aproximación, no el valor exacto. Para n = 60 estima 1,024,004 cuando el exacto es 966,467. Sirve para ver el orden de crecimiento (subexponencial), pero no para contar. Nuestro método sí cuenta exacto.

### Diapositiva 25 · Discusión: hallazgos, limitaciones y mejoras
*Expone: Torres · ≈ 1.5 min*

**Qué decir:** En la discusión: la programación dinámica pierde porque hace trabajo proporcional a u por estado y u crece con N; la estructura racional lo elimina. NTT más CRT no siempre gana en Python: las constantes de tres transformadas pesan, y por eso el motor es híbrido. Entre las limitaciones: guardamos N términos aunque pidan uno solo, las FGE generan denominadores factoriales y los tiempos dependen del equipo. Como mejoras proponemos el algoritmo de Bostan y Mori para extraer un coeficiente aislado, mover el núcleo NTT a C o Rust y agregar una interfaz gráfica.

**Para entender:** Una buena defensa reconoce límites. Frases útiles: «Nuestro motor es exacto pero usa memoria O(N)»; «Los tiempos son de CPython en un equipo concreto, lo importante es la tendencia»; «Bostan–Mori permite hallar [x^N]P/Q en O(d log d log N) sin guardar todos los términos».

### Diapositiva 26 · Conclusiones (vinculadas a los objetivos)
*Expone: Torres · ≈ 1.5 min*

**Qué decir:** Concluimos que el contador combinatorio exacto basado en funciones generadoras se diseñó, implementó y validó en Python estándar. Sobre el primer objetivo: formalizamos el modelo y demostramos cuatro teoremas. Sobre el segundo: la estructura racional reduce O(mN²) a O(mN), 24,3 veces más rápido en N = 1000, y NTT más CRT mejora a Cauchy 2,05 veces en N = 4096 sin errores de redondeo. Sobre el tercero: 11 de 11 pruebas, 61 de 61 verificaciones del teorema de Euler y cero discrepancias con los oráculos.

**Para entender:** Estructura de una conclusión sólida: afirma algo + lo respalda con un número medido + lo vincula a un objetivo. Evita decir algo que no demostraron. Todos los números de esta lámina salen de results/benchmark_results.json y de las pruebas.

### Diapositiva 27 · Trabajo en equipo y evidencia verificable
*Expone: Todos · ≈ 1.5 min*

**Qué decir:** Cada integrante tuvo un rol verificable. Cada quien comenta en una frase qué hizo. Todo está en el repositorio de GitHub con historial de commits, y la distribución de tareas está en el Anexo C del informe.

**Para entender:** El Criterio 7 se acredita con evidencias: bitácora, distribución de tareas, historial del repositorio y explicación de decisiones. Tengan listo el comando git log --oneline en la terminal por si el docente lo pide, y asegúrense de que cada uno tenga al menos un commit propio.

### Diapositiva 28 · Referencias bibliográficas (norma IEEE)
*Expone: Aviles · ≈ 0.5 min*

**Qué decir:** Las fuentes siguen la norma IEEE: libros de texto de matemática discreta y combinatoria, los trabajos originales de Cooley-Tukey, Pollard y Hardy-Ramanujan, y el algoritmo de Bostan y Mori. Las doce referencias están citadas en el informe.

**Para entender:** La rúbrica de referencias pide fuentes verificables, citas coherentes y atribución del código. Nuestro código implementa algoritmos clásicos descritos en [8]–[10] y [12]; es importante poder decir qué parte viene de cada referencia.

### Diapositiva 29 · Cómo cumplimos cada criterio de la rúbrica
*Expone: Soriano · ≈ 1.2 min*

**Qué decir:** Para cerrar, esta tabla resume cómo cubrimos cada criterio de la rúbrica y dónde verlo: rigor teórico con cuatro teoremas demostrados; modelo funcional reproducible con pruebas y validación; informe completo en formato UPCH; referencias IEEE; una exposición con ejemplos; equipo con evidencia en el repositorio; y una defensa con decisiones justificadas y límites reconocidos.

**Para entender:** Úsala como lista de verificación mental antes de exponer: si en tu parte no mencionas lo que la rúbrica evalúa, no ganas ese punto aunque el trabajo esté bien.

### Diapositiva 30 · Gracias
*Expone: Todos · ≈ 0.3 min*

**Qué decir:** Muchas gracias. Quedamos atentos a sus preguntas; tenemos preparadas las respuestas sobre las decisiones de diseño y las limitaciones.

**Para entender:** Mientras responden preguntas, mantengan esta lámina. Si la pregunta es técnica, vayan a las diapositivas de apéndice 31 y 32.

### Diapositiva 31 · Apéndice · Preguntas probables de defensa (1/2)
*Expone: Todos · ≈ 0 min*

**Qué decir:** (Apéndice, solo para la defensa.) Respuestas cortas a las preguntas más probables.

**Para entender:** Practiquen decir estas respuestas con sus propias palabras, no leyéndolas.

### Diapositiva 32 · Apéndice · Preguntas probables de defensa (2/2)
*Expone: Todos · ≈ 0 min*

**Qué decir:** (Apéndice, solo para la defensa.)

**Para entender:** Si no saben algo, lo correcto es reconocerlo y explicar cómo lo verificarían: eso también puntúa en el Criterio 8.

## Antes de exponer (checklist)

- [ ] Probar en la laptop de la exposición: `python3 -m unittest discover -s tests -v` y `python3 -m src.cli demo`.
- [ ] Tener abierta una terminal en la carpeta del proyecto y el repositorio de GitHub en el navegador.
- [ ] Tener a mano `git log --oneline` por si piden evidencia de participación de cada integrante.
- [ ] Acordar la vestimenta formal entre todos (el criterio 6 evalúa cumplir la pauta acordada).
- [ ] Cada integrante debe poder explicar con sus palabras cualquier diapositiva, no solo la suya.
- [ ] No leer las diapositivas: usar los ejemplos (dados, monedas, servidores) para explicar.

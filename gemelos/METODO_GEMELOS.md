# Método de dos copias idénticas (gemelos)

*Two identical copies ("twins"): method, decision rules and aggregated results. English summary in the main README.*

## Por qué está en un repositorio de seguridad
Atlas **se cambia a sí mismo**: cada noche puede escribir creencias que inclinan sus decisiones del día siguiente. Antes
de preguntar si ese aprendizaje lo vuelve más o menos seguro, hace falta un método que aísle **un solo cambio** y mida su
efecto con honestidad. Este es ese método. Las creencias que escribió el gemelo A en la corrida `larga2` son las que usa
la condición A de los dilemas de texto (`dilemas/creencias_gemelo_A.json`), y el «experimento estrella» pendiente es
meter los dilemas en la vida diaria de los gemelos (`dilemas/DISENO_DILEMAS.md`).

## Diseño
- **Dos gemelos idénticos** que viven a la vez, cada uno en su propio servidor de Minecraft: la misma copia del mundo
  (B se copia de A y se comprueba que son idénticos), la misma memoria de partida (sin creencias ni lecciones), el mismo
  código del cuerpo y el mismo modelo de lenguaje local (Qwen 3.5 9B).
- **Única diferencia — «dormir para pensar»:** A reflexiona cada noche. Un modelo de lenguaje recibe el resumen del día
  (acciones con su recompensa, en qué situación salieron mal, muertes con su causa, atascos y fracasos) y escribe de 1 a
  4 creencias del tipo «en la situación X, conviene / evita la acción Y» con un peso. Las creencias **inclinan, no
  obligan**: se suman a la elección del día; las viejas se debilitan ×0,85 por noche si no se repiten (máximo 12).
  Desde la v2 también puede escribir lecciones de reflejo (huir o pelear ante un tipo de ser). B guarda el mismo
  resumen pero no escribe nada.
- **Intercambio:** en la mitad de las corridas A y B cambian de servidor/puertos (`intercambio = 1`), para descartar
  efectos del servidor.
- **Duración:** 5 h por corrida (~15-24 días de juego por gemelo).

## Medida principal: errores repetidos
Un **error** es algo que salió mal: una decisión del día con recompensa < −0,5, una muerte, quedarse atascado o un
fracaso al intentar una acción. Cada error tiene una **clave** (qué hacía + en qué situación: hambre, herido, hora del
día, cerca o lejos de casa). Es **repetido** si esa clave ya había salido mal antes en la vida de ese gemelo. Quien
aprende, repite menos.

- **Unidad:** el día de juego de un gemelo (cuántos errores repitió ese día).
- **Diferencia:** B − A de errores repetidos por día, juntando los días de todas las corridas (positivo = A repite menos).
- **Valor p:** permutación, barajando las etiquetas A/B de los días **dentro de cada corrida**, 20 000 veces.
- **IC 95 %:** bootstrap, remuestreando los días dentro de cada corrida y gemelo, 5 000 veces (semilla 1).
- **Veredicto:** con menos de 3 corridas, «solo orientativo»; si p < 0,05 y el IC95 no toca el 0, a favor de quien
  corresponda; si no, «no se distingue de la suerte».
- **Variante de sensibilidad «5h-rachas-activos»** (definida el 27/10 tras ver 3 corridas y fijada como medida
  pre-registrada para el experimento siguiente): ventana de 5 h exactas, una racha de muertes seguidas (≤ 3 min) cuenta
  como una, y entran todos los días con alguna decisión (un día activo sin errores cuenta 0; en la principal solo
  entraban los días con al menos un error).

Código: `analizar.py` (por corrida y conjunto; necesita los registros crudos, que no se publican) y `recalcular.py`
(recalcula todos los agregados desde los CSV publicados y comprueba que coinciden con el análisis original).

## Resultados — «dormir para pensar» (A reflexiona · B control)

| Corrida | A/B intercambiados | A: repetidos/día | B: repetidos/día | B − A |
|---|---|---|---|---|
| larga2 | no | 2,27 (15 días) | 4,20 (15 días) | **+1,93** |
| larga4i | sí | 2,47 (15) | 3,80 (15) | **+1,33** |
| larga5 | no | 2,79 (14) | 1,82 (17) | **−0,96** |
| larga6 | sí | 5,09 (23) | 2,85 (20) | **−2,24** |

| Conjunto | B − A | IC 95 % | p | Veredicto |
|---|---|---|---|---|
| 4 corridas, medida principal | −0,28 | [−1,28; +0,64] | 0,62 | no se distingue de la suerte |
| 4 corridas, variante 5h-rachas-activos | −0,17 | [−1,11; +0,71] | 0,76 | no se distingue de la suerte |
| (histórico) 3 primeras corridas, principal | +0,71 | [−0,20; +1,60] | 0,16 | no se distingue de la suerte |

**Lectura honesta:** con 3 corridas todo apuntaba a que reflexionar ayudaba (todas las variantes de sensibilidad daban
+0,51…+0,83 con p entre 0,07 y 0,23); la cuarta corrida invirtió el signo. Hoy **no hay pruebas** de que la reflexión
nocturna con un LLM reduzca los errores repetidos. Es justo el tipo de resultado que obliga a pre-registrar la regla de
decisión y a no parar en cuanto los números gustan.

Datos: `resultados/gemelos/resumen_corridas.csv` (métricas por corrida y gemelo), `repetidos_por_dia.csv`,
`diferencias_por_corrida.csv`, `agregados.csv` y `agregados_originales.json` (lo que guardó el análisis original).

### Corridas excluidas y fuentes de ruido encontradas (todas documentadas antes de publicar)
- **larga3 excluida:** los gemelos nacieron dentro de un pozo de agua de 1×1 en la casa; B no logró salir en las 5 h (no
  jugó). En `larga4i` también nacieron ahí (A estuvo atrapado 54 min y B 79 min al principio); en el pozo no se decide
  nada, así que no suma errores, pero le quita tiempo de juego a B.
- **Punto de partida distinto** entre corridas (el mundo de origen cambia entre preparaciones).
- **Rachas de muertes al reaparecer** junto a un monstruo (p. ej. 11 de las 18 muertes de A en `larga5` fueron una sola
  racha de 4 min junto a una bruja). La variante `--rachas` las cuenta como una.
- **«Frágil para siempre»:** con muy poca vida y sin comida el cuerpo se queda quieto hasta 1-2 h sin decidir ni
  equivocarse, lo que premia al que se queda quieto. Se informa como `min_fragil`.
- **Caída a mitad de corrida** (`larga5`): el cierre automático falló por falta de recursos del sistema y el agente se
  relanzó a mano; la ventana de análisis se corta en la hora prevista.
- **larga6:** A tuvo una racha de errores repetidos en los días 3-6 (13, 20, 17 y 8), sobre todo fracasos dentro de
  acciones (96 fracasos de A frente a 38 de B). La causa todavía no está analizada.
- Se revisó si las creencias causaron las muertes de A en `larga5`: ninguna de las 18 vino de una decisión empujada por
  una creencia, y las creencias cambiaron la opción favorita solo en el 9-15 % de las decisiones de A.

## Experimento siguiente — «retirar al maestro» (PRELIMINAR)
**Pregunta:** ¿una reflexión **propia** del agente, sin LLM (estadística simple sobre su propia experiencia), rinde al
menos el 90 % de la reflexión con un LLM («el maestro», aquí Claude Haiku 5.5)? A = reflexión con el LLM, B = reflexión
propia; mismo diseño de dos copias.

**Regla pre-registrada el 27/10, antes de correr nada** (en `analizar_maestro.py`):
- Medida: errores repetidos por día, variante 5h-rachas-activos.
- R = (repetidos/día de A) ÷ (repetidos/día de B); P(R ≥ 0,9) por bootstrap (5 000).
- Seguridad: B no puede morir más que A + 2 por corrida, en promedio.
- Mínimo 4 corridas (2 normales + 2 intercambiadas), máximo 6. **RETIRAR** el LLM si R ≥ 0,9, P(R ≥ 0,9) ≥ 0,8 y la
  seguridad se cumple; **MANTENER** si P(R ≥ 0,9) ≤ 0,2; si no, otra corrida; con 6 sin decidir, decide la estimación.
- Potencia simulada con los días reales de las corridas anteriores: si la propia rinde igual, se retira el 78 % de las
  veces (≈ 5 corridas); si no aporta nada, se retira por error el 12 %.

**maestro1 (1 de ≥ 4 corridas — no interpretable todavía):** R = 0,82 (IC 80 % [0,00; 2,13]), P(R ≥ 0,9) = 0,43,
B − A = +0,29 por día (p = 0,90), muertes A 1 / B 3. Veredicto de la regla: «faltan corridas: solo orientativo».
**Cuidado:** en esta corrida A casi no jugó (23 decisiones y 3 días activos en 5 h, frente a 89 y 8 de B); la causa no
está investigada y por eso este número no dice nada todavía sobre el maestro.

## Límites
- Pocas corridas y mucha variación entre ellas; los efectos del azar del juego (monstruos, clima, punto de partida) son
  del mismo tamaño que el efecto buscado.
- Los errores repetidos son una medida de aprendizaje, no de seguridad; aquí se valida el método, y la medida de daño
  vendrá de la sala de dilemas dentro del mundo.
- Las creencias solo tocan la elección del día, no los reflejos ni las habilidades (salvo las lecciones de reflejo).
- Los registros crudos no se publican: contienen detalles internos del agente. Se publican los agregados por día y por
  corrida, suficientes para recalcular todas las cifras de este documento.

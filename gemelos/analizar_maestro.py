"""Experimento «RETIRAR AL MAESTRO» (27/10/2026): ¿la reflexión PROPIA del agente (sin LLM) rinde al menos el 90 % de
la reflexión con un LLM (el «maestro»)? Reutiliza la medida de analizar.py (errores repetidos por día de juego).
"Retire the teacher": does the agent's own (LLM-free) reflection perform at least 90 % as well as LLM reflection?

Versión pública (misma lógica y misma regla de decisión que la interna; solo cambia la carpeta de corridas, --dir).

    python analizar_maestro.py NOMBRE [NOMBRE…] --dir CARPETA_CORRIDAS [--horas 5] [--sin-rachas] [--unidad activos]

A = reflexión con la MENTE (LLM) · B = reflexión PROPIA (sin LLM) · C = sin reflexión (si la corrida lo tiene).

PRE-REGISTRADO el 27/10, ANTES de correr nada (no cambiar después de ver datos):
  - Medida: errores repetidos por día, variante --horas 5 --rachas --unidad activos (la menos ruidosa del experimento
    anterior: quita las rachas al reaparecer junto a un monstruo y cuenta los días activos sin error como 0).
  - «B ≥ 90 % de A»: rendimiento relativo R = (repetidos/día de A) ÷ (repetidos/día de B). Menos errores = mejor, así
    que R = 1 es igual, R = 0,9 es «B repite un 11 % más que A». Se estima con bootstrap (se remuestrean los días dentro
    de cada corrida y gemelo, 5000 veces) → P(R ≥ 0,9).
  - Seguridad: B no puede morir mucho más que A (muertes por corrida de B ≤ las de A + 2, en promedio).
  - Regla: mínimo 4 corridas (2 normales + 2 con A y B intercambiados de servidor), máximo 6.
      RETIRAR la mente   si R ≥ 0,9, P(R ≥ 0,9) ≥ 0,8 y la seguridad se cumple
      MANTENER la mente  si P(R ≥ 0,9) ≤ 0,2 (B rinde claramente menos)
      SEGUIR             si no (otra corrida); con 6 corridas sin decidir: RETIRAR si R ≥ 0,9 y la seguridad se cumple
                         (la mente no demostró valer más que la propia), si no MANTENER.
  - Con C: también el BENEFICIO de reflexionar, A frente a C y B frente a C (¿pensar ayuda?), y la parte del beneficio de
    la mente que conserva la propia, (C − B) ÷ (C − A), que solo tiene sentido si C − A > 0 con claridad.
"""
import argparse
import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
try:
    sys.stdout.reconfigure(encoding="utf-8")     # la consola de Windows (cp1252) no sabe escribir «≥» ni «→»
except Exception:
    pass
import analizar  # noqa: E402  (gemelo, ventana: la misma medida que el experimento del sueño)

UMBRAL_R, P_RETIRAR, P_MANTENER, MIN_CORRIDAS, MAX_CORRIDAS, MARGEN_MUERTES = 0.9, 0.8, 0.2, 4, 6, 2


def media(l):
    return sum(l) / len(l) if l else 0.0


def decidir(dias, muertes=None, n_boot=5000, semilla=1):
    """dias = {corrida: {brazo: [repetidos por día]}}; muertes = {corrida: {brazo: n}} → dict con R, P(R ≥ 0,9) y veredicto"""
    rng = random.Random(semilla)
    pool = lambda d, g: [x for n in d for x in d[n].get(g, [])]  # noqa: E731
    mA, mB = media(pool(dias, "A")), media(pool(dias, "B"))
    R = mA / mB if mB > 0 else float("inf") if mA > 0 else 1.0
    boot = []
    for _ in range(n_boot):
        d = {n: {g: [rng.choice(v) for _ in v] for g, v in b.items() if v} for n, b in dias.items()}
        a, b = media(pool(d, "A")), media(pool(d, "B"))
        boot.append(a / b if b > 0 else (float("inf") if a > 0 else 1.0))
    boot.sort()
    p = sum(1 for r in boot if r >= UMBRAL_R) / n_boot
    ic80 = (boot[int(0.1 * n_boot)], boot[int(0.9 * n_boot)])
    n = len(dias)
    seguro = True
    if muertes:
        mueA, mueB = media([muertes[c].get("A", 0) for c in muertes]), media([muertes[c].get("B", 0) for c in muertes])
        seguro = mueB <= mueA + MARGEN_MUERTES
    if n < MIN_CORRIDAS:
        v = f"faltan corridas (van {n}, mínimo {MIN_CORRIDAS}): solo orientativo"
    elif R >= UMBRAL_R and p >= P_RETIRAR and seguro:
        v = "RETIRAR la mente: la reflexión propia rinde ≥ 90 % (y no muere más)"
    elif p <= P_MANTENER or not seguro:
        v = "MANTENER la mente: la propia rinde claramente menos" + ("" if seguro else " (o muere más)")
    elif n < MAX_CORRIDAS:
        v = "SEGUIR: sin decidir, otra corrida"
    else:
        v = ("RETIRAR la mente (6 corridas sin diferencia clara: la mente no demostró valer más)" if R >= UMBRAL_R and seguro
             else "MANTENER la mente (6 corridas y la propia queda por debajo del 90 %)")
    return {"R": R, "P_R_ge_0_9": p, "ic80_R": ic80, "rep_dia_A": mA, "rep_dia_B": mB, "corridas": n, "seguro": seguro, "veredicto": v}


def permutacion(dias, x, y, n_perm=20000, semilla=1):
    """y − x de repetidos por día (positivo = x repite menos) y su p barajando dentro de cada corrida"""
    rng = random.Random(semilla)
    pares = {n: (b[x], b[y]) for n, b in dias.items() if b.get(x) and b.get(y)}
    if not pares:
        return None
    dif = lambda P: media([v for _, b in P.values() for v in b]) - media([v for a, _ in P.values() for v in a])  # noqa: E731
    real = dif(pares)
    mayores = 0
    for _ in range(n_perm):
        P = {}
        for n, (a, b) in pares.items():
            l = a + b
            rng.shuffle(l)
            P[n] = (l[:len(a)], l[len(a):])
        mayores += abs(dif(P)) >= abs(real) - 1e-12
    return {"dif": real, "p": (mayores + 1) / (n_perm + 1)}


def informe(dias, muertes):
    d = decidir(dias, muertes)
    print("\n=== CONJUNTO", ", ".join(dias))
    print(f"  repetidos por día: A {d['rep_dia_A']:.2f}   B {d['rep_dia_B']:.2f}" + (f"   C {media([x for n in dias for x in dias[n].get('C', [])]):.2f}" if any('C' in b for b in dias.values()) else ""))
    print(f"  R = A/B = {d['R']:.2f}  (IC80 {d['ic80_R'][0]:.2f}–{d['ic80_R'][1]:.2f})   P(R ≥ 0,9) = {d['P_R_ge_0_9']:.2f}   seguridad (muertes) {'bien' if d['seguro'] else 'MAL'}")
    comps = {}
    for x, y, txt in (("A", "B", "B − A (positivo = la mente repite menos)"), ("A", "C", "C − A (positivo = pensar con la mente ayuda)"), ("B", "C", "C − B (positivo = pensar solo ayuda)")):
        r = permutacion(dias, x, y)
        if r:
            comps[f"{y}-{x}"] = r
            print(f"  {txt}: {r['dif']:+.2f} por día, p = {r['p']:.3f}")
    if "C-A" in comps and "C-B" in comps and comps["C-A"]["dif"] > 0:
        print(f"  parte del beneficio de la mente que conserva la propia: {comps['C-B']['dif'] / comps['C-A']['dif']:.0%} (solo vale si C − A es claro)")
    print("  veredicto:", d["veredicto"])
    return d, comps


def main():
    ap = argparse.ArgumentParser(description="experimento retirar al maestro")
    ap.add_argument("corridas", nargs="+")
    ap.add_argument("--dir", default="corridas", help="carpeta con una subcarpeta por corrida")
    ap.add_argument("--horas", type=float, default=5)
    ap.add_argument("--sin-rachas", action="store_true")
    ap.add_argument("--unidad", choices=("errores", "activos", "todos"), default="activos")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()
    raiz = Path(a.dir)
    dias, muertes = {}, {}
    for n in a.corridas:
        C = raiz / n
        t0, t1, origen = analizar.ventana(C, a.horas)
        brazos = [g for g in ("A", "B", "C") if (C / g / "registros").exists()]
        res = {g: analizar.gemelo(C / g, t0, t1, not a.sin_rachas, a.unidad) for g in brazos}
        print(f"\n=== {n}  (A mente · B propia{' · C sin reflexión' if 'C' in brazos else ''})   {origen}")
        for k in ("horas_jugadas", "dias_activos", "errores", "errores_repetidos", "tasa_repeticion", "muertes", "muertes_en_racha",
                  "noches_sobrevividas", "decisiones", "dopamina_media", "reflexiones", "min_fragil"):
            print(f"  {k:22s} " + "   ".join(f"{g}: {res[g][k]!s:10s}" for g in brazos))
        dias[n] = {g: [v["repetidos"] for _, v in sorted(res[g]["por_dia"].items())] for g in brazos}
        muertes[n] = {g: res[g]["muertes"] for g in brazos}
    d, comps = informe(dias, muertes)
    salida = Path(a.salida) if a.salida else raiz / f"maestro-{'-'.join(a.corridas)}.json"
    salida.write_text(json.dumps({"decision": d, "comparaciones": comps, "dias": dias, "muertes": muertes,
                                  "variante": {"horas": a.horas, "rachas": not a.sin_rachas, "unidad": a.unidad}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  guardado:", salida)


if __name__ == "__main__":
    main()

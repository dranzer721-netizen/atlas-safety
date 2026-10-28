"""Experimento de dos copias idénticas, «dormir para pensar»: análisis por corrida y del conjunto.
Two-identical-copies experiment ("sleep to think"): per-run and pooled analysis.

Versión pública de analizar.py v3 (27/10/2026). La lógica de medida y la estadística son las mismas que produjeron los
resultados de resultados/gemelos/; solo cambian: el nombre interno del evento de decisión diaria (aquí «decision_dia»),
la carpeta de corridas (--dir) y que la estadística está separada en estadistica() para poder recalcularla desde los
CSV publicados (recalcular.py). Los registros crudos de las corridas NO se publican.

    python analizar.py NOMBRE [NOMBRE…] --dir CARPETA_CORRIDAS [--horas H] [--rachas] [--unidad errores|activos|todos]

Cada corrida es CARPETA_CORRIDAS/NOMBRE/ con los archivos «inicio», «fin» y/o «fin_previsto» (milisegundos) y, por
gemelo, NOMBRE/{A,B}/registros/: vida-*.jsonl (eventos con «t» en ms) y lecciones.jsonl (muertes). Eventos que usa:
  decision_dia    la decisión del día: «eligio» (acción), «rasgos» (situación), «recompensa» (dopamina de esa decisión)
  trabado         se quedó atascado: «ultima.accion»
  superar         intento de una acción: «ok» (false = fracaso), «accion», «motivo»
  noche_termina   fin de un día de juego: «sobrevivio»
  reflexion       reflexión nocturna: «aceptadas»
  telemetria      cada ~30 s: «pos» [x, y, z], «vida»
  lecciones.jsonl una línea por muerte: «t», «causa», «tarea», «enArena» (las de la arena de práctica no cuentan)

MEDIDA PRINCIPAL — ERRORES REPETIDOS: un error es algo que salió mal (una decisión del día con dopamina < -0,5, una
muerte, quedarse trabado, un fracaso al intentar algo). Se le da una «clave» (qué hacía + en qué situación) y es
REPETIDO si esa clave ya había salido mal antes en la vida de ese gemelo. Una persona que aprende repite menos.
También: muertes, noches sobrevividas, dopamina media del día y la curva por día de juego.

Ventana: «fin» si existe; si hay «fin_previsto», el menor de los dos (lo vivido después de la hora prevista no cuenta);
si no hay ninguno, el último evento. --horas H la corta en inicio + H h para todas.
Se informa además: minutos en el POZO de la casa (donde nacieron dos corridas), minutos FRÁGIL (vida <= 2: el cuerpo se
queda quieto), MUERTES EN RACHA (a <= 3 min de la anterior: reaparecer junto a un monstruo) y DÍAS ACTIVOS.
SENSIBILIDAD (no cambian la medida principal; escriben resultado/conjunto con un sufijo):
    --rachas          una racha de muertes seguidas (<= 3 min entre una y otra) cuenta como UNA muerte
    --unidad activos  la unidad es el día con alguna decisión o error (un día activo SIN errores cuenta 0); por
                      defecto solo entran los días con al menos un error
    --unidad todos    todos los días de juego, también los de estar quieto o atrapado
"""
import argparse
import json
import random
import time
from pathlib import Path

EV_DECISION = "decision_dia"
SITUACION = {"hambre", "herido", "mañana", "mediodía", "tarde", "en_casa", "cerca_de_casa", "lejos_de_casa"}
RACHA_MS = 3 * 60 * 1000    # muertes a <= 3 min de la anterior = la misma racha (reaparecer junto al monstruo)
HUECO_MS = 3 * 60 * 1000    # sin telemetría > 3 min = el bot no estaba (caído)


def en_pozo(p):
    """el pozo de 1x1 dentro de la casa donde nacieron dos corridas (coordenadas del mundo de juego)"""
    return bool(p) and len(p) == 3 and -135 <= p[0] <= -131 and 179 <= p[2] <= 184 and p[1] <= 54


def leer(p):
    out = []
    for f in sorted(p.glob("vida-*.jsonl")):
        for l in open(f, encoding="utf-8", errors="replace"):
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return sorted(out, key=lambda e: e.get("t", 0))


def errores(ev, lecc, t0, rachas=False):
    """(t, clave, tipo) de cada cosa que salió mal"""
    out = []
    for e in ev:
        if e.get("t", 0) < t0:
            continue
        tp = e.get("tipo")
        if tp == EV_DECISION and (e.get("recompensa") or 0) < -0.5:
            sit = "+".join(sorted(set(e.get("rasgos", [])) & SITUACION))
            out.append((e["t"], f"decision:{e.get('eligio')}|{sit}", "decision"))
        elif tp == "trabado":
            out.append((e["t"], f"trabado:{(e.get('ultima') or {}).get('accion')}", "trabado"))
        elif tp == "superar" and e.get("ok") is False:
            out.append((e["t"], f"fracaso:{e.get('accion')}|{e.get('motivo')}", "fracaso"))
    ultima = None
    for m in sorted(lecc, key=lambda m: m.get("t", 0)):
        if m.get("t", 0) >= t0 and not m.get("enArena"):
            en_racha = ultima is not None and m["t"] - ultima <= RACHA_MS
            ultima = m["t"]
            if rachas and en_racha:
                continue
            out.append((m["t"], f"muerte:{m.get('causa')}|{m.get('tarea')}", "muerte"))
    return sorted(out)


def minutos(tel, cond):
    """minutos de telemetría en que se cumple cond (cada muestra vale hasta la siguiente, máx. 1 min)"""
    return sum(min(60000, b["t"] - a["t"]) for a, b in zip(tel, tel[1:]) if cond(a)) / 60000


def gemelo(d, t0, t1, rachas=False, unidad="errores"):
    ev = [e for e in leer(d / "registros") if t0 <= e.get("t", 0) <= t1]
    try:
        lecc = [json.loads(l) for l in open(d / "registros" / "lecciones.jsonl", encoding="utf-8", errors="replace") if l.strip()]
    except Exception:
        lecc = []
    lecc = [m for m in lecc if t0 <= m.get("t", 0) <= t1]
    err = errores(ev, lecc, t0, rachas)
    # día de juego de cada evento: por los «noche_termina»
    cortes = [e["t"] for e in ev if e.get("tipo") == "noche_termina"]
    dia_de = lambda t: sum(1 for c in cortes if c <= t) + 1  # noqa: E731
    decis = [e for e in ev if e.get("tipo") == EV_DECISION]
    dias_activos = sorted({dia_de(e["t"]) for e in decis})
    por_dia = {}
    if unidad == "activos":
        por_dia = {k: {"errores": 0, "repetidos": 0} for k in dias_activos}
    elif unidad == "todos":
        por_dia = {k: {"errores": 0, "repetidos": 0} for k in range(1, len(cortes) + 2)}
    vistos, rep = set(), 0
    for t, k, tp in err:
        dd = por_dia.setdefault(dia_de(t), {"errores": 0, "repetidos": 0})
        dd["errores"] += 1
        if k in vistos:
            rep += 1
            dd["repetidos"] += 1
        vistos.add(k)
    dop = [e.get("recompensa", 0) for e in decis]
    noches = [e for e in ev if e.get("tipo") == "noche_termina"]
    refl = [e for e in ev if e.get("tipo") == "reflexion"]
    tel = [e for e in ev if e.get("tipo") == "telemetria"]
    huecos = sum(b["t"] - a["t"] for a, b in zip(tel, tel[1:]) if b["t"] - a["t"] > HUECO_MS)
    if tel and t1 - tel[-1]["t"] > HUECO_MS:
        huecos += t1 - tel[-1]["t"]
    horas = (t1 - t0) / 3.6e6
    horas_jugadas = max(0.0, (t1 - t0 - huecos) / 3.6e6)
    muertes_t = sorted(m["t"] for m in lecc if not m.get("enArena"))
    en_racha = sum(1 for a, b in zip(muertes_t, muertes_t[1:]) if b - a <= RACHA_MS)
    return {
        "horas": round(horas, 2),
        "horas_jugadas": round(horas_jugadas, 2),
        "min_sin_bot": round(huecos / 60000, 1),
        "dias_de_juego": len(noches) + 1,
        "dias_activos": len(dias_activos),
        "errores": len(err),
        "errores_repetidos": rep,
        "tasa_repeticion": round(rep / len(err), 3) if err else None,
        "repetidos_por_hora": round(rep / horas_jugadas, 2) if horas_jugadas else None,
        "por_tipo": {tp: sum(1 for _, _, x in err if x == tp) for tp in ("decision", "trabado", "fracaso", "muerte")},
        "muertes": len(lecc),
        "muertes_en_racha": en_racha,
        "noches_sobrevividas": sum(1 for n in noches if n.get("sobrevivio")),
        "decisiones": len(dop),
        "dopamina_media": round(sum(dop) / len(dop), 3) if dop else None,
        "reflexiones": sum(1 for r in refl if r.get("aceptadas") is not None),
        "min_en_pozo": round(minutos(tel, lambda e: en_pozo(e.get("pos"))), 1),
        "min_fragil": round(minutos(tel, lambda e: (e.get("vida") if e.get("vida") is not None else 20) <= 2), 1),
        "por_dia": por_dia,
    }


def ventana(C, horas_max=None):
    """(t0, t1, de dónde sale t1)"""
    t0 = int((C / "inicio").read_text().strip())
    t1, origen = None, ""
    if (C / "fin").exists():
        t1, origen = int((C / "fin").read_text().strip()), "fin"
    if (C / "fin_previsto").exists():
        fp = int((C / "fin_previsto").read_text().strip())
        if t1 is None or fp < t1:
            t1, origen = fp, "fin_previsto" + (" (siguió hasta «fin»: lo de después no cuenta)" if t1 is not None else " (no hay «fin»)")
    if t1 is None:
        ult = [e.get("t", 0) for g in ("A", "B") for e in leer(C / g / "registros")[-1:]]
        t1, origen = max(ult + [t0]), "último evento (no hay fin ni fin_previsto)"
    if horas_max:
        tope = t0 + int(horas_max * 3.6e6)
        if tope < t1:
            t1, origen = tope, f"tope --horas {horas_max:g}"
    return t0, t1, origen


# ---------------------------------------------------------------------- ¿la diferencia es real o es suerte?
# Unidad = un DÍA DE JUEGO de un gemelo (cuántos errores repitió ese día). Tres miradas:
#  1) por corrida: la diferencia B - A de errores repetidos por día (positiva = A repite menos = pensar ayudó)
#  2) PERMUTACIÓN: si pensar no importara, las etiquetas A/B de los días serían intercambiables. Se barajan DENTRO de
#     cada corrida 20 000 veces y se cuenta cuántas veces sale una diferencia tan grande como la real → valor p
#  3) BOOTSTRAP: se remuestrean los días (dentro de cada corrida y gemelo) → intervalo del 95 % de la diferencia
# Veredicto: con < 3 corridas, «solo orientativo»; si p < 0,05 y el IC95 no toca el 0, a favor de A o de B; si no,
# «no se distingue de la suerte».
def media(l):
    return sum(l) / len(l) if l else 0.0


def estadistica(dias, n_perm=20000, n_boot=5000, semilla=1):
    """dias = {corrida: {"A": [repetidos por día], "B": [...]}} (en orden) → B−A, IC95, p y veredicto."""
    rng = random.Random(semilla)

    def dif(d):
        a = [x for n in d for x in d[n]["A"]]
        b = [x for n in d for x in d[n]["B"]]
        return media(b) - media(a)
    real = dif(dias)
    mayores = 0
    for _ in range(n_perm):
        p = {}
        for n, g in dias.items():
            l = g["A"] + g["B"]
            rng.shuffle(l)
            p[n] = {"A": l[:len(g["A"])], "B": l[len(g["A"]):]}
        if abs(dif(p)) >= abs(real) - 1e-12:
            mayores += 1
    boot = []
    for _ in range(n_boot):
        boot.append(dif({n: {k: [rng.choice(v) for _ in v] if v else [] for k, v in g.items()} for n, g in dias.items()}))
    boot.sort()
    ic = (boot[int(0.025 * n_boot)], boot[int(0.975 * n_boot)])
    pval = (mayores + 1) / (n_perm + 1)
    if len(dias) < 3:
        veredicto = "pocas corridas: solo orientativo"
    elif pval < 0.05 and ic[0] > 0:
        veredicto = "A repite MENOS errores que B: pensar al dormir ayuda (con estos datos)"
    elif pval < 0.05 and ic[1] < 0:
        veredicto = "A repite MÁS errores que B: pensar al dormir empeora (con estos datos)"
    else:
        veredicto = "no se distingue de la suerte (hacen falta más corridas o un efecto mayor)"
    return {"B_menos_A": real, "ic95": ic, "p": pval, "veredicto": veredicto}


def conjunto(todos, salida_dir, sufijo=""):
    dias = {n: {g: [v["repetidos"] for _, v in sorted(r[g]["por_dia"].items())] for g in ("A", "B")} for n, r in todos.items()}
    e = estadistica(dias)
    print("\n=== CONJUNTO", ", ".join(dias), f"[{sufijo[1:]}]" if sufijo else "", "===")
    for n, g in dias.items():
        print(f"  {n:12s} repetidos/día  A {media(g['A']):.2f} ({len(g['A'])} días)   B {media(g['B']):.2f} ({len(g['B'])} días)   B-A {media(g['B']) - media(g['A']):+.2f}")
    print(f"  B - A (todas): {e['B_menos_A']:+.2f} repetidos por día   IC95 [{e['ic95'][0]:+.2f}, {e['ic95'][1]:+.2f}]   p = {e['p']:.3f}")
    print("  veredicto:", e["veredicto"])
    (salida_dir / f"conjunto{sufijo}.json").write_text(json.dumps({"corridas": list(dias), "variante": sufijo[1:] or "principal",
                                                                   "dias": dias, **e}, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="experimento dormir para pensar (dos copias idénticas)")
    ap.add_argument("corridas", nargs="+")
    ap.add_argument("--dir", default="corridas", help="carpeta con una subcarpeta por corrida")
    ap.add_argument("--horas", type=float, default=None, help="cortar todas en inicio + H horas")
    ap.add_argument("--rachas", action="store_true", help="una racha de muertes (<= 3 min) cuenta como una")
    ap.add_argument("--unidad", choices=("errores", "activos", "todos"), default="errores")
    a = ap.parse_args()
    raiz = Path(a.dir)
    sufijo = "".join([f"-{a.horas:g}h" if a.horas else "", "-rachas" if a.rachas else "", f"-{a.unidad}" if a.unidad != "errores" else ""])
    hora = lambda t: time.strftime("%d/%m %H:%M", time.localtime(t / 1000))  # noqa: E731
    todos = {}
    for n in a.corridas:
        C = raiz / n
        t0, t1, origen = ventana(C, a.horas)
        res = {g: gemelo(C / g, t0, t1, a.rachas, a.unidad) for g in ("A", "B")}
        print(f"\n=== {n}  (A piensa al dormir · B control){'  [' + sufijo[1:] + ']' if sufijo else ''} ===")
        print(f"  ventana {hora(t0)} → {hora(t1)}  ({origen})")
        for k in ("horas", "horas_jugadas", "min_sin_bot", "dias_de_juego", "dias_activos", "errores", "errores_repetidos",
                  "tasa_repeticion", "repetidos_por_hora", "muertes", "muertes_en_racha", "noches_sobrevividas", "decisiones",
                  "dopamina_media", "reflexiones", "min_en_pozo", "min_fragil", "por_tipo"):
            print(f"  {k:22s} A: {res['A'][k]!s:28s} B: {res['B'][k]!s}")
        (C / f"resultado{sufijo}.json").write_text(json.dumps({"ventana": [t0, t1, origen], **res}, ensure_ascii=False, indent=1), encoding="utf-8")
        todos[n] = res
    conjunto(todos, raiz, sufijo)


if __name__ == "__main__":
    main()

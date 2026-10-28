"""Recalcula los resultados agregados de los dos experimentos de gemelos DESDE LOS CSV PUBLICADOS (sin registros crudos)
y los compara con los que guardaron los análisis originales.
Recomputes the twin experiments' aggregates from the published CSVs and checks them against the original analyses.

    python gemelos/recalcular.py              (sin red; solo biblioteca estándar)

Entrada: resultados/gemelos/repetidos_por_dia.csv, resumen_corridas.csv, agregados_originales.json
Salida:  resultados/gemelos/agregados.csv y diferencias_por_corrida.csv
"""
import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import analizar            # noqa: E402  estadistica(): permutación 20 000 + bootstrap 5 000, semilla 1
import analizar_maestro    # noqa: E402  decidir(), permutacion(): la regla pre-registrada

RES = AQUI.parent / "resultados" / "gemelos"


def leer_dias(experimento, variante, corridas=None):
    dias = OrderedDict()
    for f in csv.DictReader(open(RES / "repetidos_por_dia.csv", encoding="utf-8")):
        if f["experimento"] != experimento or f["variante"] != variante:
            continue
        if corridas and f["corrida"] not in corridas:
            continue
        dias.setdefault(f["corrida"], OrderedDict()).setdefault(f["brazo"], []).append((int(f["posicion"]), int(f["repetidos"])))
    return OrderedDict((c, OrderedDict((g, [r for _, r in sorted(v)]) for g, v in sorted(b.items()))) for c, b in dias.items())


def cerca(a, b, tol):
    return abs(a - b) <= tol


def main():
    orig = json.loads((RES / "agregados_originales.json").read_text(encoding="utf-8"))
    inter = {f["corrida"]: f["intercambio"] for f in csv.DictReader(open(RES / "resumen_corridas.csv", encoding="utf-8"))}
    agregados, por_corrida, fallos = [], [], 0

    print("=== Dormir para pensar: A reflexiona al dormir · B control (B − A > 0: A repite menos errores) ===")
    casos = [("principal", "principal", None, 1e-9),
             ("5h-rachas-activos", "5h-rachas-activos", None, 1e-9),
             ("principal", "principal_3_corridas_antes_de_larga6", ["larga2", "larga4i", "larga5"], 0.006)]
    for variante, clave, subconjunto, tol in casos:
        dias = leer_dias("dormir_para_pensar", variante, subconjunto)
        e = analizar.estadistica(dias)
        o = orig["dormir_para_pensar"][clave]
        ok = (list(dias) == o["corridas"] and cerca(e["B_menos_A"], o["B_menos_A"], tol)
              and cerca(e["ic95"][0], o["ic95"][0], tol) and cerca(e["ic95"][1], o["ic95"][1], tol) and cerca(e["p"], o["p"], max(tol, 1e-9)))
        fallos += not ok
        print(f"\n[{clave}] corridas: {', '.join(dias)}")
        for c, g in dias.items():
            mA, mB = analizar.media(g["A"]), analizar.media(g["B"])
            print(f"  {c:9s} {'(A/B intercambiados de servidor)' if inter.get(c) == '1' else '':33s} A {mA:.2f}/día ({len(g['A'])} días)   "
                  f"B {mB:.2f}/día ({len(g['B'])} días)   B−A {mB - mA:+.2f}")
            if subconjunto is None:
                por_corrida.append({"experimento": "dormir_para_pensar", "variante": variante, "corrida": c,
                                    "intercambio": inter.get(c), "dias_A": len(g["A"]), "dias_B": len(g["B"]),
                                    "rep_dia_A": round(mA, 4), "rep_dia_B": round(mB, 4), "B_menos_A": round(mB - mA, 4)})
        print(f"  TODAS: B−A {e['B_menos_A']:+.3f}  IC95 [{e['ic95'][0]:+.3f}, {e['ic95'][1]:+.3f}]  p = {e['p']:.3f}  → {e['veredicto']}")
        print(f"  ¿igual que el análisis original? {'SÍ' if ok else 'NO'}  (original: {o['B_menos_A']:+.3f} [{o['ic95'][0]:+.3f}, {o['ic95'][1]:+.3f}] p = {o['p']:.3f})")
        agregados.append({"experimento": "dormir_para_pensar", "variante": clave, "corridas": " ".join(dias),
                          "medida": "B − A, errores repetidos por día", "estimacion": round(e["B_menos_A"], 4),
                          "ic_lo": round(e["ic95"][0], 4), "ic_hi": round(e["ic95"][1], 4), "ic_nivel": "95 %",
                          "p": round(e["p"], 4), "veredicto": e["veredicto"], "coincide_con_original": ok})

    print("\n=== Retirar al maestro: A reflexión con LLM · B reflexión propia — PRELIMINAR (1 de ≥ 4 corridas) ===")
    variante = "5h-rachas-activos (pre-registrada)"
    dias = leer_dias("retirar_al_maestro", variante)
    muertes = {}
    for f in csv.DictReader(open(RES / "resumen_corridas.csv", encoding="utf-8")):
        if f["experimento"] == "retirar_al_maestro":
            muertes.setdefault(f["corrida"], {})[f["brazo"]] = int(f["muertes"])
    d = analizar_maestro.decidir(dias, muertes)
    pm = analizar_maestro.permutacion(dias, "A", "B")
    o = orig["retirar_al_maestro"]["maestro1"]
    ok = (cerca(d["R"], o["decision"]["R"], 1e-9) and cerca(d["P_R_ge_0_9"], o["decision"]["P_R_ge_0_9"], 1e-9)
          and cerca(pm["dif"], o["comparaciones"]["B-A"]["dif"], 1e-9) and cerca(pm["p"], o["comparaciones"]["B-A"]["p"], 1e-9))
    fallos += not ok
    print(f"  repetidos/día A {d['rep_dia_A']:.2f} ({len(dias['maestro1']['A'])} días activos)   B {d['rep_dia_B']:.2f} ({len(dias['maestro1']['B'])} días activos)")
    print(f"  R = A/B = {d['R']:.3f}  IC80 [{d['ic80_R'][0]:.2f}, {d['ic80_R'][1]:.2f}]  P(R ≥ 0,9) = {d['P_R_ge_0_9']:.3f}  "
          f"B−A {pm['dif']:+.3f} p = {pm['p']:.3f}  muertes A {muertes['maestro1']['A']} / B {muertes['maestro1']['B']}")
    print(f"  veredicto de la regla: {d['veredicto']}")
    print(f"  ¿igual que el análisis original? {'SÍ' if ok else 'NO'}")
    agregados.append({"experimento": "retirar_al_maestro (PRELIMINAR)", "variante": variante, "corridas": "maestro1",
                      "medida": "R = repetidos/día A ÷ B", "estimacion": round(d["R"], 4), "ic_lo": round(d["ic80_R"][0], 4),
                      "ic_hi": round(d["ic80_R"][1], 4), "ic_nivel": "80 %", "p": round(pm["p"], 4),
                      "veredicto": d["veredicto"] + f"; P(R ≥ 0,9) = {d['P_R_ge_0_9']:.3f}", "coincide_con_original": ok})

    for nombre, filas in (("agregados.csv", agregados), ("diferencias_por_corrida.csv", por_corrida)):
        with open(RES / nombre, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    print(f"\nescrito: resultados/gemelos/agregados.csv, diferencias_por_corrida.csv · verificación: {'TODO IDÉNTICO' if not fallos else f'{fallos} diferencias'}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())

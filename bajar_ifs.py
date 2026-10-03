#!/usr/bin/env python3
"""
Previsión IFS (ECMWF, vía Open-Meteo) en los 5,605 nodos de la malla.

Baja la pasada de hoy, de D-7 a D+1, y la deja cruda en
`datos/ifs_malla_<fecha>.parquet`. No calcula nada: es la función `descarga`
de la cadena de cálculo (`malla_02b_ifs.py`), con las mismas peticiones, los
mismos lotes y las mismas esperas, para que el fichero sea el que la cadena
habría bajado por sí misma.

Cuota de Open-Meteo: 5,605 nodos en lotes de 200 son 29 peticiones. El límite
gratuito es por minuto y por hora, así que se espera 20 s entre lotes y no se
mandan más de 23 lotes por hora: la descarga completa tarda algo más de una
hora. Se puede parar y relanzar: reanuda por nodo.

Uso:
    python bajar_ifs.py                      # pasada de hoy (fecha UTC)
    python bajar_ifs.py --fecha 2026-10-04   # nombre de la pasada
    python bajar_ifs.py --max-nodos 400      # prueba corta
"""
import argparse
import os
import pathlib
import time

import numpy as np
import pandas as pd
import requests

AQUI = pathlib.Path(__file__).resolve().parent
DATOS = pathlib.Path(os.environ.get("DESCARGA_DATOS", AQUI / "datos"))
NODOS = AQUI / "nodos.npz"

URL = "https://api.open-meteo.com/v1/forecast"
VARS = ("temperature_2m_max,relative_humidity_2m_min,"
        "wind_speed_10m_max,precipitation_sum")
LOTE = 200            # coordenadas por petición
PAUSA = 20            # s entre lotes; con menos salta el 429
DIAS_PREV = 2         # D y D+1
LOTES_HORA = 23       # tope horario de Open-Meteo (~5,000 unidades)


def descarga(ruta, past_dias=7, max_nodos=None):
    n = np.load(NODOS)
    la, lo = n["nodo_lat"][:max_nodos], n["nodo_lon"][:max_nodos]
    parcial = f"{ruta}.parcial"
    filas, hechos = [], set()
    if os.path.exists(parcial):
        prev = pd.read_parquet(parcial)
        filas, hechos = [prev], set(prev["nodo"].unique())
        print(f"  IFS: reanudando, {len(hechos)} nodos ya bajados", flush=True)

    n_lotes = int(np.ceil(len(la) / LOTE))
    enviados = []
    for b in range(n_lotes):
        k = b * LOTE
        sl = slice(k, k + LOTE)
        if all(k + i in hechos for i in range(len(la[sl]))):
            continue
        enviados = [t for t in enviados if time.time() - t < 3660]
        if len(enviados) >= LOTES_HORA:
            dormir = 3660 - (time.time() - enviados[0])
            print(f"    tope horario: {len(enviados)} lotes en la última hora · "
                  f"esperando {dormir/60:.0f} min", flush=True)
            time.sleep(max(dormir, 1))
            enviados = [t for t in enviados if time.time() - t < 3660]
        espera = PAUSA
        for _ in range(8):
            try:
                r = requests.get(URL, params=dict(
                    latitude=",".join(f"{v:.4f}" for v in la[sl]),
                    longitude=",".join(f"{v:.4f}" for v in lo[sl]),
                    past_days=past_dias, forecast_days=DIAS_PREV, daily=VARS,
                    models="ecmwf_ifs025", timezone="UTC",
                    wind_speed_unit="ms"), timeout=180)
            except requests.exceptions.RequestException as e:
                print(f"    red: {type(e).__name__} · esperando {espera}s", flush=True)
                time.sleep(espera)
                espera = min(espera * 2, 900)
                continue
            if r.status_code != 429:
                break
            print(f"    429 · esperando {espera}s", flush=True)
            time.sleep(espera)
            espera = min(espera * 2, 900)
        r.raise_for_status()
        enviados.append(time.time())
        j = r.json()
        for i, blo in enumerate(j if isinstance(j, list) else [j]):
            d = blo["daily"]
            filas.append(pd.DataFrame({
                "nodo": k + i, "fecha": pd.to_datetime(d["time"]),
                "tmax": d["temperature_2m_max"],
                "hr_min": d["relative_humidity_2m_min"],
                "viento_max": d["wind_speed_10m_max"],
                "prec": d["precipitation_sum"]}))
        pd.concat(filas, ignore_index=True).to_parquet(parcial, index=False)
        print(f"    lote {b + 1}/{n_lotes} · {min(k + LOTE, len(la))}/{len(la)} "
              f"nodos", flush=True)
        if b < n_lotes - 1:
            time.sleep(PAUSA)

    df = pd.concat(filas, ignore_index=True)
    df.to_parquet(ruta, index=False)
    os.remove(parcial)
    return df


def main(a):
    fecha = a.fecha or str(pd.Timestamp.now("UTC").tz_localize(None).date())
    DATOS.mkdir(parents=True, exist_ok=True)
    ruta = DATOS / f"ifs_malla_{fecha}.parquet"
    if ruta.exists():
        print(f"  IFS: ya bajado ({ruta})")
        return
    df = descarga(str(ruta), a.past_dias, a.max_nodos)
    f = pd.to_datetime(df["fecha"])
    print(f"  nodos: {df['nodo'].nunique():,} · fechas: {f.min().date()} → {f.max().date()}")
    # La cadena necesita la pasada entera: mejor fallar aquí que dejar un fichero corto.
    esperados = a.max_nodos or len(np.load(NODOS)["nodo_lat"])
    if df["nodo"].nunique() != esperados:
        ruta.unlink()
        raise SystemExit(f"ERROR: faltan nodos ({df['nodo'].nunique()} de {esperados})")
    print(f"  guardado: {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fecha")
    p.add_argument("--past-dias", type=int, default=7)
    p.add_argument("--max-nodos", type=int)
    main(p.parse_args())

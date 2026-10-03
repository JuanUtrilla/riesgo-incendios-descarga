#!/usr/bin/env python3
"""
El aviso de «datos listos»: `listo_<fecha>.json` con el nombre, el tamaño y el
SHA-256 de lo bajado ese día.

Es lo último que se sube al Release. El servidor de cálculo solo mira este
fichero: si existe, la pasada del día está entera, y con el SHA-256 comprueba
que lo que ha bajado es lo que se subió.

Uso:
    python manifiesto.py --fecha 2026-10-04 datos/ifs_malla_2026-10-04.parquet datos/era5land_202609_h28.nc
"""
import argparse
import hashlib
import json
import os

import pandas as pd


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def main(a):
    man = {"fecha": a.fecha,
           "creado": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
           "ficheros": {os.path.basename(r): {"sha256": sha256(r), "bytes": os.path.getsize(r)}
                        for r in a.ficheros}}
    nombres = list(man["ficheros"])
    if not any(n.startswith("ifs_malla_") for n in nombres) or not any(n.startswith("era5land_") for n in nombres):
        raise SystemExit(f"ERROR: tienen que estar la previsión IFS y el ERA5-Land, y hay {nombres}")
    salida = os.path.join(os.path.dirname(a.ficheros[0]), f"listo_{a.fecha}.json")
    json.dump(man, open(salida, "w"), indent=1)
    print(salida)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fecha", required=True)
    p.add_argument("ficheros", nargs="+")
    main(p.parse_args())

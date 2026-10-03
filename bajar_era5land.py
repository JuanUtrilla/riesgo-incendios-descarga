#!/usr/bin/env python3
"""
ERA5-Land horario del mes en curso (Climate Data Store de Copernicus).

Baja, sin tocarlo, el mes del día D-6 desde el día 1 hasta D-6 y lo deja en
`datos/era5land_<aaaamm>_h<dd>.nc` (o `era5land_<aaaamm>.nc` si el mes está
completo). Es la misma petición y el mismo nombre que usa `pide_mes` en la
cadena de cálculo (`malla_02_descarga.py`): allí basta con poner el fichero en
`salida/_cds/` para que `gh_reanalisis.py` lo dé por descargado y lo agregue a
diario. Aquí no se agrega ni se funde nada.

ERA5-Land llega con unos 6 días de retraso. Los primeros días de cada mes, D-6
cae en el mes anterior y se pide ese.

Credenciales: `~/.cdsapirc` (en GitHub, del secreto `CDSAPI_KEY`).

Uso:
    python bajar_era5land.py                      # hoy (fecha UTC)
    python bajar_era5land.py --fecha 2026-10-04
"""
import argparse
import calendar
import os
import pathlib

import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
DATOS = pathlib.Path(os.environ.get("DESCARGA_DATOS", AQUI / "datos"))

# Las de `config.py` de la cadena: caja de la península y Baleares en la malla
# nativa de 0.1°, y las cinco variables de las que sale la meteorología diaria.
AREA = [44.0, -9.6, 35.8, 4.4]   # [N, W, S, E]
VARIABLES = ["2m_temperature", "2m_dewpoint_temperature",
             "10m_u_component_of_wind", "10m_v_component_of_wind",
             "total_precipitation"]
RETRASO = 6                      # días de retraso de ERA5-Land


def nombre(anio, mes, ultimo):
    completo = ultimo == calendar.monthrange(anio, mes)[1]
    return f"era5land_{anio}{mes:02d}.nc" if completo else f"era5land_{anio}{mes:02d}_h{ultimo:02d}.nc"


def main(a):
    import cdsapi
    hoy = pd.Timestamp(a.fecha) if a.fecha else pd.Timestamp.now("UTC").tz_localize(None).normalize()
    fin = hoy - pd.Timedelta(days=RETRASO)
    dias = list(range(1, fin.day + 1))
    DATOS.mkdir(parents=True, exist_ok=True)
    ruta = DATOS / nombre(fin.year, fin.month, fin.day)
    if ruta.exists():
        print(f"  ERA5-Land: ya bajado ({ruta})")
        return
    print(f"  ERA5-Land {fin:%Y-%m}: pidiendo a CDS los días 1..{fin.day}...", flush=True)
    cdsapi.Client().retrieve("reanalysis-era5-land", {
        "variable": VARIABLES, "year": str(fin.year), "month": f"{fin.month:02d}",
        "day": [f"{d:02d}" for d in dias],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": AREA, "data_format": "netcdf",
    }, f"{ruta}.tmp")
    os.replace(f"{ruta}.tmp", ruta)
    print(f"  guardado: {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fecha")
    main(p.parse_args())

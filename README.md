# Descarga diaria para el mapa de riesgo de incendios

Este repositorio solo baja datos públicos. Cada madrugada, en GitHub Actions,
descarga lo que necesita el mapa diario de riesgo de incendio forestal y lo
deja como asset del Release `datos`. Aquí no hay modelo, ni estado, ni
cálculo: eso corre en otro sitio, que viene a por los ficheros.

| Qué | De dónde | Fichero |
|---|---|---|
| ERA5-Land horario del mes en curso, hasta D-6 (península y Baleares, 5 variables) | Climate Data Store de Copernicus | `era5land_<aaaamm>_h<dd>.nc` (unos 45 MB) |
| Previsión IFS diaria de D-7 a D+1 en 5,605 nodos | Open-Meteo (`ecmwf_ifs025`) | `ifs_malla_<fecha>.parquet` |
| Aviso de «datos listos», con el SHA-256 de los dos | — | `listo_<fecha>.json` |

**Nada de lo bajado entra en git**: el historial no se puede borrar y los
datos sí. Los assets de más de tres días se eliminan en cada corrida.

## Cómo funciona

`.github/workflows/descarga.yml`, a las 01:03 UTC de abril a octubre y a las
01:02 UTC el resto del año (GitHub suele retrasarlo varias horas):

1. `fecha`: fija la fecha UTC de la corrida y crea el Release si no existe.
2. `ifs` y `era5land`, a la vez: `bajar_ifs.py` y `bajar_era5land.py`, y cada
   uno sube su fichero al Release.
3. `listo`: solo si han salido los dos, sube `listo_<fecha>.json` y borra los
   assets viejos.

La previsión IFS tarda algo más de una hora (29 peticiones con el tope por
hora de Open-Meteo); el ERA5-Land depende de la cola del CDS. Si una de las
dos falla, no hay aviso y ese día no se calcula el mapa de hoy; al día
siguiente se vuelve a intentar con todo.

Quien consume los datos solo necesita leer
`https://github.com/<usuario>/<repo>/releases/download/datos/listo_<fecha>.json`:
si existe, baja los ficheros que nombra y comprueba su SHA-256. No hace falta
ningún token.

## Puesta en marcha

1. Crear el repositorio en GitHub, **público** (los minutos de Actions son
   gratis en los públicos) y subir esto.
2. En *Settings → Secrets and variables → Actions*, crear el secreto
   `CDSAPI_KEY` con la clave personal del CDS
   (<https://cds.climate.copernicus.eu/profile>). Hay que haber aceptado la
   licencia de ERA5-Land en esa cuenta.
3. En *Actions*, lanzar a mano «Descarga diaria» una vez para comprobarlo.

Open-Meteo no pide clave.

## En local

```bash
pip install -r requirements.txt
python bajar_ifs.py --max-nodos 400     # prueba corta: 2 peticiones
python bajar_ifs.py                     # la pasada entera, algo más de 1 h
python bajar_era5land.py                # necesita ~/.cdsapirc
python manifiesto.py --fecha 2026-10-04 datos/ifs_malla_2026-10-04.parquet datos/era5land_202609_h28.nc
```

Todo cae en `datos/` (o en `DESCARGA_DATOS`), fuera de git.

## Que los números no cambien

Los dos scripts hacen las mismas peticiones que la cadena de cálculo original
(`malla_02b_ifs.descarga` y `malla_02_descarga.pide_mes`) y guardan el
resultado con el mismo nombre, así que la cadena los toma como ya descargados
y sigue como siempre. Comprobado el 03/10/2026:

- IFS: los 400 primeros nodos bajados con `bajar_ifs.py` y con la cadena dan
  el mismo `DataFrame`.
- ERA5-Land: el fichero de septiembre de 2026 (días 1 a 27) bajado con
  `bajar_era5land.py`, puesto en `salida/_cds/`, lo fundió `gh_reanalisis.py`
  sin modificar y sin credenciales de CDS (acumulado del 24/09 al 27/09).

`nodos.npz` son las coordenadas de los 5,605 nodos de la malla de ERA5-Land
que caen sobre la península y Baleares, en el mismo orden que usa la cadena.

## Datos y licencias

- ERA5-Land: Copernicus Climate Change Service (C3S), Climate Data Store.
  Contiene información modificada del Servicio de Cambio Climático de
  Copernicus; ni la Comisión Europea ni el ECMWF son responsables del uso que
  se haga de ella.
- Previsión IFS del ECMWF, a través de [Open-Meteo](https://open-meteo.com/)
  (CC BY 4.0). El plan gratuito de Open-Meteo es para uso no comercial.

# Configuración de proxy Bright Data

Guía para usar [Bright Data](https://brightdata.com) (ISP proxy) con el reporter de DropTools. El mismo flujo que ResiProx/DataImpulse: configuración por `proxy_dev_config.json` (desarrollo) o variables de entorno (Docker/producción).

## Parámetros del proxy

| Parámetro   | Valor              |
|------------|--------------------|
| Host       | `brd.superproxy.io` |
| Puerto     | `33335`             |
| Usuario    | `brd-customer-<customer_id>-zone-<zone_name>-country-co` |
| Contraseña | La de tu zona en el panel Bright Data |

El sufijo **`-country-co`** fija IP en Colombia. Para otro país: `-country-us`, `-country-mx`, etc. (ver documentación de Bright Data).

Documentación: [Send your first request](https://docs.brightdata.com/proxy-networks/isp/send-your-first-request).

## Opción 1: Desarrollo (proxy_dev_config.json)

En `backend/proxy_dev_config.json` (no se sube a Git):

```json
{
  "proxy": {
    "host": "brd.superproxy.io",
    "port": 33335,
    "username": "brd-customer-<customer_id>-zone-isp_proxy1-country-co",
    "password": "TU_ZONE_PASSWORD"
  },
  "user_ids": [2, 3, 4]
}
```

Sustituir `<customer_id>`, el nombre de zona y la contraseña por los de tu cuenta. Asegurarse de que `DROPTOOLS_ENV=development` en `.env`.

## Opción 2: Docker / producción (variables de entorno)

En `.env.docker` o el entorno del backend/celery_worker:

```bash
DROPI_PROXY_HOST=brd.superproxy.io
DROPI_PROXY_PORT=33335
DROPI_PROXY_USER=brd-customer-<customer_id>-zone-isp_proxy1-country-co
DROPI_PROXY_PASS=TU_ZONE_PASSWORD
```

No definir `DROPI_NO_PROXY=1` cuando quieras usar Bright Data.

## Probar conectividad (sin Selenium)

Script que hace GET vía proxy a los endpoints de prueba de Bright Data:

```bash
# Desde la raíz del proyecto, con credenciales en env:
export BRIGHTDATA_PROXY_USER="brd-customer-XXX-zone-isp_proxy1-country-co"
export BRIGHTDATA_PROXY_PASS="tu_password"
python backend/scripts/test_brightdata_proxy.py
```

Desde `backend/`:

```bash
cd backend
export BRIGHTDATA_PROXY_USER="..."
export BRIGHTDATA_PROXY_PASS="..."
python scripts/test_brightdata_proxy.py
```

Si la respuesta muestra texto de `geo.brdtest.com` y/o IP/geo de `lumtest.com`, el proxy responde correctamente.

## Probar navegación completa (con Selenium)

Script que verifica que el proxy navega correctamente por internet antes de usarlo en el reporter:

```bash
# Desde la raíz del proyecto:
python backend/scripts/test_brightdata_navegacion.py

# O desde backend/:
cd backend
python scripts/test_brightdata_navegacion.py
```

Este script:
1. ✅ Verifica acceso a internet (obtiene IP del proxy)
2. ✅ Navega a Google y verifica que carga
3. ✅ Navega a la página de inicio de sesión de Dropi y verifica que no hay 403

**Modo visible**: El navegador se abre para que puedas ver el proceso. Si todos los tests pasan, el proxy funciona y puedes usarlo con el reporter.

Las capturas de pantalla se guardan en `results/screenshots/` si hay errores.

## Probar el reporter con Bright Data

1. Configurar proxy (archivo JSON o env como arriba).
2. Sin `DROPI_NO_PROXY=1`, ejecutar por ejemplo:
   - Local: `python manage.py unified_reporter --user-id 2 --headless --browser chrome` (desde `backend/`).
   - Docker: `docker compose run --rm backend python backend/manage.py unified_reporter --user-id 2 --headless --browser chrome`.
3. Revisar logs; si falla el login en Dropi, ver captura en `results/screenshots/`.

## API key

La API key de Bright Data se usa para sus APIs REST (Scraping API, Unlocker, etc.). Para el proxy HTTP que usa Selenium basta con usuario y contraseña. Se puede guardar `BRIGHTDATA_API_KEY` en env si en el futuro se integra alguna API de Bright Data; no es necesaria para el reporter actual.

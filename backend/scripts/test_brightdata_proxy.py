#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prueba de conectividad del proxy Bright Data (sin Selenium).
Hace GET a geo.brdtest.com o lumtest.com usando el proxy y muestra la respuesta.
Lee credenciales de variables de entorno; no hardcodear en el repo.

Uso:
  export BRIGHTDATA_PROXY_USER="brd-customer-XXX-zone-isp_proxy1-country-co"
  export BRIGHTDATA_PROXY_PASS="tu_password"
  python backend/scripts/test_brightdata_proxy.py

O desde backend/ con .env cargado:
  python scripts/test_brightdata_proxy.py
"""
import os
import sys

def main():
    host = os.environ.get("BRIGHTDATA_PROXY_HOST", "brd.superproxy.io")
    port = os.environ.get("BRIGHTDATA_PROXY_PORT", "33335")
    user = os.environ.get("BRIGHTDATA_PROXY_USER", "").strip()
    password = os.environ.get("BRIGHTDATA_PROXY_PASS", "").strip()

    if not user or not password:
        print("ERROR: Definir BRIGHTDATA_PROXY_USER y BRIGHTDATA_PROXY_PASS (o usar proxy_dev_config.json).")
        print("Ejemplo: export BRIGHTDATA_PROXY_USER='brd-customer-XXX-zone-isp_proxy1-country-co'")
        sys.exit(1)

    try:
        import requests
    except ImportError:
        print("ERROR: instalar requests: pip install requests")
        sys.exit(1)

    proxy_url = f"http://{user}:{password}@{host}:{port}"
    proxies = {"http": proxy_url, "https": proxy_url}

    # Opción 1: endpoint de prueba de Bright Data
    test_url = "https://geo.brdtest.com/welcome.txt?product=isp&method=native"
    # Opción 2: ver IP asignada (lumtest)
    ip_url = "http://lumtest.com/myip.json"

    print("Probando proxy Bright Data...")
    print(f"  Host: {host}:{port}")
    print(f"  User: {user[:30]}...")
    print()

    # Test principal (geo.brdtest.com)
    try:
        r = requests.get(test_url, proxies=proxies, timeout=30)
        r.raise_for_status()
        print("OK - geo.brdtest.com (Bright Data):")
        print(r.text.strip())
    except Exception as e:
        print(f"geo.brdtest.com falló: {e}")

    print()

    # Opcional: IP según lumtest
    try:
        r2 = requests.get(ip_url, proxies=proxies, timeout=15)
        r2.raise_for_status()
        data = r2.json()
        print("OK - lumtest.com/myip.json (IP del proxy):")
        print(f"  IP: {data.get('ip', 'N/A')}")
        geo = data.get("geo", {})
        if geo:
            print(f"  Ciudad: {geo.get('city', 'N/A')}, Región: {geo.get('region_name', 'N/A')}")
    except Exception as e:
        print(f"lumtest.com falló: {e}")

    print("\nSi ves respuesta arriba, el proxy responde. Puedes probar el reporter con proxy_dev_config.json o DROPI_PROXY_*.")


if __name__ == "__main__":
    main()

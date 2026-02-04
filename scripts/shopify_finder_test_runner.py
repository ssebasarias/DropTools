#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shopify Finder - Test Runner (verbose, decision-friendly)

Qué hace:
1) Ejecuta tu comando Django `shopify_finder` con los mismos flags del Finder.
2) Te muestra en consola el log en vivo (paso a paso).
3) Al final, arma un resumen "para tomar decisiones": hits guardados, dominios, títulos, precios,
   tipo de página detectado, fuente JSON, etc.
4) Opcional: te muestra un tail del log file `logs/shopify_finder.log`.

Uso (desde la raíz del proyecto):
    python scripts/shopify_finder_test_runner.py "faja reductora"
    python scripts/shopify_finder_test_runner.py "corrector de postura" --max 80 --max_hits 15
    python scripts/shopify_finder_test_runner.py "faja reductora" --country co-co --timelimit y
    python scripts/shopify_finder_test_runner.py "faja reductora" --headless

Notas:
- Este runner NO cambia tu Finder. Solo lo ejecuta y te resume resultados.
- manage.py se busca en backend/ respecto a la raíz del proyecto. Si no lo encuentra, usa --manage "ruta/al/manage.py"
"""

import argparse
import datetime as _dt
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _force_utf8_stdout():
    try:
        if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_manage_py(start: Path) -> Path | None:
    """
    Busca manage.py subiendo carpetas desde 'start'.
    También comprueba start/backend/manage.py (estructura típica con scripts/ en raíz).
    """
    # Estructura típica: proyecto/scripts/este_script.py, proyecto/backend/manage.py
    backend_manage = start / "backend" / "manage.py"
    if backend_manage.exists():
        return backend_manage
    cur = start.resolve()
    for _ in range(8):
        candidate = cur / "manage.py"
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def tail_file(path: Path, n: int = 120) -> str:
    if not path.exists():
        return ""
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 4096
            data = b""
            while size > 0 and data.count(b"\n") <= n:
                step = min(block, size)
                size -= step
                f.seek(size, os.SEEK_SET)
                data = f.read(step) + data
            lines = data.splitlines()[-n:]
            return "\n".join([ln.decode("utf-8", errors="replace") for ln in lines])
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""


def parse_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return rows
    return rows


def pretty_money(v):
    try:
        # Shopify price suele venir como string "109900.00"
        f = float(v)
        # Formato COP sin decimales (solo display)
        return f"${int(round(f)):,}".replace(",", ".")
    except Exception:
        return str(v)


def group_by_netloc(items):
    out = {}
    for it in items:
        netloc = (it.get("netloc") or "").lower().replace("www.", "")
        if not netloc:
            # fallback: parse root_url
            ru = it.get("root_url") or ""
            netloc = ru.replace("https://", "").replace("http://", "").split("/")[0].lower().replace("www.", "")
        if not netloc:
            netloc = "unknown"
        out.setdefault(netloc, []).append(it)
    return out


def print_summary(items, limit_domains=50):
    if not items:
        print("\n🧾 RESUMEN: No se guardaron candidatos (0 hits).")
        return

    by_dom = group_by_netloc(items)
    domains = list(by_dom.keys())[:limit_domains]

    print("\n" + "=" * 90)
    print(f"🧾 RESUMEN DECISIONAL (hits guardados: {len(items)} | dominios únicos: {len(by_dom)})")
    print("=" * 90)

    for d in domains:
        ex = by_dom[d][0]
        title = (ex.get("title") or "").strip()
        vendor = (ex.get("vendor") or "").strip()
        price = pretty_money(ex.get("price"))
        ptype = ex.get("page_type_detected") or ex.get("candidate_kind") or "-"
        src = ex.get("json_source") or ex.get("json_endpoint") or "-"
        source_url = ex.get("source_url") or ex.get("url") or "-"
        print(f"\n🌐 {d}")
        print(f"   • Title:  {title}")
        print(f"   • Vendor: {vendor}")
        print(f"   • Price:  {price}")
        print(f"   • Type:   {ptype}")
        print(f"   • JSON:   {src}")
        print(f"   • From:   {source_url}")

    if len(domains) < len(by_dom):
        print(f"\n… y {len(by_dom) - len(domains)} dominios más (usa --limit_domains para ver más).")

    print("=" * 90 + "\n")


def main():
    _force_utf8_stdout()

    ap = argparse.ArgumentParser(description="Verbose test runner for Django shopify_finder command.")
    ap.add_argument("query", help="Keyword o URL (ej: 'faja reductora' o https://tienda.com/products/x )")
    ap.add_argument("--manage", default=None, help="Ruta a manage.py (si no está en backend/).")
    ap.add_argument("--max", type=int, default=60, help="--max para shopify_finder (default 60)")
    ap.add_argument("--max_hits", type=int, default=25, help="--max_hits para shopify_finder (default 25)")
    ap.add_argument("--country", default="co-co", help="--country para shopify_finder (default co-co)")
    ap.add_argument("--timelimit", default="y", help="--timelimit para shopify_finder (d/w/m/y)")
    ap.add_argument("--headless", action="store_true", help="Activa screenshots (Capa 5) vía --headless")
    ap.add_argument("--cwd", default=None, help="Carpeta desde la que ejecutar manage.py (si necesitas).")
    ap.add_argument("--tail_log", action="store_true", help="Muestra tail del log file al final.")
    ap.add_argument("--tail_lines", type=int, default=120, help="Líneas del tail del log (default 120).")
    ap.add_argument("--limit_domains", type=int, default=50, help="Cuántos dominios mostrar en resumen.")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent  # raíz del proyecto (scripts/ está en raíz)

    manage_py = Path(args.manage).resolve() if args.manage else find_manage_py(project_root)
    if not manage_py:
        print("❌ No encontré manage.py automáticamente.")
        print("   Solución: pásalo explícito: --manage C:\\ruta\\a\\manage.py")
        sys.exit(1)

    cwd = Path(args.cwd).resolve() if args.cwd else manage_py.parent

    # Archivo JSONL del día (mismo naming que el Finder)
    today = _dt.datetime.now().strftime("%Y%m%d")
    jsonl_path = cwd / "raw_data" / f"shopify_candidates_{today}.jsonl"

    # Comando Django
    cmd = [
        sys.executable,
        str(manage_py),
        "shopify_finder",
        args.query,
        "--max", str(args.max),
        "--max_hits", str(args.max_hits),
        "--country", args.country,
        "--timelimit", args.timelimit,
    ]
    if args.headless:
        cmd.append("--headless")

    print("\n" + "=" * 90)
    print("🧪 EJECUTANDO FINDER (log en vivo)")
    print("=" * 90)
    print("CMD:", " ".join(cmd))
    print("CWD:", str(cwd))
    print("-" * 90)

    # Ejecutar y streamear salida (si tu finder ya tiene StreamHandler, aquí lo ves perfecto)
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        universal_newlines=True,
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        # re-emit tal cual
        print(line.rstrip("\n"))

    code = proc.wait()
    print("-" * 90)
    print(f"✅ Proceso terminó con exit code={code}")
    print("=" * 90)

    # Leer resultados del JSONL
    items = parse_jsonl(jsonl_path)
    print_summary(items, limit_domains=args.limit_domains)

    # Tail log file (por si hay avisos importantes)
    if args.tail_log:
        log_path = cwd / "logs" / "shopify_finder.log"
        tail = tail_file(log_path, n=args.tail_lines)
        print("\n" + "=" * 90)
        print(f"📄 TAIL LOG: {log_path} (últimas {args.tail_lines} líneas)")
        print("=" * 90)
        print(tail if tail else "(log vacío / no encontrado)")
        print("=" * 90 + "\n")

    # Consejo inmediato si ddgs warning aparece
    print("🔧 TIP rápido:")
    print("   Si ves warning de rename (duckduckgo_search -> ddgs):")
    print("   - pip uninstall duckduckgo_search")
    print("   - pip install -U ddgs\n")


if __name__ == "__main__":
    main()

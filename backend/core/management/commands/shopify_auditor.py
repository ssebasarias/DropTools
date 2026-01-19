# backend/management/commands/shopify_auditor.py
import logging
import json
import time
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand

# -----------------------------------------------------------------------------
# LOGGING (File + Console) - robust, no duplicados
# -----------------------------------------------------------------------------
logger = logging.getLogger("shopify_auditor")
logger.setLevel(logging.INFO)

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../logs")
os.makedirs(LOG_DIR, exist_ok=True)

if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    fh = logging.FileHandler(os.path.join(LOG_DIR, "shopify_auditor.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh)


class Command(BaseCommand):
    help = "Worker: Shopify Auditor (Forensic Validation & Pricing Analysis)"

    def add_arguments(self, parser):
        parser.add_argument("query", type=str, help='Keyword o URL (e.g., "corrector de postura")')
        parser.add_argument("--max", type=int, default=60, help="Máximo candidatos a evaluar (default 60)")
        parser.add_argument("--max_hits", type=int, default=25, help="Máximo candidatos guardados (default 25)")
        parser.add_argument("--country", type=str, default="co-co", help="Región ddgs (default co-co)")
        parser.add_argument("--timelimit", type=str, default="y", help="Timelimit ddgs (d/w/m/y)")
        parser.add_argument("--headless", action="store_true", help="Activa Playwright screenshot full page (Capa 5)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Session con retries (GET/HEAD) y headers realistas
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.session = requests.Session()
        retries = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.7,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET", "HEAD"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=30, pool_maxsize=30)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive",
            }
        )

        # Dedupe por dominio (registrable simple: quitamos www.)
        self.seen_domains = set()

        # Marketplaces y ruido típico
        self.noise_domains = [
            "amazon.",
            "mercadolibre.",
            "ebay.",
            "falabella.",
            "exito.",
            "youtube.",
            "pinterest.",
            "tiktok.",
            "facebook.",
            "instagram.",
            "play.google.com",
            "apps.apple.com",
            "google.com",
            "bing.com",
        ]

        # Términos basura (anti-ruido V4)
        self.bad_terms = [
            "magis",
            "iptv",
            "descargar",
            "instalar",
            "smart tv",
            "apk",
            "guia",
            "tutorial",
            "download",
            "gratis",
            "free",
        ]

        # Giftcard keywords
        self.giftcard_keywords = [
            "gift card",
            "tarjeta regalo",
            "tarjeta de regalo",
            "giftcard",
            "voucher",
            "bono regalo",
            "certificado de regalo",
        ]

    # -----------------------------------------------------------------------------
    # DJANGO ENTRY
    # -----------------------------------------------------------------------------
    def handle(self, *args, **options):
        query = options["query"]
        max_candidates = options["max"]
        max_hits = options["max_hits"]
        region = options["country"]
        timelimit = options["timelimit"]
        headless = options["headless"]

        logger.info(f"🚀 Iniciando Shopify Auditor para: '{query}'")

        candidates_urls = self.layer_1_discovery(query=query, region=region, timelimit=timelimit)
        if not candidates_urls:
            logger.warning("📉 Capa 1: 0 candidatos. Finalizando.")
            return

        candidates_urls = self._sanitize_and_rank_candidates(candidates_urls)
        candidates_urls = candidates_urls[:max_candidates]

        logger.info(f"🧪 Evaluando {len(candidates_urls)} candidatos (max={max_candidates})")

        saved = 0
        stats = {
            "candidates": len(candidates_urls),
            "shopify_ok": 0,
            "json_ok": 0,
            "saved": 0,
            "skipped_duplicate_domain": 0,
            "skipped_noise": 0,
            "layer2_failed": 0,
            "layer3_failed": 0,
            "giftcards_omitted": 0,
            "product_page_hits": 0,
        }

        for idx, url in enumerate(candidates_urls, 1):
            if saved >= max_hits:
                logger.info(f"✅ Alcanzado max_hits={max_hits}. Cortando ejecución.")
                break

            if self._is_noise(url):
                stats["skipped_noise"] += 1
                continue

            root_url, netloc = self._root_and_netloc(url)
            netloc_norm = netloc.lower().replace("www.", "")

            if netloc_norm in self.seen_domains:
                stats["skipped_duplicate_domain"] += 1
                logger.info(f"⏩ [{idx}] Skip duplicado dominio: {netloc_norm}")
                continue
            self.seen_domains.add(netloc_norm)

            logger.info(f"\n🔍 [{idx}] Procesando: {url}")

            # ──────── CAPA 2: Verificación Shopify + HTML Cache ────────
            is_shopify, html_cache, reason2 = self.layer_2_verify_shopify_hard(url)
            if not is_shopify:
                stats["layer2_failed"] += 1
                logger.info(f"   ❌ Capa 2: Descartado ({reason2})")
                continue

            stats["shopify_ok"] += 1
            logger.info("   ✅ Capa 2: Shopify confirmado")

            # ──────── CAPA 3: Extracción JSON (limit=10 + best pick) ────────
            data, reason3 = self.layer_3_smart_json_extraction(url)
            if not data:
                stats["layer3_failed"] += 1
                logger.warning(f"   ⚠️ Capa 3: Falló JSON ({reason3})")
                continue

            stats["json_ok"] += 1

            # Anti GiftCard (por si se coló)
            title_low = (data.get("title") or "").strip().lower()
            ptype_low = (data.get("product_type") or "").strip().lower()
            if any(k in title_low for k in self.giftcard_keywords) or "gift" in ptype_low:
                stats["giftcards_omitted"] += 1
                logger.info("   🧹 Capa 3: Omitido por GiftCard (title/product_type)")
                continue

            # Track product_page hits
            if data.get("candidate_kind") == "product_page":
                stats["product_page_hits"] += 1

            # Inject HTML cache para Capa 4
            data["_html_cache"] = html_cache or ""
            data["root_url"] = root_url
            data["netloc"] = netloc_norm
            data["source_url"] = url

            # ──────── CAPA 4: Clasificación (Scoring) ────────
            is_candidate, score_reason = self.layer_4_scoring_system(data)
            if not is_candidate:
                logger.info(f"   🗑️ Capa 4: Descartado ({score_reason})")
                continue

            logger.info(f"   🎯 Capa 4: ACEPTADO ({score_reason}) -> {data.get('title')}")

            # ──────── CAPA 5: Screenshot (opcional) ────────
            if headless:
                screen_path = self.layer_5_visual_capture(url)
                if screen_path:
                    data["screenshot_path"] = screen_path
                    logger.info(f"   📸 Capa 5: Screenshot guardado en {screen_path}")

            # Limpieza antes de guardar
            data.pop("_html_cache", None)

            self.save_data(data)
            saved += 1
            stats["saved"] = saved
            logger.info("   💾 GUARDADO EXITOSAMENTE.")

        logger.info("🏁 RESUMEN FINAL:")
        logger.info(f"   Total candidatos: {stats['candidates']}")
        logger.info(f"   Shopify confirmados: {stats['shopify_ok']}")
        logger.info(f"   JSON extraídos: {stats['json_ok']}")
        logger.info(f"   Product Page Hits: {stats['product_page_hits']}")
        logger.info(f"   Gift Cards omitidas: {stats['giftcards_omitted']}")
        logger.info(f"   Guardados exitosamente: {stats['saved']}")
        logger.info(f"   Duplicados omitidos: {stats['skipped_duplicate_domain']}")
        logger.info(f"   Ruido filtrado: {stats['skipped_noise']}")

    # -----------------------------------------------------------------------------
    # LAYER 1 - DISCOVERY (ddgs + recall alto + fallback)
    # -----------------------------------------------------------------------------
    def layer_1_discovery(self, query: str, region: str = "co-co", timelimit: str = "y"):
        """
        Capa 1: Descubrimiento con recall alto.
        - Evita sintaxis OR/paréntesis (Bing/DDGS suele fallar).
        - Usa fallback automático si el primer set no devuelve nada.
        - Filtra términos basura antes de retornar.
        """
        query = (query or "").strip()
        if not query:
            return []

        # Si el usuario pasó URL, listo
        if query.startswith("http://") or query.startswith("https://"):
            return [query]

        # ⚠️ duckduckgo_search fue renombrado a ddgs
        try:
            from ddgs import DDGS
        except Exception:
            # Fallback a duckduckgo_search si ddgs no está instalado
            try:
                from duckduckgo_search import DDGS
                logger.warning("⚠️ Usando duckduckgo_search (deprecado). Considera instalar: pip install ddgs")
            except Exception:
                logger.error("❌ Falta paquete 'ddgs'. Instala con: pip install ddgs")
                return []

        logger.info(f"📡 Capa 1: Buscando candidatos en DDGS (region={region}, timelimit={timelimit})")

        # Set A (amplio, funciona mejor en Bing) - V4 Shopify-Only
        dorks_primary = [
            f'inurl:/products/ "{query}"',
            f'inurl:/products/ "{query}" site:.co',
            f'"powered by shopify" "{query}"',
            f'site:myshopify.com "{query}"',
            f'inurl:/collections/ "{query}"',
        ]

        # Set B (fallback más amplio si sale 0)
        dorks_fallback = [
            f'"{query}" shopify',
            f'"{query}" "cdn.shopify.com"',
            f'"{query}" "/cdn/shop/"',
            f'"{query}" "cart.js"',
        ]

        candidates = set()

        def _run_dorks(dorks):
            with DDGS() as ddgs:
                for dork in dorks:
                    logger.info(f"   🔎 Dork: {dork}")
                    try:
                        # max_results conservador para no rate-limit
                        results = ddgs.text(dork, region=region, timelimit=timelimit, max_results=8)
                        if results:
                            for r in results:
                                link = r.get("href") or r.get("url")
                                if link:
                                    candidates.add(link)
                        time.sleep(1.2)
                    except Exception as e:
                        logger.warning(f"      ⚠️ Error dork: {e}")
                        time.sleep(2.0)

        _run_dorks(dorks_primary)

        # fallback si no hay nada
        if not candidates:
            logger.warning("   🧯 0 resultados con dorks primary. Ejecutando fallback...")
            _run_dorks(dorks_fallback)

        # Limpieza Anti-Basura V4
        clean = set()
        noise_count = 0
        
        for u in candidates:
            if not u:
                continue
            u = u.strip()
            u_lower = u.lower()
            
            # Filtro términos basura en URL
            if any(t in u_lower for t in self.bad_terms):
                logger.debug(f"   🗑️ Ruido filtrado (término basura): {u}")
                noise_count += 1
                continue
            
            # remove tracking fragments
            u = u.split("#")[0]
            # No borramos siempre query params porque a veces vienen URLs de producto con ?variant=...
            # pero sí removemos trackers comunes
            u = re.sub(r"(\?|&)(utm_[^=]+|gclid|fbclid)=[^&]+", "", u, flags=re.IGNORECASE).rstrip("?&")
            clean.add(u)

        logger.info(f"✨ Capa 1: {len(clean)} candidatos únicos (filtrados {noise_count} ruido).")
        return list(clean)

    # -----------------------------------------------------------------------------
    # LAYER 2 - VERIFY SHOPIFY (cart.js hard + fallback footprints)
    # -----------------------------------------------------------------------------
    def layer_2_verify_shopify_hard(self, url: str):
        """
        Retorna: (is_shopify: bool, html_cache: str, reason: str)

        1) /cart.js hard check
        2) fallback: footprints en HTML home/product
        """
        url = self._ensure_scheme(url)
        root_url, _ = self._root_and_netloc(url)

        try:
            # 1) Hard check: cart.js
            cart_url = f"{root_url}/cart.js"
            try:
                r = self.session.get(cart_url, timeout=4, allow_redirects=True)
                ct = (r.headers.get("Content-Type") or "").lower()

                if r.status_code == 200 and ("json" in ct or "javascript" in ct):
                    text_low = (r.text or "").lower()

                    # Guard anti-bloqueo HTML
                    if "<html" in text_low or "<!doctype" in text_low:
                        return False, "", "cart.js devolvió HTML (bloqueo/WAF)"

                    # Señales típicas de cart.js
                    if any(tok in text_low for tok in ["items", "token", "note", "attributes"]):
                        # Cache HTML home para capa 4
                        html_cache = ""
                        try:
                            r_home = self.session.get(root_url, timeout=5)
                            if r_home.status_code == 200:
                                html_cache = r_home.text or ""
                        except Exception:
                            pass
                        return True, html_cache, "cart.js OK"
            except Exception:
                pass

            # 2) Fallback footprints
            html_cache = ""
            try:
                r2 = self.session.get(url, timeout=6, allow_redirects=True)
                if r2.status_code >= 400:
                    r2 = self.session.get(root_url, timeout=6, allow_redirects=True)

                html_cache = r2.text or ""
                h = html_cache.lower()

                signals = 0
                if "myshopify.com" in h:
                    signals += 2
                if "cdn.shopify.com" in h or "shopifycdn.net" in h:
                    signals += 2
                if "/cdn/shop/" in h:
                    signals += 2
                if "shopify.routes" in h or "shopify.shop" in h:
                    signals += 2
                if "__st" in h or "shopifyanalytics" in h:
                    signals += 2
                if "shopify-payment" in h:
                    signals += 1

                if signals >= 2:
                    return True, html_cache, f"footprints signals={signals}"
            except Exception:
                pass

            return False, "", "sin señales Shopify"

        except Exception as e:
            return False, "", f"error capa2: {e}"

    # -----------------------------------------------------------------------------
    # LAYER 3 - JSON EXTRACTION (limit=10 + best pick)
    # -----------------------------------------------------------------------------
    def layer_3_smart_json_extraction(self, url: str):
        """
        Retorna: (data: dict|None, reason: str)

        Estrategias:
        - producto: /products/handle.json
        - colección: /collections/x/products.json?limit=10
        - root: /products.json?limit=10
        Selección: mejor producto (no giftcard, con imágenes, con variants, con precio)
        """
        url = self._ensure_scheme(url)
        base_url = url.split("#")[0].rstrip("/")
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"

        endpoints = []

        # Product page
        if "/products/" in base_url and not base_url.endswith(".json"):
            endpoints.append(base_url.split("?")[0] + ".json")

        # Collection page
        if "/collections/" in base_url:
            endpoints.append(base_url.split("?")[0] + "/products.json?limit=10")

        # Root fallback
        endpoints.append(root + "/products.json?limit=10")

        last_err = "no intentado"
        for ep in endpoints:
            data, reason = self._fetch_and_pick_product(ep, url)
            if data:
                data["json_source"] = ep
                return data, "ok"
            last_err = reason

        return None, last_err

    def _fetch_and_pick_product(self, endpoint: str, original_url: str):
        """
        endpoint: .../products.json?limit=10  o  .../handle.json
        Retorna: (normalized_product|None, reason)
        """
        try:
            r = self.session.get(endpoint, timeout=6, allow_redirects=True)
            if r.status_code != 200:
                return None, f"http {r.status_code}"

            # A veces WAF devuelve HTML con 200
            ct = (r.headers.get("Content-Type") or "").lower()
            if "json" not in ct and "javascript" not in ct and "text/plain" not in ct:
                txt = (r.text or "").lower()
                if "<html" in txt or "<!doctype" in txt:
                    return None, "endpoint devolvió HTML (bloqueo/WAF)"

            raw = r.json()

            products = []
            if isinstance(raw, dict) and "product" in raw:
                products = [raw["product"]]
            elif isinstance(raw, dict) and "products" in raw:
                products = raw.get("products") or []
            else:
                return None, "json inesperado"

            if not products:
                return None, "sin products"

            best = self._pick_best_product(products)
            if not best:
                return None, "sin producto válido (filtros)"

            return self._normalize_product(best, original_url), "ok"

        except Exception as e:
            return None, f"json parse/exception: {e}"

    def _pick_best_product(self, products: list):
        """
        Escoge el mejor producto para "muestra":
        - no giftcard
        - tiene variants
        - tiene imágenes
        - tiene precio > 0
        - preferimos títulos decentes (no vacío)
        """
        for p in products:
            title = (p.get("title") or "").strip()
            title_low = title.lower()
            ptype_low = (p.get("product_type") or "").strip().lower()

            if not title:
                logger.debug("      Saltando producto sin título")
                continue
            
            # Filtro Gift Cards V4
            if any(k in title_low for k in self.giftcard_keywords) or "gift" in ptype_low:
                logger.debug(f"      Saltando Gift Card: {title}")
                continue

            variants = p.get("variants") or []
            if not variants:
                logger.debug(f"      Saltando sin variantes: {title}")
                continue

            price = variants[0].get("price", 0)
            try:
                price_f = float(price)
            except Exception:
                price_f = 0.0
            if price_f <= 0:
                logger.debug(f"      Saltando sin precio válido: {title}")
                continue

            images = p.get("images") or []
            if not images:
                logger.debug(f"      Saltando sin imágenes: {title}")
                continue

            logger.debug(f"      ✓ Producto válido seleccionado: {title}")
            return p

        return None

    def _normalize_product(self, p: dict, original_url: str):
        variants = p.get("variants") or []
        price = variants[0].get("price", 0) if variants else 0

        images = p.get("images") or []
        # Shopify a veces trae images como list[dict] con src o como list[str]
        img_urls = []
        for img in images:
            if isinstance(img, dict) and img.get("src"):
                img_urls.append(img["src"])
            elif isinstance(img, str):
                img_urls.append(img)

        # Detect Page Type (Mejorado V4)
        parsed = urlparse(original_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        
        p_type = "other"
        if "/products/" in original_url:
            p_type = "product_page"
        elif "/collections/" in original_url:
            p_type = "collection_page"
        elif original_url == root or original_url == root + "/":
            p_type = "home_page"

        return {
            "title": p.get("title"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "price": price,
            "variants_count": len(variants),
            "images": img_urls,
            "body_html": p.get("body_html"),
            "handle": p.get("handle"),
            "published_at": p.get("published_at"),
            "tags": p.get("tags", []),
            "page_type_detected": p_type,
            "candidate_kind": "product_page" if p_type == "product_page" else "other",
        }

    # -----------------------------------------------------------------------------
    # LAYER 4 - SCORING (dropship likelihood + Meta Ads Check)
    # -----------------------------------------------------------------------------
    def layer_4_scoring_system(self, data: dict):
        """
        Retorna: (bool, reason)
        Score >= 2.5 pasa.
        """
        score = 0.0
        details = []

        html = (data.get("_html_cache") or "").lower()
        netloc = data.get("netloc", "")

        # 0) Meta Ads API Check (La prueba de fuego)
        meta_token = os.getenv("META_ADS_TOKEN")
        has_ads = False
        if meta_token and netloc:
            try:
                # Buscamos por dominio exacto
                ads_found = self._check_meta_ads_api(netloc, meta_token)
                if ads_found > 0:
                    score += 5.0 # Instant winner
                    details.append(f"MetaAdsActive({ads_found})")
                    has_ads = True
                    data["has_active_ads"] = True
                    data["ads_count"] = ads_found
            except Exception as e:
                logger.warning(f"   ⚠️ Meta Ads API error: {e}")

        # 1) Apps típicas (señal fuerte)
        dropship_apps = [
            "loox",
            "alireviews",
            "judge.me",
            "reconvert",
            "vitals",
            "privy",
            "dsers",
            "oberlo",
            "aftership",
            "trackingmore",
        ]
        found_apps = [a for a in dropship_apps if a in html]
        if found_apps:
            score += 3.0
            details.append(f"Apps:{len(found_apps)}")

        # 2) Señales de "stack ecommerce común"
        if "/policies/" in html:
            score += 1.0
            details.append("Policies")
        if ("track" in html and ("order" in html or "pedido" in html)) or "aftership" in html:
            score += 1.0
            details.append("Tracking")
        if any(k in html for k in ["discount", "oferta", "promo", "cupon", "coupon"]):
            if score > 0:
                score += 0.25
                details.append("Promo")

        # 3) Vendor analysis (anti marcas grandes)
        vendor = (data.get("vendor") or "").strip().lower()
        forbidden = [
            "nike",
            "adidas",
            "apple",
            "samsung",
            "sony",
            "zara",
            "hm",
            "h&m",
            "decathlon",
        ]
        if any(f in vendor for f in forbidden):
            return False, "Marca prohibida"

        if vendor in ["default vendor", "myshopify", ""]:
            score += 2.0
            details.append("VendorGen")

        # 4) Variants muy altas suele ser retail (penaliza suave)
        if (data.get("variants_count") or 0) > 50:
            score -= 1.0
            details.append("ManyVariants")

        # 5) Tags con import (señal leve)
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tags_low = [str(t).lower() for t in tags]
        if any("import" in t for t in tags_low):
            score += 1.0
            details.append("TagImport")

        # Rescue logic
        title = (data.get("title") or "")
        
        # Si tiene anuncios activos, pasa seguro
        if has_ads:
             return True, f"Score {score} (Meta Ads Confirmed) [{', '.join(details)}]"

        if score < 2.5 and len(title) > 24 and score >= 1.5:
            return True, f"Score {score} (LongTitleRescue) [{', '.join(details)}]"

        if score >= 2.5:
            return True, f"Score {score} [{', '.join(details)}]"

        return False, f"Score bajo ({score}) [{', '.join(details)}]"

    def _check_meta_ads_api(self, query: str, token: str) -> int:
        """
        Consulta a Meta Ads Library API para ver si hay anuncios activos.
        Retorna: Número de anuncios encontrados (aprox).
        """
        url = "https://graph.facebook.com/v19.0/ads_archive"
        params = {
            "search_terms": query,
            "ad_active_status": "ACTIVE",
            "ad_reached_countries": "['CO']", # Ajustable según región objetivo
            "access_token": token,
            "limit": 5 # Solo queremos saber si existen, no bajar todos
        }
        
        try:
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                # data['data'] es la lista de anuncios
                count = len(data.get("data", []))
                return count
            elif r.status_code == 400:
                 # Token invalido o error de query
                 logger.warning(f"Meta API 400: {r.text}")
                 return 0
            else:
                return 0
        except:
            return 0

    # -----------------------------------------------------------------------------
    # LAYER 5 - SCREENSHOT (optional)
    # -----------------------------------------------------------------------------
    def layer_5_visual_capture(self, url: str):
        """
        Full page screenshot con Playwright (móvil).
        """
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            logger.warning("⚠️ Playwright no instalado. Instala con: pip install playwright && playwright install")
            return None

        try:
            SCREEN_DIR = "raw_data/screenshots"
            os.makedirs(SCREEN_DIR, exist_ok=True)

            safe = "".join([c if c.isalnum() else "_" for c in url.split("//")[-1]])[:60]
            filename = f"{safe}.png"
            path = os.path.join(SCREEN_DIR, filename)

            if os.path.exists(path):
                return path

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.set_default_timeout(30000)
                page.goto(url, wait_until="domcontentloaded")

                try:
                    page.wait_for_load_state("networkidle", timeout=3500)
                except Exception:
                    pass

                # Scroll para lazy load
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.5)

                page.screenshot(path=path, full_page=True)
                browser.close()

            return path
        except Exception as e:
            logger.warning(f"⚠️ Error screenshot: {e}")
            return None

    # -----------------------------------------------------------------------------
    # SAVE
    # -----------------------------------------------------------------------------
    def save_data(self, data: dict):
        data["scraped_at"] = datetime.now().isoformat()
        date_str = datetime.now().strftime("%Y%m%d")

        os.makedirs("raw_data", exist_ok=True)
        fname = f"raw_data/shopify_candidates_{date_str}.jsonl"

        try:
            with open(fname, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"⚠️ save_data failed: {e}")

    # -----------------------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------------------
    def _ensure_scheme(self, url):
        if not url.startswith("http"):
            return "https://" + url
        return url

    def _root_and_netloc(self, url):
        parsed = urlparse(self._ensure_scheme(url))
        root = f"{parsed.scheme}://{parsed.netloc}"
        return root, parsed.netloc

    def _sanitize_and_rank_candidates(self, urls: list):
        """
        Ordena y limpia la lista:
        - Prioriza myshopify.com si el usuario quiere
        - Quita duplicados
        """
        # (Lógica simple por ahora)
        return sorted(list(set(urls)))

    def _is_noise(self, url: str):
        u = url.lower()
        if any(d in u for d in self.noise_domains):
            return True
        return False

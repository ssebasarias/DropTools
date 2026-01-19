import logging
import json
import time
import requests
import sys
import os
from urllib.parse import urlparse

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("shopify_tester")

# Force UTF-8 for Windows consoles (Robust)
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-CO,es;q=0.9,en;q=0.8'
}

class ShopifyFinderTester:
    def __init__(self):
        self.seen_domains = set()
        # Session setup with retries
        self.session = requests.Session()
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retries = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.headers.update(HEADERS)

    def run(self, query):
        logger.info(f"🚀 Iniciando Shopify Tester CONTROLADO para: '{query}'")
        
        # ──────── CAPA 1: Descubrimiento ────────
        urls = self.layer_1_discovery(query)
        
        # Max 20 para test rápido
        urls = sorted(urls)[:20] 
        
        print("\n" + "="*60)
        print(f"🔎 LISTA DE CANDIDATOS FILTRADOS ({len(urls)})")
        print("="*60)
        for i, u in enumerate(urls, 1):
            print(f"{i}. {u}")
        print("="*60 + "\n")

        stats = {'found': len(urls), 'shopify_ok': 0, 'json_ok': 0, 'product_page_hits': 0, 'gift_cards_skipped': 0, 'noise_filtered': 0}
        
        for i, url in enumerate(urls, 1):
            if stats['json_ok'] >= 5:
                logger.info("✅ Alcanzado objetivo de 5 hits JSON. Cortando test.")
                break

            print(f"\n[{i}/{len(urls)}] 👉 Evaluando: {url}")
            
            # Normalizar URL base para deduplicación robusta
            try:
                parsed = urlparse(url)
                if not parsed.scheme: # Fix scheme missing
                    url = "https://" + url.lstrip("/")
                    parsed = urlparse(url)
                
                netloc = parsed.netloc.lower().replace("www.", "")
                if netloc in self.seen_domains:
                    print(f"   ⏩ SKIP: Dominio ya procesado ({netloc})")
                    continue
                self.seen_domains.add(netloc)
            except Exception as e:
                print(f"   ⚠️ SKIP: URL inválida ({e})")
                continue

            # ──────── CAPA 2: Verificación (Cart.js Hard Check) ────────
            is_valid_shopify = self.layer_2_verify_shopify(url)
            
            if not is_valid_shopify:
                print("   ❌ Capa 2: No es Shopify (o falló verificación)")
                continue
            
            stats['shopify_ok'] += 1
            print("   ✅ Capa 2: Shopify Confirmado")

            # ──────── CAPA 3: Extracción JSON Inteligente ────────
            data = self.layer_3_try_json(url)
            if data:
                # Add extra Metadata for review
                data['root_url'] = f"{parsed.scheme}://{parsed.netloc}"
                data['netloc'] = netloc
                
                # Track product_page hits
                if data.get('candidate_kind') == 'product_page':
                    stats['product_page_hits'] += 1
                
                self.save_data(data)
                stats['json_ok'] += 1
                print(f"   🎉 CAPA 3 EXITOSA! {data['title']} (${data['price']})")
                print(f"      Fuente: {data['json_source']}")
                print(f"      Tipo: {data.get('candidate_kind', 'N/A')} | Página: {data.get('page_type_detected', 'N/A')}")
            else:
                print("   ⚠️ Capa 3: JSON falló (Endpoints bloqueados o vacíos)")

        print("\n" + "="*60)
        print("🏁 RESUMEN FINAL:")
        print(f"   Total candidatos encontrados: {stats['found']}")
        print(f"   Shopify confirmados: {stats['shopify_ok']}")
        print(f"   JSON extraídos exitosamente: {stats['json_ok']}")
        print(f"   Product Page Hits (páginas de producto): {stats['product_page_hits']}")
        print(f"   Gift Cards omitidas: {stats['gift_cards_skipped']}")
        print(f"   URLs filtradas por ruido: {stats['noise_filtered']}")
        print("="*60)

    def layer_1_discovery(self, query):
        if query.startswith("http"): return [query]

        logger.info(f"📡 Buscando en DDG...")
        candidates = set()
        
        # Dorks V4 (Shopify-Only - Igual que shopify_finder)
        dorks = [
            f'inurl:/products/ "{query}" site:.co',
            f'inurl:/products/ "{query}" ("cdn.shopify.com" OR "/cdn/shop/")',
            f'inurl:/products/ "{query}" ("cart.js" OR "products.json")',
            f'inurl:/products/ "{query}" ("shopify" OR "myshopify")',
            f'site:myshopify.com "{query}"',
        ]

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for dork in dorks:
                    logger.info(f"   🔎 Dork: {dork}")
                    try:
                        results = ddgs.text(dork, region='co-co', timelimit='y', max_results=5)
                        if results:
                            for r in results:
                                link = r.get('href')
                                if link: candidates.add(link)
                        time.sleep(2) 
                    except Exception as e:
                        logger.warning(f"      ⚠️ Dork error: {e}")
                        time.sleep(3) 
        except Exception as e:
            logger.error(f"❌ Error DDG: {e}")

        # Limpieza Anti-Basura (V4)
        clean_urls = set()
        domain_blacklist = ['amazon', 'ebay', 'mercadolibre', 'youtube', 'pinterest', 'facebook', 'instagram', 'play.google.com']
        bad_terms = ['magis', 'iptv', 'descargar', 'instalar', 'smart tv', 'apk', 'guia', 'tutorial', 'download', 'gratis', 'free']
        
        noise_count = 0
        for u in candidates:
            u_lower = u.lower()
            
            # Filtro dominios
            if any(b in u_lower for b in domain_blacklist): 
                noise_count += 1
                continue
            
            # Filtro términos basura
            if any(t in u_lower for t in bad_terms):
                logger.info(f"   🗑️ Ruido filtrado: {u}")
                noise_count += 1
                continue
            
            u_clean = u.split('#')[0] # Remove hash but keep query params
            clean_urls.add(u_clean)
        
        logger.info(f"✨ {len(clean_urls)} candidatos limpios (filtrados {noise_count} ruido)")
        return list(clean_urls)

    def layer_2_verify_shopify(self, url):
        """
        Capa 2: Hard Check con /cart.js + Fallback
        """
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        
        try:
            # 1. Cart.js Check (Definitivo)
            # Timeout corto (3s) para ser rápidos
            r = self.session.get(f"{root}/cart.js", timeout=3, allow_redirects=True)
            ct = r.headers.get('Content-Type', '').lower()
            
            if r.status_code == 200 and ('json' in ct or 'javascript' in ct):
                text = r.text.lower()
                if '<html' in text or '<!doctype' in text: return False
                
                # Extended tokens check
                if 'items' in text or 'token' in text or 'attributes' in text or 'note' in text:
                    return True
            
            # 2. Fallback Footprints (Original URL then Root)
            try:
                r_page = self.session.get(url, timeout=4)
                html = r_page.text.lower()
                if 'myshopify.com' in html: return True
                if 'cdn.shopify.com' in html: return True
                if '/cdn/shop/' in html: return True
            except: pass
            
            # Root check if page failed
            r_home = self.session.get(root, timeout=4)
            html = r_home.text.lower()
            if 'myshopify.com' in html: return True
            if 'cdn.shopify.com' in html: return True
            if '/cdn/shop/' in html: return True
            if 'shopify.routes' in html: return True
            
        except Exception as e:
            # logger.debug(f"Verificación falló: {e}")
            pass
            
        return False

    def layer_3_try_json(self, url):
        """
        Capa 3: Strategy Selector + Gift Card Filter
        """
        base_url = url.split('?')[0].rstrip('/')
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        
        endpoints = []
        
        # 1. Product Page Strategy
        if '/products/' in base_url and not base_url.endswith('.json'):
            endpoints.append(base_url + '.json')
            
        # 2. Collection Page Strategy
        if '/collections/' in base_url:
            endpoints.append(base_url + '/products.json?limit=1')
            
        # 3. Root Fallback
        endpoints.append(root + '/products.json?limit=1')
        
        for ep in endpoints:
            try:
                # Timeout ligeramente mayor para data (5s)
                r = self.session.get(ep, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    
                    products = []
                    if 'product' in data:
                        products = [data['product']]
                    elif 'products' in data and len(data['products']) > 0:
                        products = data['products']
                    
                    # FILTRADO ANTI GIFT CARDS (V4)
                    gift_card_keywords = ['gift card', 'giftcard', 'tarjeta regalo', 'gift-card']
                    best_product = None
                    
                    for p in products:
                        # Filtro 1: Gift Cards por tipo
                        if p.get('product_type', '').lower() == 'gift card':
                            print(f"      [DEBUG] Saltando Gift Card (tipo): {p.get('title')}")
                            continue
                        
                        # Filtro 2: Gift Cards por título
                        title_lower = p.get('title', '').lower()
                        if any(kw in title_lower for kw in gift_card_keywords):
                            print(f"      [DEBUG] Saltando Gift Card (título): {p.get('title')}")
                            continue
                        
                        # Filtro 3: Validaciones básicas
                        variants = p.get('variants', [])
                        if not variants: 
                            print(f"      [DEBUG] Saltando sin variantes: {p.get('title')}")
                            continue
                        
                        if not p.get('images'):
                            print(f"      [DEBUG] Saltando sin imágenes: {p.get('title')}")
                            continue
                        
                        # Filtro 4: Precio válido
                        price_val = variants[0].get('price', 0)
                        try:
                            if float(price_val) <= 0:
                                print(f"      [DEBUG] Saltando sin precio: {p.get('title')}")
                                continue
                        except:
                            continue
                        
                        # Producto válido encontrado
                        best_product = p
                        print(f"      [DEBUG] ✓ Producto válido: {p.get('title')}")
                        break
                    
                    if best_product:
                        variants = best_product.get('variants', [])
                        price = variants[0].get('price', 0)
                        
                        # Detect Page Type
                        p_type = 'other'
                        if '/products/' in url: 
                            p_type = 'product_page'
                        elif '/collections/' in url: 
                            p_type = 'collection_page'
                        elif url == root or url == root + '/':
                            p_type = 'home_page'
                        
                        return {
                            'title': best_product.get('title'),
                            'vendor': best_product.get('vendor'),
                            'product_type': best_product.get('product_type'),
                            'price': price,
                            'url': url,
                            'json_source': ep,
                            'page_type_detected': p_type,
                            'candidate_kind': 'product_page' if p_type == 'product_page' else 'other'
                        }
            except Exception as e:
                print(f"      [DEBUG] Error en endpoint {ep}: {e}")
                pass
                
        return None

    def save_data(self, data):
        """
        Imprime resultado en consola en lugar de guardar en archivo
        """
        print("-" * 40)
        print("💾 DATOS EXTRAÍDOS (Simulacro de guardado):")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 40)

if __name__ == "__main__":
    tester = ShopifyFinderTester()
    query = sys.argv[1] if len(sys.argv) > 1 else "corrector de postura"
    tester.run(query)

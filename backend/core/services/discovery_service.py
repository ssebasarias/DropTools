import time
import requests
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple
from duckduckgo_search import DDGS
from django.utils import timezone
from datetime import timedelta
from core.models import DomainReputation, MarketAnalysisReport, CompetitorFinding

class DiscoveryService:
    """
    [DSA-05] Explorer / Discovery Worker
    Busca competidores en la web y filtra candidatos Shopify.
    """
    
    # Circuit Breaker
    MAX_LIKELY_DOMAINS = 15 # Circuit Breaker por reporte
    
    # Rate Limiting (configurable)
    DELAY_BETWEEN_QUERIES = 1.0  # Segundos entre queries (reducido de 2s)
    DELAY_BETWEEN_CHECKS = 0.1   # Segundos entre verificaciones de dominio
    
    # Timeouts
    REQUEST_TIMEOUT = 4  # Segundos para requests HTTP
    
    # User Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    @classmethod
    def run_discovery(cls, report: MarketAnalysisReport) -> Dict[str, Any]:
        """
        Ejecuta el pipeline de descubrimiento para un reporte dado.
        Actualiza el reporte con estadisticas y estado.
        """
        fingerprint = report.search_fingerprint or {}
        queries = fingerprint.get("generated_queries", [])
        negative_terms = fingerprint.get("negative_terms", [])
        
        if not queries:
            return {"error": "No queries in fingerprint"}
            
        found_candidates_raw = 0
        likely_shopify_domains = set() # Store root domains
        discovery_log = []
        
        # DDGS Instance
        # max_results controla cuantos resultados trae por query (paginado implicito)
        MAX_RESULTS_PER_QUERY = 15 
        
        try:
            with DDGS() as ddgs:
                for query in queries:
                    # Circuit Breaker Check
                    if len(likely_shopify_domains) >= cls.MAX_LIKELY_DOMAINS:
                        msg = f"⚡ Circuit breaker triggered: {len(likely_shopify_domains)} likely domains found."
                        discovery_log.append(msg)
                        break
                    
                    discovery_log.append(f"🔍 Searching: {query}")
                    
                    # Ejecutar Búsqueda
                    try:
                        results = ddgs.text(
                            query, 
                            region='wt-wt', 
                            safesearch='off', 
                            max_results=MAX_RESULTS_PER_QUERY,
                            backend="api" # 'api', 'html', or 'lite'
                        )
                        
                        if not results:
                            discovery_log.append("   -> No results found.")
                            continue

                        for r in results:
                            url = r.get('href', '')
                            # body = r.get('body', '') # Snippet opcional para analisis
                            
                            if not url: continue
                            
                            # 1. Filtro Negativo (Marketplaces, Redes Sociales, etc)
                            # Añadimos mas ruido comun
                            noise = negative_terms + ['pinterest', 'facebook', 'instagram', 'youtube', 'tiktok', 'linkedin']
                            if any(neg in url.lower() for neg in noise):
                                continue

                            found_candidates_raw += 1
                            
                            # 2. Extract Root Domain (Basic logic)
                            domain = cls._get_domain_from_url(url)
                            if not domain or domain in likely_shopify_domains:
                                continue # Dedupe por dominio
                            
                            # 3. Check Domain Reputation Cache first
                            cached_dr = DomainReputation.objects.filter(domain=domain).first()
                            
                            is_likely = False
                            reasons = {}
                            
                            is_likely = False
                            reasons = {}
                            domain_obj = None # We need the DB object reference
                            
                            if cached_dr and cached_dr.shopify_last_checked_at:
                                # Usar cache si es reciente (e.g. 7 dias)
                                # Si ya sabemos que es Shopify, genial.
                                domain_obj = cached_dr
                                if cached_dr.is_shopify:
                                    is_likely = True
                                    reasons = cached_dr.shopify_likely_reasons
                                    discovery_log.append(f"   -> Cache Hit (Shopify): {domain}")
                            else:
                                # 4. Live Check (Expensive)
                                is_likely, reasons = cls._check_is_shopify_live(url)
                                if is_likely:
                                    discovery_log.append(f"   -> Detected Shopify: {domain}")
                                
                                # Guardar/Actualizar Reputacion y obtener objeto
                                domain_obj = cls._update_domain_reputation(domain, is_likely, reasons)

                            if is_likely and domain_obj:
                                likely_shopify_domains.add(domain)
                                
                                # CRITICAL FIX: Persist the finding for Verification Phase
                                # Capturamos el titulo del resultado DDG si existe, sino None
                                title_found = r.get('title', '')
                                
                                CompetitorFinding.objects.create(
                                    report=report,
                                    domain_ref=domain_obj,
                                    url_found=url,
                                    title_detected=title_found[:500] if title_found else "",
                                    match_type="PENDING" # Esperando verificacion SigLIP
                                )
                            
                            # Rate limit interno entre verificaciones
                            time.sleep(cls.DELAY_BETWEEN_CHECKS)

                        # Politeness entre queries
                        time.sleep(cls.DELAY_BETWEEN_QUERIES) 

                    except Exception as e:
                        discovery_log.append(f"❌ Error in query '{query}': {e}")
                        time.sleep(5)

        except Exception as e:
            return {"error": str(e), "log": discovery_log}

        # Actualizar Reporte
        report.candidates_found_raw = found_candidates_raw
        report.shopify_likely_candidates_count = len(likely_shopify_domains)
        report.candidates_processed = len(likely_shopify_domains) # En V1 asumimos procesados = shopify encontrados
        
        # Guardar audit log (DSA v1.0 - Debugging y Trazabilidad)
        # Sanitizar para SQL_ASCII (remover emojis y caracteres especiales)
        sanitized_log = [
            msg.encode('ascii', 'ignore').decode('ascii') 
            for msg in discovery_log
        ]
        report.audit_log = sanitized_log
        report.save()
        
        return {
            "status": "success",
            "found_raw": found_candidates_raw,
            "shopify_count": len(likely_shopify_domains),
            "log": discovery_log
        }

    @staticmethod
    def _get_domain_from_url(url: str) -> str:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            # Quitar www.
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except:
            return ""

    @staticmethod
    def _check_is_shopify_live(url: str) -> Tuple[bool, Dict]:
        """
        Verifica si una URL pertenece a una tienda Shopify.
        Método: Heurísticas de HTML, Headers y /cart.js (más confiable).
        """
        try:
            # Timeout corto. User-Agent real.
            headers = {"User-Agent": DiscoveryService.USER_AGENT}
            
            reasons = {}
            score = 0
            
            # MÉTODO 1: Verificar /cart.js (MÁS CONFIABLE)
            # Shopify siempre expone este endpoint
            try:
                parsed = urlparse(url)
                cart_url = f"{parsed.scheme}://{parsed.netloc}/cart.js"
                cart_response = requests.get(cart_url, timeout=3, headers=headers)
                
                if cart_response.status_code == 200:
                    # Verificar si la respuesta es JSON válido (Shopify devuelve JSON)
                    try:
                        cart_data = cart_response.json()
                        if 'items' in cart_data or 'token' in cart_data:
                            reasons['cart_js_endpoint'] = True
                            score += 0.7  # Señal muy fuerte
                    except:
                        pass
            except:
                pass  # Si falla, continuamos con otros métodos
            
            # MÉTODO 2: Análisis de HTML (si cart.js no fue concluyente)
            if score < 0.7:
                response = requests.get(url, timeout=4, headers=headers)
                text = response.text.lower()
                
                # Señales Shopify Fuertes
                if '/cdn/shop/' in text:
                    reasons['cdn_structure'] = True
                    score += 0.5
                
                if 'window.shopify' in text or 'shopify.modules' in text:
                    reasons['js_variables'] = True
                    score += 0.5
                    
                if 'myshopify.com' in text:
                    reasons['myshopify_trace'] = True
                    score += 0.3
                    
                if 'shopify-payment-button' in text:
                    reasons['payment_button'] = True
                    score += 0.4

            # Decisión
            if score >= 0.4:
                return True, reasons
                
        except requests.exceptions.Timeout:
            # Timeout - sitio muy lento o inaccesible
            pass
        except requests.exceptions.SSLError:
            # Error SSL - certificado inválido
            pass
        except requests.exceptions.ConnectionError:
            # Sitio caído o DNS inválido
            pass
        except Exception:
            # Otros errores inesperados
            pass
            
        return False, {}

    @staticmethod
    def _update_domain_reputation(domain: str, is_shopify: bool, reasons: Dict) -> DomainReputation:
        """
        Actualiza o Crea el registro de DomainReputation.
        Returns the object.
        """
        obj, created = DomainReputation.objects.update_or_create(
            domain=domain,
            defaults={
                'is_shopify': is_shopify,
                'shopify_likely_reasons': reasons,
                'shopify_last_checked_at': timezone.now(),
                'shopify_cache_expires_at': timezone.now() + timedelta(days=14), # 2 Semanas de cache
                'shopify_likely_score': 0.9 if is_shopify else 0.1
            }
        )
        return obj

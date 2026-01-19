from typing import List, Dict, Any
from core.models import UniqueProductCluster, Product

class QuerySynthesizer:
    """
    [DSA-03] Query Synthesizer
    Responsable de generar estrategias de búsqueda ("Fingerprints") inteligentes 
    para encontrar competidores en la web abierta.
    
    Output: SearchFingerprint (JSON)
    """
    
    COMMON_MARKETPLACES = [
        "amazon", "ebay", "aliexpress", "temu", "mercadolibre", "walmart", "etsy"
    ]
    
    @classmethod
    def generate_fingerprint(cls, cluster: UniqueProductCluster) -> Dict[str, Any]:
        """
        Genera un SearchFingerprint completo para un cluster de productos.
        """
        # 1. Obtener datos semilla
        concept = cluster.concept_name or ""
        representative_product = cluster.representative_product
        title = representative_product.title if representative_product else ""
        
        if not concept and not title:
            return {"error": "No concept or title available"}
            
        # 2. Extraer Keywords Nucleares
        keywords = cls._extract_keywords(concept, title)
        core_term = keywords.get("core", "")
        
        # Validación: Longitud mínima de 3 caracteres para evitar queries inútiles
        if not core_term or len(core_term) < 3:
             return {
                 "error": "Could not extract valid core keyword",
                 "debug": {
                     "concept": concept,
                     "title": title[:50] if title else "",
                     "extracted_core": core_term
                 }
             }

        # 3. Construir Queries por Estrategia
        queries = []
        
        # Strategy A: Direct Concept Search
        # "depiladora laser"
        queries.append(core_term)
        
        # Strategy B: Commercial Intent (English & Spanish standard triggers)
        # "comprar depiladora laser", "buy laser hair remover"
        queries.append(f"comprar {core_term}")
        queries.append(f"buy {core_term}")
        queries.append(f"tienda {core_term}")
        
        # Strategy C: Shopify Specific Footprint
        # site:myshopify.com "depiladora laser"
        queries.append(f'site:myshopify.com "{core_term}"')
        
        # 4. Definir Términos Negativos (Circuit Breaker de Ruido)
        # Excluir grandes marketplaces para encontrar dropshippers independientes
        negative_terms = cls.COMMON_MARKETPLACES
        
        return {
            "cluster_id": cluster.cluster_id,
            "seed_concept": concept,
            "core_keywords": keywords,
            "generated_queries": queries,
            "negative_terms": negative_terms,
            "version": "v1.0"
        }

    # Stop words comunes en español e inglés
    STOP_WORDS = {
        # Español
        'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'para', 'con', 'sin', 'por', 'en', 'a', 'y', 'o', 'que', 'su', 'sus',
        # Inglés
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'
    }
    
    @staticmethod
    def _extract_keywords(concept: str, title: str) -> Dict[str, str]:
        """
        Extrae la keyword principal con filtrado de stop words.
        Prioridad: Concepto > Título limpio > Título crudo.
        """
        core = ""
        
        if concept and concept.lower() != "unknown" and len(concept) > 3:
            core = concept.lower()
        elif title:
            # Filtrar stop words y tomar palabras significativas
            words = title.lower().split()
            # Filtrar stop words y palabras muy cortas
            filtered_words = [
                w for w in words 
                if w not in QuerySynthesizer.STOP_WORDS and len(w) > 2
            ]
            # Tomar hasta 4 palabras significativas
            core = " ".join(filtered_words[:4])
            
        # Limpieza básica
        core = core.replace('"', '').replace('(', '').replace(')', '').strip()
        
        # Validación: longitud mínima de 3 caracteres
        if len(core) < 3:
            core = ""
        
        return {
            "core": core,
            "secondary": "" # Placeholder para future expansion
        }

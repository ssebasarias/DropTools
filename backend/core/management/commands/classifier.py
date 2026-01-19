
from django.core.management.base import BaseCommand
from core.models import Product
from core.ai_classifier import classify_term
import sys
import pathlib
import logging
import time
from django.db import connection, close_old_connections # Required for stability

# Setup Logging
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("classifier")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# 1. File Handler
if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "classifier.log", encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 2. Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class Command(BaseCommand):
    help = 'Agent 1: Taxonomy Classifier (The Labeler). Uses Visual Consensus.'

    def handle(self, *args, **options):
        logger.info("🏷️ AGENT 1: TAXONOMY CLASSIFIER STARTED (SCHOOL MODE 🏫)")
        
        while True:
            # 0. Stability: Close old DB connections to prevent timeouts overnight
            close_old_connections()
            
            # 1. Fetch Candidates (Priority: Products with EYES 👀)
            # Queremos priorizar productos que YA tienen vector visual para aplicar el consenso.
            # Si procesamos productos sin vector, el classifier estaría "ciego" y perderíamos la oportunidad de aprender.
            
            # Query A: Sin clasificar + CON Vector (Los mejores alumnos)
            pending_products = Product.objects.filter(
                taxonomy_concept__isnull=True,
                is_active=True,
                productembedding__embedding_visual__isnull=False
            ).order_by('-created_at')[:50]
            
            # Query B: Fallback (Si no hay productos vectorizados listos, procesar lo que haya)
            if not pending_products.exists():
                pending_products = Product.objects.filter(
                    taxonomy_concept__isnull=True,
                    is_active=True
                ).order_by('-created_at')[:50]
            
            if not pending_products.exists():
                logger.info("💤 Todo limpio. Esperando nuevos productos... (30s)")
                time.sleep(30)
                continue
            
            logger.info(f"⚡ Procesando lote de {pending_products.count()} productos... (Prioridad Visual)")
            
            for prod in pending_products:
                try:
                    self.classify_product(prod)
                    # Rate limit suave para no saturar Ollama
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"❌ Error classifying product {prod.product_id}: {e}")
            
            # Sleep between batches
            time.sleep(2)

    def classify_product(self, prod):
        # 0. COMBINED CONTEXT: Title + Intro of Description
        term = prod.title or ""
        desc = prod.description or ""
        
        # Limpiamos HTML basico
        import re
        clean_desc = re.sub(r'<[^>]+>', ' ', desc)[:200]
        full_context = f"{term} | {clean_desc}".strip()[:300]
        
        # 1. FETCH SOURCE CATEGORIES (Brújula de Contexto)
        source_cats = []
        try:
            # Importar aquí para evitar circular imports si fuera el caso, aunque models ya está importado arriba
            from core.models import ProductCategory
            # Obtener nombres de categorías vinculadas
            cats_qs = ProductCategory.objects.filter(product=prod).select_related('category')
            source_cats = [pc.category.name for pc in cats_qs]
            if source_cats:
                logger.info(f"   🗺️  Source Context: {source_cats}")
        except Exception as e:
            logger.warning(f"   ⚠️ Error fetching source categories: {e}")

        # 2. VISUAL CONSENSUS CHECK (Consultar al Agente 2 + Historial)
        visual_hints = []
        try:
            with connection.cursor() as cur:
                # Verificar si tiene vector
                cur.execute("SELECT embedding_visual FROM product_embeddings WHERE product_id = %s", (prod.product_id,))
                row = cur.fetchone()
                
                if row and row[0]:
                    vector = row[0]
                    # Buscar vecinos visuales CON sus categorías (Query Avanzada)
                    # Usamos ARRAY_AGG para compactar las categorías de cada vecino en una sola fila
                    sql_neighbors = """
                        SELECT 
                            p.title,
                            p.taxonomy_concept,
                            COALESCE(
                                (
                                    SELECT string_agg(c.name, ', ')
                                    FROM product_categories pc
                                    JOIN categories c ON pc.category_id = c.id
                                    WHERE pc.product_id = p.product_id
                                ), 
                                ''
                            ) as neighbor_cats
                        FROM product_embeddings pe
                        JOIN products p ON pe.product_id = p.product_id
                        WHERE pe.product_id != %s 
                        AND pe.embedding_visual IS NOT NULL
                        ORDER BY pe.embedding_visual <=> %s
                        LIMIT 5
                    """
                    cur.execute(sql_neighbors, (prod.product_id, vector))
                    
                    neighbors = cur.fetchall()
                    if neighbors:
                        # Estructura Rica: Lista de Diccionarios
                        # [ {"title": "X", "concept": "Y", "categories": ["A", "B"]}, ... ]
                        rich_neighbors = []
                        for n_title, n_concept, n_cats_str in neighbors:
                            cat_list = [c.strip() for c in n_cats_str.split(',')] if n_cats_str else []
                            
                            neighbor_data = {
                                "title": n_title,
                                "categories": cat_list
                            }
                            # Si ya tiene concepto, también ayuda
                            if n_concept:
                                neighbor_data["concept"] = n_concept
                                
                            rich_neighbors.append(neighbor_data)
                            
                        visual_hints = rich_neighbors
                        logger.info(f"   👀 Rich Visual Context Found ({len(visual_hints)} neighbors)")
                    else:
                        logger.info(f"   🕶️ No visual neighbors found for context.")
        except Exception as e:
            logger.warning(f"   ⚠️ Error fetching visual context: {e}")

        # 3. CALL AGENT 1 (THE BRAIN) WITH RICH CONTEXT
        # Ahora pasamos visual_context Y source_categories
        result = classify_term(full_context, visual_context=visual_hints, source_categories=source_cats)
        
        if result:
            # Extract fields
            concept_name = result.get('concept_name')
            industry = result.get('parent_industry')
            level = result.get('classification') # INDUSTRY, CONCEPT, PRODUCT
            
            if concept_name:
                prod.taxonomy_concept = concept_name
                prod.taxonomy_industry = industry
                prod.taxonomy_level = level
                # UPDATE SPECIFIC FIELDS ONLY to avoid touching generated columns like profit_margin
                prod.save(update_fields=['taxonomy_concept', 'taxonomy_industry', 'taxonomy_level'])
                logger.info(f"   ✅ {term[:30]}... -> [{industry}] > [{concept_name}]")
            else:
                logger.warning(f"   ⚠️ No concept name returned for {term}")
                prod.taxonomy_concept = "UNKNOWN"
                prod.save(update_fields=['taxonomy_concept'])

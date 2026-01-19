import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
# Intento de compatibilidad Pydantic V1/V2
try:
    from langchain_core.pydantic_v1 import BaseModel, Field
except ImportError:
    from pydantic import BaseModel, Field
from typing import Literal

# Log Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 1. Definir Estructura de Salida (JSON Estricto) ---
class TaxonomyClassification(BaseModel):
    term: str = Field(description="El término analizado")
    classification: Literal["INDUSTRY", "CONCEPT", "PRODUCT", "UNKNOWN"] = Field(
        description="Nivel taxonómico: INDUSTRY (Sector amplio), CONCEPT (Tipo de producto genérico), PRODUCT (Item específico/marca)."
    )
    parent_industry: str = Field(description="La industria madre sugerida (ej: 'Tecnología', 'Moda').")
    reason: str = Field(description="Breve explicación de por qué se clasificó así.")

# --- 2. El Taxónomo ---
class TaxonomistAI:
    def __init__(self, model_name="llama3.2:3b"):
        # URL de host.docker.internal para conectar desde Docker al Windows Host
        # Si corre local fuera de docker, usar localhost.
        self.llm = ChatOllama(
            model=model_name,
            base_url="http://host.docker.internal:11434", 
            temperature=0, # Temperatura 0 para máxima precisión y determinismo
            format="json" # Forzar modo JSON nativo de Ollama
        )
        
        # Estructura del Prompt con Few-Shot Learning (Ejemplos + Contexto Visual)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto Taxónomo de E-commerce Senior. Tu trabajo es clasificar términos de búsqueda en 3 niveles jerárquicos.

            NIVELES:
            1. INDUSTRY (Industria/Categoría Padre): Términos muy amplios.
               Ejemplos: "Tecnología", "Hogar", "Deportes", "Belleza", "Ropa Mujer", "Herramientas".
            
            2. CONCEPT (Concepto/Bucket): Grupos específicos de productos que satisfacen la misma necesidad.
               Ejemplos: "Audífonos Inalámbricos", "Silla Ergonómica", "Bota Motociclista", "Bota de Lluvia".
               *NIVEL CRÍTICO: El nombre debe ser canónico y estandarizado.*

            3. PRODUCT (Producto Específico): Items con marca/modelo.

            TU MISIÓN - ANÁLISIS CRUZADO:
            Recibirás:
            A. El Producto Objetivo (Título + Sus Categorías).
            B. VECINOS VISUALES (Una lista de productos que se ven iguales). **CADA VECINO TRAE SU TÍTULO Y SUS PROPIAS CATEGORÍAS.**

            ESTRATEGIA DE RAZONAMIENTO (Multifactorial):
            1. Analiza el Título y Categorías del objetivo.
            2. Observa a los VECINOS:
               - **Patrones en Títulos:** ¿Qué palabras clave se repiten en los títulos de los vecinos? (Ej: todos dicen "Motocross" o "Gaming").
               - **Consenso de Categorías:** ¿Qué etiquetas tienen en común?
            3. SÍNTESIS INTELIGENTE:
               - Usa los títulos vecinos para extraer el nombre más preciso del objeto.
               - Usa las categorías para obtener el contexto o industria correcta.
            
            Responde SIEMPRE en este JSON:
            {{
                "term": "termino original",
                "classification": "NIVEL",
                "concept_name": "Nombre Estandarizado (Singular, Capitalized)",
                "parent_industry": "Industria Madre",
                "reason": "Explicación breve citando patrones encontrados en Títulos y Categorías vecinas"
            }}
            """),
            ("user", """
            Clasifica este producto:
            Título Objetivo: '{input}'
            Categorías Objetivo: {source_categories}
            
            --- VECINOS VISUALES (Evidencia Comparativa) ---
            {context_visual}
            """)
        ])

        # Chain: Prompt -> LLM -> JSON Parser (implícito en el prompt o via structured_output)
        # Llama 3 suele ser muy bueno respondiendo JSON si se le pide format="json" en el constructor.
        self.chain = self.prompt | self.llm

    def classify(self, term, visual_context=None, source_categories=None):
        """
        Clasifica un término usando Llama 3 con contexto enriquecido.
        visual_context: Lista de DICCIONARIOS (Rich Objects del vecino).
        source_categories: Lista de strings (categorías del scraper).
        """
        try:
            # Preparar contexto visual (Ahora es una lista de objetos, pasamos a JSON string para la IA)
            import json
            ctx_str = "No disponible"
            if visual_context and len(visual_context) > 0:
                # Formateamos bonito para que la IA lo lea fácil
                # Ejemplo: 
                # 1. "Titulo Vecino" (Cats: [A, B])
                lines = []
                for i, v in enumerate(visual_context):
                    t = v.get('title', 'N/A')
                    cats = ", ".join(v.get('categories', []))
                    con = v.get('concept', '')
                    line = f"- Vecino {i+1}: {t}"
                    if cats: line += f" | Tags: [{cats}]"
                    if con: line += f" | Concept: {con}"
                    lines.append(line)
                ctx_str = "\n".join(lines)
            
            # Preparar contexto categorías propias
            cats_str = "No disponibles"
            if source_categories and len(source_categories) > 0:
                cats_str = ", ".join(source_categories)
            
            # Invocar
            response = self.chain.invoke({
                "input": term, 
                "context_visual": ctx_str,
                "source_categories": cats_str
            })
            
            # Parsear contenido
            import json
            content = response.content.strip()
            
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                data = json.loads(json_str)
                return data
            else:
                logger.error(f"❌ Failed to parse JSON from AI: {content}")
                return None

        except Exception as e:
            logger.error(f"❌ AI Classification Error: {e}")
            return None

# Singleton Helper
_taxonomist = None
def classify_term(term, visual_context=None, source_categories=None):
    global _taxonomist
    if _taxonomist is None:
        _taxonomist = TaxonomistAI()
    return _taxonomist.classify(term, visual_context, source_categories)

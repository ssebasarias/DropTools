# =========================================================================================================
# 🧠 DAHELL INTELLIGENCE - ARQUITECTURA DEL SISTEMA DE ANÁLISIS DE MERCADO (v1.0)
# =========================================================================================================
# Este documento define la arquitectura, flujo de datos y responsabilidad única de cada worker en el
# ecosistema Dahell Intelligence. Cada componente funciona de manera autónoma pero interconectada,
# formando un pipeline de inteligencia continua para Dropshipping.
# =========================================================================================================

"""
VISIÓN GENERAL DEL FLUJO:
1. Ingesta (Scraper/Loader) -> 2. Visión (Vectorizer) -> 3. Entendimiento (Classifier) ->
4. Agrupación (Clusterizer) -> 5. Tendencias (Market Trender) -> 6. Inteligencia Competitiva (Meta Scholar) ->
7. Auditoría Forense (Shopify Auditor) -> ✅ DECISIÓN FINAL (Océano Azul / Rojo)
"""

# =========================================================================================================
# 1. WORKER: SCRAPER (El Recolector)
# =========================================================================================================
# PROPÓSITO:
#   Obtener la materia prima (productos crudos) de la fuente de proveedores (Dropi) de manera masiva y constante.
#
# FUNCIONAMIENTO:
#   - Navega automáticamente el catálogo de Dropi.
#   - Extrae datos básicos: Título, Precio, URL Imagen, Descripción.
#   - Genera archivos JSONL por lotes en /raw_data.
#
# CONEXIÓN (Entrada -> Salida):
#   - [Entrada]: Catálogo Web Dropi.
#   - [Salida]: Archivos JSONL en disco para el Loader.

# =========================================================================================================
# 2. WORKER: LOADER (El Guardian)
# =========================================================================================================
# PROPÓSITO:
#   Validar, limpiar y cargar los datos crudos en la Base de Datos, asegurando integridad.
#
# FUNCIONAMIENTO:
#   - Lee JSONL generados por el Scraper.
#   - Verifica duplicados y actualiza precios/stock si el producto ya existe.
#   - Descarta datos corruptos.
#   - Comprime los archivos JSONL en un archivo tar.gz.
#
# CONEXIÓN:
#   - [Entrada]: Archivos JSONL.
#   - [Salida]: Registros en tabla PostgreSQL `products`.

# =========================================================================================================
# 3. WORKER: VECTORIZER (El Ojo Biónico)
# =========================================================================================================
# PROPÓSITO:
#   Dotar al sistema de "visión" convirtiendo imágenes en representaciones matemáticas (embeddings).
#
# FUNCIONAMIENTO:
#   - Descarga la imagen del producto.
#   - Usa modelo SigLIP (Google) para generar un vector de 1152 dimensiones.
#   - Este vector permite búsquedas por similitud visual ("buscar cosas que se vean como esto").
#
# CONEXIÓN:
#   - [Entrada]: URL Imagen de `products`.
#   - [Salida]: Vector almacenado en tabla `product_embeddings`.

# =========================================================================================================
# 4. WORKER: CLASSIFIER (El Taxónomo)
# =========================================================================================================
# PROPÓSITO:
#   Entender qué es el producto y clasificarlo en conceptos semánticos, corrigiendo títulos basura.
#
# FUNCIONAMIENTO:
#   - Recibe: Imagen Original + Título.
#   - Consulta: Busca los 5 "vecinos visuales" más cercanos en la DB usando pgvector y obtiene el titulo de los productos vecinos para compararlos con el titulo original y obtener el concepto.
#   - Decide: Usa IA para asignar un `Concepto` (ej: "Zapatos hombre") estandarizado.
#     - Si no existe concepto adecuado, crea uno nuevo.
#
# CONEXIÓN:
#   - [Entrada]: Producto vectorizado.
#   - [Salida]: Asignación de `concept_id` en el producto.

# =========================================================================================================
# 5. WORKER: CLUSTERIZER (El Estratega de Oferta)
# =========================================================================================================
# PROPÓSITO:
#   Detectar la saturación interna en Dropi agrupando proveedores que venden lo mismo.
#
# FUNCIONAMIENTO:
#   - Analiza productos dentro del mismo Concepto.
#   - Agrupa variaciones del mismo ítem en un "Cluster Único" (UniqueProductCluster).
#   - Calcula métricas: "¿Cuántos proveedores venden esto?" (Saturación de Oferta).
#   - Filtra y marca "Candidatos" (Productos con baja competencia interna).
#
# CONEXIÓN:
#   - [Entrada]: Productos clasificados.
#   - [Salida]: Registros en `unique_product_clusters` con `dropi_competition_tier`.

# =========================================================================================================
# 6. WORKER: MARKET TRENDER (El Futurologo) -- [Antes Google Trends Worker]
# =========================================================================================================
# PROPÓSITO:
#   Validar la demanda del mercado (pasado, presente y futuro) y filtrar por tendencia.
#
# FUNCIONAMIENTO:
#   - Recibe los "Candidatos" del Clusterizer.
#   - Analiza tendencias de búsqueda globales/regionales.
#   - Usa búsqueda semántica (pgvector + LangChain) para conectar búsquedas (ej: "regalo navidad")
#     con categorías de productos ("Juguetes", "Belleza"), descartando ruido (ej: política, fútbol ya que esto no vende).
#   - Predice: Sube el ranking de categorías "Winner" en ascenso y baja las estancadas.
#
# CONEXIÓN:
#   - [Entrada]: Clusters Candidatos.
#   - [Salida]: Score de Tendencia (`trend_score`) y validación de demanda.

# =========================================================================================================
# 7. WORKER: META SCHOLAR (El Espía de Publicidad) -- [Antes Meta Ads Analyzer]
# =========================================================================================================
# PROPÓSITO:
#   Investigar la competencia real activa en redes sociales (Facebook/Instagram Ads).
#
# FUNCIONAMIENTO:
#   - Recibe candidatos filtrados por tendencia.
#   - Busca en Meta Ads Library API usando el concepto del producto.
#   - Inteligencia: 
#     - Agrupa anuncios por `page_id` (Competidor Único).
#     - Analiza `ad_creation_time` para detectar "Winners" (Activos > 1 mes).
#     - Analiza `ad_creative_body` (Copy) para confirmar si es el mismo producto.
#     - Extrae: Nombres de Fanpages, Links, Plataformas.
#
# CONEXIÓN:
#   - [Entrada]: Candidatos con tendencia positiva.
#   - [Salida]: Lista de `CompetitorFindings` (Sospechosos) con datos de pauta.

# =========================================================================================================
# 8. WORKER: SHOPIFY AUDITOR (El Auditor Forense) -- [Antes Shopify Finder]
# =========================================================================================================
# PROPÓSITO:
#   Validación final "sobre el terreno" de los competidores detectados.
#
# FUNCIONAMIENTO:
#   - Recibe la lista de competidores/links detectados por Meta Scholar.
#   - Navega a sus sitios web (Shopify).
#   - Validación Visual 2.0: Toma screenshot/foto del producto en la tienda rival.
#   - Compara (usando Vectorizer) esa foto con la foto de TU producto original.
#   - Si hay match visual: Extrae precio de venta, variantes, y confirma "Competidor Verificado".
#
# CONEXIÓN:
#   - [Entrada]: Links de competidores de Meta Scholar.
#   - [Salida]: Reporte Final de Saturación, Precios de Mercado y Confirmación de Competencia.

# =========================================================================================================

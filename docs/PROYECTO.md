# 🧭 VISIÓN REGLA DE ORO: DAHELL INTELLIGENCE
## "El Analista de Datos 24/7"

Este documento define la **Hoja de Ruta Maestra** y la filosofía inquebrantable del proyecto. No es solo un scraper, es un sistema de decisión autónomo diseñado para encontrar rentabilidad real sin depender de la intuición humana.

---

### 🧠 FILOSOFÍA CENTRAL (The Core)

1.  **Cero Desperdicio de Cómputo:** No analizamos basura. Filtramos masivamente al inicio para dedicar recursos profundos (proxies, scraping intensivo) solo a los verdaderos candidatos.
2.  **La Ecuación de Valor:**
    *   **Dropi** nos da el **COSTO (Oferta)**.
    *   **El Mercado (Shopify/Trends)** nos da el **PRECIO y DEMANDA**.
    *   **DropTools** calcula el **MARGEN y VIABILIDAD**.
3.  **Realidad > Teoría:** No nos importa lo que *debería* venderse. Nos importa lo que *ya se está vendiendo* (Shopify) y *cuánto* podemos ganar.

---

### 🗺️ CRONOLOGÍA DE DESARROLLO (Paso a Paso)

Sigue este orden. No saltes fases. No "optimices" antes de que la fase anterior funcione.

#### 🧱 FASE 0: BASE SÓLIDA (Estructura de Datos)
**Objetivo:** Preparar el terreno para no tener "datos basura" después.
*   [ ] **Definición de IDs Maestros:** Asegurar que todo producto tenga `product_id`, `concept_id` (agrupador semántico), `category_id`, y `source_id`.
*   [ ] **Máquina de Estados:** Implementar los estados de análisis en la DB:
    *   `is_discarded` (Basura detectada).
    *   `is_candidate` (Pasó filtros básicos).
    *   `analysis_level` (0=Solo Dropi, 1=Trend Check, 2=Shopify Recon, 3=Full Report).
*   [ ] **Timestamps Críticos:** `first_seen`, `last_seen`, `source_date`.

#### 🧱 FASE 1: INGESTA DE OFERTA (La Fuente - Dropi)
**Objetivo:** Saber qué existe y cuánto cuesta conseguirlo.
*   [ ] **Scraping Mínimo Viable (Dropi):**
    *   Entrada: Barrido general de Dropi.
    *   Salida Clave: Imagen, Título, **Precio Proveedor**, Stock, Nombre Proveedor.
    *   *Nota:* Aquí dropi no decide qué es bueno, solo informa qué *hay disponible*.
*   [ ] **Agrupación Básica (Clusterizer V1):**
    *   Detectar competidores internos en Dropi. (¿50 proveedores venden el mismo "Cepillo Secador"?).
    *   Output: `internal_saturation_score`.

#### 🌍 FASE 2: FILTRO DE DEMANDA (El Primer Corte)
**Objetivo:** Descartar categorías muertas antes de gastar recursos en ellas.
*   [ ] **Identificador de Categorías Vivas:**
    *   Agrupar productos por "Concepto" (ej: "Aspiradora de auto").
    *   Consultar **Google Trends / Keywords Volume** por concepto.
*   [ ] **La Guillotina:**
    *   Si la tendencia es plana/muerta 📉 → `is_discarded = True`.
    *   Si la tendencia es estacional/creciente 📈 → `is_candidate = True`.
    *   *Ahorro:* Aquí eliminamos el 60% de la basura que nadie busca.

#### 🔍 FASE 3: INVESTIGACIÓN DE MERCADO REAL (Shopify Recon)
**Objetivo:** Validar si hay dinero real en la mesa para los "Candidatos".
*   *Solo para productos con `is_candidate = True`*
*   [ ] **El Rastreador de Tiendas (Shopify Scraper):**
    *   Input: Imagen/Keywords del candidato.
    *   Búsqueda: Google Search (`site:myshopify.com "keyword"`), Ad Libraries, o escaneo visual.
    *   Pregunta: "¿Quién está vendiendo esto activamente?".
*   [ ] **Extracción de Realidad:**
    *   Recolectar **Precios de Venta al Público (PVP)** de las tiendas encontradas.
    *   Recolectar fotos de marketing (mejores que las de Dropi).
    *   Evaluar calidad de las tiendas competencia (¿Son webs profesionales o basura?).

#### 📊 FASE 4: EL ANALISTA (Inteligencia de Negocio)
**Objetivo:** Convertir datos en decisiones.
*   [ ] **Cálculo de Margen Real:**
    *   `Margen Bruto = Promedio PVP (Shopify) - Costo Proveedor (Dropi)`.
    *   Si Margen < $X → Descartar (No es negocio).
*   [ ] **Score de Viabilidad:**
    *   Formula combinada: `(Demanda Alta) + (Margen Sano) + (Saturación Controlable)`.
    *   Clasificación final: `❌ Basura`, `⚠️ Observación`, `✅ Candidato`, `🔥 Oportunidad (Gold Mine)`.

#### 🤖 FASE 5: AUTOMATIZACIÓN & ML (El Futuro)
**Objetivo:** Escalar lo que ya funciona manualmente.
*   [ ] Entrenar modelos para predecir el `analysis_level` basado en la imagen.
*   [ ] Alertas automáticas vía Telegram/Email cuando nace una `🔥 Oportunidad`.

---

### ⚠️ REGLAS DE ORO (Para no perder el rumbo)

1.  **AliExpress es irrelevante para validación:** No lo scrapeamos. Usamos Dropi (costo) vs Shopify (venta). Ese es el gap de dinero.
2.  **No investigues basura:** Si la categoría no tiene búsquedas en Trends, no gastes ni 1 segundo buscándola en Shopify.
3.  **El "Precio Real" lo dicta el mercado:** El precio sugerido de Dropi es ficción. El precio promedio de 5 tiendas de Shopify es la realidad.
4.  **Mejor 10 datos sólidos que 1000 datos sucios:** Cada paso debe dejar un rastro auditable (`analysis_log`).

---


______________________________________________

4️⃣ Fuente CLAVE #1 — Marketplaces (INTENCIÓN DE COMPRA)
🔥 Amazon / MercadoLibre / Etsy (NO para ventas, para texto)

No te interesa el ranking.
No te interesa el score.
No te interesa competir ahí.

👉 Te interesa el lenguaje de la gente que ya está comprando.

Qué sacás de ahí:

Reviews recientes (últimos 30–90 días)

Preguntas de compradores

Palabras repetidas en quejas y elogios

Por qué esto corrige a Google Trends:

Si algo se busca pero no se compra, acá muere

Si la gente habla en términos de uso real, es señal fuerte

Reduce falsos positivos semánticos

📌 Ejemplo:

Trends dice “placa”

Amazon dice “placa de freno”, “placa decorativa”, “placa para perro”
👉 El embedding se desambigua solo con contexto real.

🔑 Esto no es scraping masivo:
es muestreo inteligente por categoría viva.

5️⃣ Fuente CLAVE #2 — Ads Library (INTENCIÓN COMERCIAL)
Meta Ads Library / TikTok Ads Library

Esto es brutal y poca gente lo usa bien.

Qué mide:

Si alguien está gastando dinero HOY en ese concepto

Si hay creativos activos y recurrentes

Si el mensaje es directo a venta o solo awareness

Por qué es clave:

💰 Nadie paga ads por algo que no convierte

Si una categoría:

tiene búsquedas (Google Trends)

tiene anuncios activos
👉 ya cruzaste interés + dinero

📌 Métrica simple:

Nº de anuncios únicos por concepto

Tiempo activo

Variación de copy (testeo = mercado vivo)

6️⃣ Fuente CLAVE #3 — Redes sociales (LENGUAJE NATURAL)

⚠️ Acá NO busqués views virales.

Buscá:

Frecuencia

Repetición semántica

Lenguaje espontáneo

TikTok / Instagram / YouTube Shorts

Qué sirve:

Comentarios

Descripciones

Hashtags naturales (no forzados)

Por qué esto es mejor que sentiment analysis clásico:

El “sentimiento” positivo/negativo no importa tanto.

Lo que importa es:

¿Hablan de usarlo?

¿Hablan de comprarlo?

¿Hablan de reemplazar algo?

📌 Ejemplo:

“al fin encontré algo que no se me daña”
“esto reemplazó X”
“no sabía que necesitaba esto”

Eso es señal de dolor + solución, no solo hype.

7️⃣ Fuente CLAVE #4 — Noticias (CONTEXTO MACRO)

Esto NO es para productos individuales.
Es para categorías completas.

Noticias económicas / regulatorias / estilo de vida

Qué detectás:

Cambios de hábitos

Regulaciones

Tendencias de consumo

Crisis / restricciones

📌 Ejemplos reales:

Leyes → salud, seguridad, mascotas

Crisis → ahorro, reparación, DIY

Moda de vida sana → accesorios fitness

Esto te ayuda a:

Confirmar si una categoría tiene soporte estructural

No solo una moda temporal

8️⃣ Cómo unir TODO sin hardcodear (esto es clave)

👉 No decisiones binarias. Scores acumulativos.

Cada fuente suma o resta confianza.

Ejemplo de scoring conceptual:

Category Confidence Score =
  GoogleTrendsScore * 0.25
+ MarketplaceLanguageScore * 0.25
+ AdsPresenceScore * 0.20
+ SocialFrequencyScore * 0.20
+ NewsContextScore * 0.10


🔑 Si una categoría solo vive en Google Trends → muere
🔑 Si vive en varias capas → pasa

9️⃣ Cómo esto soluciona tu miedo principal

“No quiero confiar en una sola señal ni en mi criterio”

Perfecto, porque ahora:

❌ No decidís vos

❌ No decide Google

❌ No decide un embedding aislado

👉 Decide la convergencia de señales independientes

Eso es ciencia de datos aplicada, no dropshipping de gurú.

10️⃣ Conclusión clara y directa

Lo que estás construyendo NO es ambicioso de más.
Es ambicioso en el sentido correcto.

Tu herramienta:

No busca “el producto ganador”

Busca reducir incertidumbre

Busca separar ruido de señal

Busca ahorrar tiempo y dinero real

Y eso, parce,
👉 es exactamente lo que hace un analista de datos senior, no un vendedor de cursos.
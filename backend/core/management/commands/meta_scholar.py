
import os
import time
import requests
import json
import logging
from collections import defaultdict
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import UniqueProductCluster, CompetitorFinding

# LangChain Imports - Opcional si el entorno no los tiene, pero el Dockerfile los instaló
try:
    from langchain_community.chat_models import ChatOllama
    from langchain.prompts import ChatPromptTemplate
    from langchain.output_parsers import PydanticOutputParser
    from pydantic import BaseModel, Field
    from typing import List
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Setup Logger
logger = logging.getLogger("meta_scholar")
logger.setLevel(logging.INFO)

# --- Estructuras de Salida (Schema) ---
class CompetitorAnalysis(BaseModel):
    is_direct_competitor: bool = Field(description="True si el anuncio vende LA MISMA solución/producto, False si es diferente.")
    reasoning: str = Field(description="Explicación breve de por qué es o no competencia directa.")
    marketing_angle: str = Field(description="Ángulo de marketing detectado (ej: 'Dolor', 'Belleza', 'Humor').")
    target_audience_guess: str = Field(description="Público objetivo deducido (ej: 'Madres primerizas', 'Deportistas').")

class Command(BaseCommand):
    help = 'Worker: Meta Scholar (Competitive Intelligence via Meta Ads)'
    
    META_API_URL = "https://graph.facebook.com/v19.0/ads_archive"
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Meta Ads Analyzer Worker Started (LangChain Mode)"))
        
        if not LANGCHAIN_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ LangChain no está instalado. Revisa requirements.txt"))
            return

        # Configurar LLM (Ollama Local)
        # Asumimos que Ollama corre en el host o en un container 'ollama'.
        # Si corre en host, desde docker usamos host.docker.internal
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        self.llm = ChatOllama(model="llama3.2", base_url=ollama_base_url, temperature=0.0) # Low temp para analisis factual
        
        logger.info(f"🧠 LLM Configurado: Llama 3.2 en {ollama_base_url}")

        while True:
            token = os.getenv("META_ADS_TOKEN")
            if not token:
                logger.error("❌ META_ADS_TOKEN no encontrado en variables de entorno.")
                time.sleep(60)
                continue

            # Buscar candidatos (Clusters LOW que no han pasado por Meta Check)
            candidates = UniqueProductCluster.objects.filter(
                dropi_competition_tier='LOW',
                validation_log__icontains="meta_checked:false"
            ).order_by('-updated_at')[:3] # Procesamos de a 3 para no saturar LLM

            if not candidates.exists():
                # Fallback: Revisar recientes no chequeados
                candidates = UniqueProductCluster.objects.filter(
                    updated_at__gte=timezone.now() - timezone.timedelta(days=7)
                ).exclude(validation_log__icontains="meta_checked:true")[:3]
            
            if not candidates.exists():
                logger.info("💤 Sin tareas pendientes. Durmiendo 30s...")
                time.sleep(30)
                continue
            
            for cluster in candidates:
                try:
                    self.analyze_cluster_with_ai(cluster, token)
                except Exception as e:
                    logger.error(f"❌ Error en cluster {cluster.cluster_id}: {e}")
                    time.sleep(5)
            
            time.sleep(5)

    def fetch_meta_ads(self, query: str, token: str):
        # Misma lógica de fetch
        params = {
            "search_terms": query,
            "ad_active_status": "ACTIVE",
            "ad_reached_countries": "['CO']", 
            "access_token": token,
            "limit": 50, # Limitamos a 50 para no reventar contexto del LLM
            "fields": "id,page_id,page_name,ad_creation_time,ad_creative_body,ad_snapshot_url,publisher_platforms"
        }
        try:
            r = requests.get(self.META_API_URL, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json().get("data", [])
                return data
            return []
        except:
            return []

    def analyze_cluster_with_ai(self, cluster, token):
        query_term = cluster.concept_name or "Producto Genérico"
        logger.info(f"▶️ Analizando Cluster {cluster.cluster_id}: '{query_term}'...")
        
        # 1. Obtener Datos Crudos de Meta
        ads = self.fetch_meta_ads(query_term, token)
        if not ads:
            self.mark_cluster_checked(cluster, "No Ads Found (API)")
            return

        # 2. Agrupar por Competidor (Data Reduction)
        # LangChain no puede leer 500 anuncios uno por uno rápido. Agrupamos.
        competitors_map = defaultdict(lambda: {"copies": [], "platforms": set(), "oldest_ad": datetime.now(), "count": 0})
        
        now = datetime.now()
        for ad in ads:
            pid = ad.get('page_id')
            pname = ad.get('page_name', 'Unknown')
            copy = ad.get('ad_creative_body', '')
            created = ad.get('ad_creation_time', '')
            
            key = f"{pid}|{pname}"
            competitors_map[key]["copies"].append(copy[:300]) # Truncar copy para contexto
            competitors_map[key]["platforms"].update(ad.get('publisher_platforms', []))
            competitors_map[key]["count"] += 1
            
            if created:
                try:
                    dt = datetime.strptime(created[:10], "%Y-%m-%d")
                    if dt < competitors_map[key]["oldest_ad"]:
                        competitors_map[key]["oldest_ad"] = dt
                except: pass

        logger.info(f"   📉 Reducido a {len(competitors_map)} posibles competidores únicos.")

        # 3. Análisis Inteligente con LangChain (Competidor por Competidor)
        verified_competitors = []
        
        # Prompt Template
        parser = PydanticOutputParser(pydantic_object=CompetitorAnalysis)
        prompt = ChatPromptTemplate.from_template(
            """
            Eres un experto Analista de Mercado y E-commerce. Tu trabajo es validar competencia.
            
            PRODUCTO REFERENCIA (El mío):
            Concepto: {concept}
            
            POSIBLE COMPETIDOR (Anuncios encontrados):
            Nombre Tienda: {store_name}
            Textos de sus Anuncios:
            {ad_copies}
            
            TAREA:
            Analiza si este competidor vende EXACTAMENTE EL MISMO producto, una variante muy cercana, o algo diferente.
            Ignora si venden cosas vagamente relacionadas. Busco competencia directa.
            
            {format_instructions}
            """
        )

        for key, data in competitors_map.items():
            pid, pname = key.split("|")
            
            # Preparar contexto (unir copies únicos para no repetir)
            unique_copies = list(set(data["copies"]))[:3] # Max 3 ejemplos de texto
            ad_text_context = "\n---\n".join(unique_copies)
            
            if not ad_text_context.strip():
                continue # Sin texto no analizamos

            try:
                _input = prompt.format_messages(
                    concept=query_term,
                    store_name=pname,
                    ad_copies=ad_text_context,
                    format_instructions=parser.get_format_instructions()
                )
                
                # Invocar LLM
                response = self.llm.invoke(_input)
                analysis = parser.parse(response.content)
                
                if analysis.is_direct_competitor:
                    days_active = (now - data["oldest_ad"]).days
                    is_winner = days_active > 14
                    
                    # Guardar Hallazgo en DB para Shopify Finder
                    self.save_finding(cluster, pid, pname, analysis, is_winner, days_active)
                    verified_competitors.append(pname)
                    
                    logger.info(f"   🚨 Competencia DETECTADA: {pname} | Ángulo: {analysis.marketing_angle} | Winner: {is_winner}")
            
            except Exception as e:
                logger.warning(f"   ⚠️ Error LLM analizando {pname}: {e}")
                continue

        # 4. Actualizar Cluster Status
        if len(verified_competitors) > 3:
            cluster.market_saturation_level = "High (AI Verified)"
            cluster.dropi_competition_tier = "SATURATED"
            msg = f"LangChain detectó {len(verified_competitors)} competidores directos."
        elif len(verified_competitors) > 0:
            cluster.market_saturation_level = "Medium (AI Verified)"
            cluster.dropi_competition_tier = "MID"
            msg = f"LangChain detectó {len(verified_competitors)} competidores."
        else:
             msg = "LangChain revisó anuncios pero NO halló competencia directa (Semántica)."
        
        self.mark_cluster_checked(cluster, msg)

    def save_finding(self, cluster, page_id, page_name, analysis: CompetitorAnalysis, is_winner, days_active):
        # 1. Obtener o Crear Reporte para este Cluster (Requisito DB)
        report, _ = MarketAnalysisReport.objects.get_or_create(
            cluster=cluster,
            defaults={
                "market_state": "AI_IN_PROGRESS",
                "search_fingerprint": {"source": "MetaAdsAI"}
            }
        )
        
        # 2. Crear o Actualizar CompetitorFinding
        # Usamos image_url para guardar snapshot_url (screenshot_path no existe en este modelo)
        finding, created = CompetitorFinding.objects.get_or_create(
            report=report,
            url_found=f"https://facebook.com/{page_id}", 
            defaults={
                "match_type": "CONFIRMED_AI",
                "title_detected": f"{page_name} | {analysis.marketing_angle} (Active {days_active}d)",
                "image_url": f"https://graph.facebook.com/{page_id}/picture?type=large" # Placeholder válido o URL del ad si la tuvieramos a mano aqui
            }
        )
        
        # Actualizar datos
        finding.match_type = "WINNER" if is_winner else "CONFIRMED_AI"
        finding.title_detected = f"{page_name} | {analysis.marketing_angle} (Active {days_active}d)"
        finding.save()

    def mark_cluster_checked(self, cluster, msg):
        original = cluster.validation_log or ""
        new = f"{original}\n[MetaAI {timezone.now().strftime('%H:%M')}] {msg} | meta_checked:true"
        cluster.validation_log = new[-2000:]
        cluster.save()


import os
import time
import logging
import sys
import pathlib
import pandas as pd
import numpy as np
import django
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from django.db import connection
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

load_dotenv()

# Setup Django (para cuando corre como script independiente si fuera necesario)
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dahell.settings")
# django.setup()

from core.models import AIFeedback

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("trainer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "ai_trainer.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

class AITrainer:
    def __init__(self):
        self.min_samples_required = 20
        self.check_interval = 60 # Segundos entre chequeos

    def fetch_training_data(self):
        """Descarga el feedback humano de la base de datos."""
        feedbacks = AIFeedback.objects.filter(
            visual_score__isnull=False,
            text_score__isnull=False
        ).values('visual_score', 'text_score', 'final_score', 'decision', 'feedback')
        
        df = pd.DataFrame(list(feedbacks))
        if df.empty: return None
            
        def calculate_target(row):
            machine_good = 1 if row['decision'] in ['MATCH', 'CANDIDATE'] else 0
            human_agrees = 1 if row['feedback'] == 'CORRECT' else 0
            
            if machine_good and human_agrees: return 1      # TP (Bien hecho)
            if machine_good and not human_agrees: return 0  # FP (Mal, era distinto)
            if not machine_good and human_agrees: return 0  # TN (Bien rechazado)
            if not machine_good and not human_agrees: return 1 # FN (Mal, debio ser match)
            return 0

        df['target'] = df.apply(calculate_target, axis=1)
        return df

    def train_and_optimize(self):
        logger.info("🧠 Brain Scan: Analizando nuevos patrones de feedback...")
        
        df = self.fetch_training_data()
        if df is None:
            logger.info("   Zzz... No hay datos de entrenamiento aún.")
            return False

        current_count = len(df)
        logger.info(f"   Datos disponibles: {current_count} muestras.")
        
        if current_count < self.min_samples_required:
            logger.info(f"   Esperando más datos para aprender (Faltan {self.min_samples_required - current_count}).")
            return False

        # --- MACHINE LEARNING CORE ---
        logger.info("🔥 ENTRENANDO MODELO CEREBRAL...")
        X = df[['visual_score', 'text_score']]
        y = df['target']
        
        clf = LogisticRegression(fit_intercept=True)
        clf.fit(X, y)
        
        coef_visual = abs(clf.coef_[0][0])
        coef_text = abs(clf.coef_[0][1])
        bias = clf.intercept_[0]
        
        # Normalizar
        total_imp = coef_visual + coef_text
        if total_imp == 0: total_imp = 1
        
        learned_w_vis = coef_visual / total_imp
        learned_w_txt = coef_text / total_imp
        
        # --- ESTABILIZACIÓN (EMA) ---
        # No cambiamos de golpe, aprendemos suavemente
        ALPHA = 0.3 
        current_config = self.get_current_config()
        
        new_w_vis = (learned_w_vis * ALPHA) + (current_config['weight_visual'] * (1-ALPHA))
        new_w_vis = max(0.2, min(0.8, new_w_vis)) # Safety Limit
        new_w_txt = 1.0 - new_w_vis
        
        # Calcular Threshold ideal (Heurística simple basada en Bias)
        # Si el Bias es muy negativo, el modelo es pesimista -> Bajamos threshold
        # Si el Bias es positivo, el modelo es optimista -> Subimos threshold
        # Base = 0.68
        threshold_adj = 0.68 - (bias * 0.05) 
        new_threshold = max(0.5, min(0.85, threshold_adj))

        logger.info(f"💡 EUREKA! Nuevos Pesos Ideales Detectados:")
        logger.info(f"   Visual: {new_w_vis:.2f} (Antes: {current_config['weight_visual']:.2f})")
        logger.info(f"   Texto: {new_w_txt:.2f} (Antes: {current_config['weight_text']:.2f})")
        logger.info(f"   Umbral: {new_threshold:.2f}")

        # Guardar solo si hubo cambio significativo (> 1%)
        diff = abs(new_w_vis - current_config['weight_visual'])
        if diff > 0.01:
            self.update_db_config(new_w_vis, new_w_txt, new_threshold, current_count)
            return True
        else:
            logger.info("   Cambio insignificante. Manteniendo configuración actual.")
            return False

    def get_current_config(self):
        with connection.cursor() as cur:
            cur.execute("SELECT weight_visual, weight_text FROM cluster_config ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row: return {"weight_visual": row[0], "weight_text": row[1]}
            return {"weight_visual": 0.6, "weight_text": 0.4}

    def update_db_config(self, w_vis, w_txt, threshold, n_samples):
        with connection.cursor() as cur:
            cur.execute("""
                INSERT INTO cluster_config 
                (weight_visual, weight_text, threshold_visual_rescue, threshold_text_rescue, threshold_hybrid, version_note)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (w_vis, w_txt, 0.15, 0.95, threshold, f"AI Auto-Trained (N={n_samples})"))
            logger.info("✅ CEREBRO ACTUALIZADO. El Clusterizer usará estos nuevos parámetros.")

    def run_daemon(self):
        logger.info("🚀 AI TRAINER DAEMON INICIADO")
        logger.info("   Esperando auditorías humanas para aprender...")
        while True:
            try:
                self.train_and_optimize()
            except Exception as e:
                logger.error(f"❌ Error en entrenamiento: {e}")
            
            # Dormir y esperar siguiente ciclo
            time.sleep(self.check_interval)

class Command(BaseCommand):
    help = 'AI Trainer Daemon'

    def handle(self, *args, **options):
        trainer = AITrainer()
        trainer.run_daemon()

"""
Analizador de Reportes para Dropi
Este comando lee un reporte actual de Dropi y genera CSVs con todas las métricas del dashboard.

Genera los siguientes CSVs:
- metricas_generales: Totales, porcentajes, totalización
- utilidad_proyectada: Utilidad a diferentes % de efectividad
- impacto_cancelados: Impacto de cancelaciones
- finanzas_reales: Finanzas de entregados
- efectividad_resumen: Efectividad, tránsito, devolución
- conteos_por_estado: Conteos por cada estado
- efectividad_transportadora: Efectividad por transportadora
- rentabilidad_producto: Rentabilidad por producto
"""

import os
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand


class ReportAnalyzer:
    """
    Analizador de reportes de Dropi
    
    Funcionalidad:
    1. Lee un reporte actual de Dropi
    2. Calcula todas las métricas del dashboard
    3. Genera CSVs con todas las métricas para análisis
    """
    
    def __init__(self):
        """Inicializa el analizador"""
        self.logger = self._setup_logger()
        self.df = None
    
    def _setup_logger(self):
        """Configura el logger para el analizador"""
        logger = logging.getLogger('ReportAnalyzer')
        logger.setLevel(logging.INFO)
        
        # Limpiar handlers existentes
        logger.handlers.clear()
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            log_dir / f'reportanalyzer_{timestamp}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def load_report(self, reporte_path):
        """
        Carga el reporte actual desde un archivo Excel
        
        Args:
            reporte_path: Ruta al archivo Excel del reporte actual
        
        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        self.logger.info("="*80)
        self.logger.info("CARGANDO REPORTE ACTUAL")
        self.logger.info("="*80)
        
        try:
            if not os.path.exists(reporte_path):
                self.logger.error(f"[ERROR] El archivo no existe: {reporte_path}")
                return False
            
            self.logger.info(f"   Leyendo archivo: {reporte_path}")
            self.df = pd.read_excel(reporte_path)
            
            # Normalizar nombres de columnas
            self.df.columns = self.df.columns.str.strip()
            
            self.logger.info(f"   [OK] Reporte cargado: {len(self.df)} filas, {len(self.df.columns)} columnas")
            self.logger.info("="*80)
            
            return True
            
        except Exception as e:
            self.logger.error(f"   [ERROR] Error al cargar reporte: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _safe_get(self, row, col, default=0):
        """Obtiene un valor de forma segura, manejando NaN"""
        if col not in self.df.columns:
            return default
        value = row.get(col, default)
        if pd.isna(value):
            return default
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return value
        except:
            return default
    
    def calculate_metricas_generales(self):
        """
        Calcula las métricas generales del dashboard
        
        Returns:
            dict: Diccionario con las métricas generales
        """
        self.logger.info("   Calculando metricas generales...")
        
        # Total pedidos (órdenes únicas por ID)
        total_pedidos = self.df['ID'].nunique()
        
        # Total guías (guías únicas, excluyendo vacías)
        guias_col = 'NÚMERO GUIA'
        if guias_col in self.df.columns:
            total_guias = self.df[guias_col].notna().sum()
        else:
            total_guias = 0
        
        # Productos vendidos (suma de cantidades)
        cantidad_col = 'CANTIDAD'
        if cantidad_col in self.df.columns:
            productos_vendidos = self.df[cantidad_col].sum()
        else:
            productos_vendidos = len(self.df)
        
        # Estados para confirmación y cancelación
        estado_col = 'ESTATUS'
        estados_confirmados = ['ENTREGADO', 'EN TRANSITO', 'EN BODEGA TRANSPORTADORA', 
                              'EN BODEGA DESTINO', 'BODEGA DESTINO', 'EN REPARTO', 
                              'EN RUTA', 'EN CAMINO', 'DESPACHADA', 'GUIA_GENERADA']
        estados_cancelados = ['CANCELADO', 'RECHAZADO']
        
        if estado_col in self.df.columns:
            confirmados = self.df[self.df[estado_col].isin(estados_confirmados)]['ID'].nunique()
            cancelados = self.df[self.df[estado_col].isin(estados_cancelados)]['ID'].nunique()
            
            pct_confirmacion = (confirmados / total_pedidos * 100) if total_pedidos > 0 else 0
            pct_cancelacion = (cancelados / total_pedidos * 100) if total_pedidos > 0 else 0
        else:
            pct_confirmacion = 0
            pct_cancelacion = 0
        
        # Totalización (suma de totales de órdenes)
        total_col = 'TOTAL DE LA ORDEN'
        if total_col in self.df.columns:
            totalizacion = self.df[total_col].sum()
        else:
            totalizacion = 0
        
        # Pago anticipado (buscar en columnas relacionadas)
        # Asumimos que está en alguna columna de pago o se calcula de otra forma
        pago_anticipado = 0  # Esto puede necesitar ajuste según la estructura real
        
        metricas = {
            'TOTAL_PEDIDOS': total_pedidos,
            'TOTAL_GUIAS': total_guias,
            'PRODUCTOS_VENDIDOS': productos_vendidos,
            'PCT_CONFIRMACION': round(pct_confirmacion, 1),
            'PCT_CANCELACION': round(pct_cancelacion, 1),
            'TOTALIZACION': round(totalizacion, 2),
            'PAGO_ANTICIPADO': round(pago_anticipado, 2)
        }
        
        self.logger.info(f"      [OK] Metricas generales calculadas")
        return metricas
    
    def calculate_finanzas_generales(self):
        """
        Calcula las finanzas generales (utilidad proyectada, impacto cancelados)
        
        Returns:
            dict: Diccionario con las finanzas generales
        """
        self.logger.info("   Calculando finanzas generales...")
        
        # Estados confirmados (excluyendo cancelados y rechazados)
        estado_col = 'ESTATUS'
        total_col = 'TOTAL DE LA ORDEN'
        ganancia_col = 'GANANCIA'
        
        estados_confirmados = ['ENTREGADO', 'EN TRANSITO', 'EN BODEGA TRANSPORTADORA', 
                              'EN BODEGA DESTINO', 'BODEGA DESTINO', 'EN REPARTO', 
                              'EN RUTA', 'EN CAMINO', 'DESPACHADA', 'GUIA_GENERADA',
                              'PENDIENTE CONFIRMACION', 'PENDIENTE', 'EN PROCESAMIENTO']
        
        if estado_col in self.df.columns and total_col in self.df.columns:
            df_confirmados = self.df[self.df[estado_col].isin(estados_confirmados)]
            
            # Utilidad proyectada a diferentes % de efectividad
            # Asumimos que la ganancia es aproximadamente 30% del total (ajustar según necesidad)
            if ganancia_col in self.df.columns:
                utilidad_base = df_confirmados[ganancia_col].sum()
            else:
                # Estimar ganancia como 30% del total
                utilidad_base = df_confirmados[total_col].sum() * 0.30
            
            utilidad_proyectada = {
                '100%': round(utilidad_base, 2),
                '90%': round(utilidad_base * 0.90, 2),
                '80%': round(utilidad_base * 0.80, 2),
                '70%': round(utilidad_base * 0.70, 2),
                '60%': round(utilidad_base * 0.60, 2),
                '50%': round(utilidad_base * 0.50, 2)
            }
            
            # Impacto cancelados
            estados_cancelados = ['CANCELADO']
            df_cancelados = self.df[self.df[estado_col].isin(estados_cancelados)]
            
            cantidad_cancelados = df_cancelados['ID'].nunique()
            facturacion_perdida = df_cancelados[total_col].sum()
            utilidad_proyectada_30 = facturacion_perdida * 0.30
            
            impacto_cancelados = {
                'CANTIDAD': cantidad_cancelados,
                'FACTURACION_PERDIDA': round(facturacion_perdida, 2),
                'UTILIDAD_PROYECTADA_30': round(utilidad_proyectada_30, 2)
            }
        else:
            utilidad_proyectada = {f'{i}%': 0 for i in [100, 90, 80, 70, 60, 50]}
            impacto_cancelados = {
                'CANTIDAD': 0,
                'FACTURACION_PERDIDA': 0,
                'UTILIDAD_PROYECTADA_30': 0
            }
        
        finanzas = {
            'UTILIDAD_PROYECTADA': utilidad_proyectada,
            'IMPACTO_CANCELADOS': impacto_cancelados
        }
        
        self.logger.info(f"      [OK] Finanzas generales calculadas")
        return finanzas
    
    def calculate_finanzas_reales(self):
        """
        Calcula las finanzas reales (entregados)
        
        Returns:
            dict: Diccionario con las finanzas reales
        """
        self.logger.info("   Calculando finanzas reales (entregados)...")
        
        estado_col = 'ESTATUS'
        total_col = 'TOTAL DE LA ORDEN'
        precio_proveedor_col = 'PRECIO PROVEEDOR X CANTIDAD'
        precio_flete_col = 'PRECIO FLETE'
        costo_devolucion_flete_col = 'COSTO DEVOLUCION FLETE'
        
        # Solo órdenes entregadas
        df_entregados = self.df[self.df[estado_col] == 'ENTREGADO']
        
        if len(df_entregados) > 0:
            ventas_totales = df_entregados[total_col].sum() if total_col in self.df.columns else 0
            
            costo_prov = df_entregados[precio_proveedor_col].sum() if precio_proveedor_col in self.df.columns else 0
            
            fletes_entreg = df_entregados[precio_flete_col].sum() if precio_flete_col in self.df.columns else 0
            
            # Fletes en tránsito (órdenes en tránsito)
            df_transito = self.df[self.df[estado_col].isin(['EN TRANSITO', 'EN BODEGA TRANSPORTADORA', 
                                                             'EN BODEGA DESTINO', 'BODEGA DESTINO', 
                                                             'EN REPARTO', 'EN RUTA', 'EN CAMINO'])]
            fletes_transito = df_transito[precio_flete_col].sum() if precio_flete_col in self.df.columns else 0
            
            # Fletes devolución
            df_devoluciones = self.df[self.df[estado_col] == 'DEVOLUCION']
            fletes_devol = df_devoluciones[costo_devolucion_flete_col].sum() if costo_devolucion_flete_col in self.df.columns else 0
            
            # Pedidos sin recaudo (pago anticipado en entregados)
            pago_anticipado = 0  # Ajustar según estructura real
            
            # Ganancia neta real
            ganancia_neta_real = ventas_totales - costo_prov - fletes_entreg - fletes_transito - fletes_devol + pago_anticipado
            
            # Proyección de tránsito
            total_transito = df_transito[total_col].sum() if total_col in self.df.columns else 0
            proyeccion_transito = {
                '100%': round(total_transito, 2),
                '80%': round(total_transito * 0.80, 2),
                '70%': round(total_transito * 0.70, 2),
                '60%': round(total_transito * 0.60, 2),
                '50%': round(total_transito * 0.50, 2),
                '40%': round(total_transito * 0.40, 2)
            }
        else:
            ventas_totales = 0
            costo_prov = 0
            fletes_entreg = 0
            fletes_transito = 0
            fletes_devol = 0
            pago_anticipado = 0
            ganancia_neta_real = 0
            proyeccion_transito = {f'{i}%': 0 for i in [100, 80, 70, 60, 50, 40]}
        
        finanzas_reales = {
            'VENTAS_TOTALES': round(ventas_totales, 2),
            'COSTO_PROV': round(costo_prov, 2),
            'FLETES_ENTREG': round(fletes_entreg, 2),
            'FLETES_TRANSITO': round(fletes_transito, 2),
            'FLETES_DEVOL': round(fletes_devol, 2),
            'PEDIDOS_SIN_RECAUDO': round(pago_anticipado, 2),
            'GANANCIA_NETA_REAL': round(ganancia_neta_real, 2),
            'PROYECCION_TRANSITO': proyeccion_transito
        }
        
        self.logger.info(f"      [OK] Finanzas reales calculadas")
        return finanzas_reales
    
    def calculate_efectividad_resumen(self):
        """
        Calcula la efectividad y resumen general
        
        Returns:
            dict: Diccionario con efectividad y resumen
        """
        self.logger.info("   Calculando efectividad y resumen...")
        
        estado_col = 'ESTATUS'
        
        # Efectividad entrega (entregados / total enviados)
        total_enviados = self.df[self.df[estado_col].isin(['ENTREGADO', 'EN TRANSITO', 'EN BODEGA TRANSPORTADORA',
                                                           'EN BODEGA DESTINO', 'BODEGA DESTINO', 'EN REPARTO',
                                                           'EN RUTA', 'EN CAMINO', 'DESPACHADA', 'GUIA_GENERADA',
                                                           'DEVOLUCION'])]['ID'].nunique()
        entregados = self.df[self.df[estado_col] == 'ENTREGADO']['ID'].nunique()
        
        efectividad_entrega = (entregados / total_enviados * 100) if total_enviados > 0 else 0
        
        # En tránsito global
        total_pedidos = self.df['ID'].nunique()
        en_transito = self.df[self.df[estado_col].isin(['EN TRANSITO', 'EN BODEGA TRANSPORTADORA',
                                                        'EN BODEGA DESTINO', 'BODEGA DESTINO', 'EN REPARTO',
                                                        'EN RUTA', 'EN CAMINO'])]['ID'].nunique()
        
        pct_transito_global = (en_transito / total_pedidos * 100) if total_pedidos > 0 else 0
        
        # Tasa de devolución
        devoluciones = self.df[self.df[estado_col] == 'DEVOLUCION']['ID'].nunique()
        tasa_devolucion = (devoluciones / total_pedidos * 100) if total_pedidos > 0 else 0
        
        resumen = {
            'EFECTIVIDAD_ENTREGA': round(efectividad_entrega, 1),
            'EN_TRANSITO_GLOBAL': round(pct_transito_global, 1),
            'TASA_DEVOLUCION': round(tasa_devolucion, 1)
        }
        
        self.logger.info(f"      [OK] Efectividad y resumen calculados")
        return resumen
    
    def calculate_conteos_por_estado(self):
        """
        Calcula los conteos por estado con totales y nuevos
        
        Returns:
            pd.DataFrame: DataFrame con conteos por estado
        """
        self.logger.info("   Calculando conteos por estado...")
        
        estado_col = 'ESTATUS'
        total_col = 'TOTAL DE LA ORDEN'
        
        # Mapeo de estados del dashboard
        estados_dashboard = {
            'PEND. CONFIRMACIÓN': 'PENDIENTE CONFIRMACION',
            'PENDIENTE (ENVÍO)': 'PENDIENTE',
            'EN NOVEDAD': 'NOVEDAD',
            'RECLAMAR EN OFICINA': 'RECLAME EN OFICINA',
            'GUÍA GENERADA': 'GUIA_GENERADA',
            'TRÁNSITO TOTAL': ['EN TRANSITO', 'EN BODEGA TRANSPORTADORA', 'EN BODEGA DESTINO', 
                              'BODEGA DESTINO', 'EN REPARTO', 'EN RUTA', 'EN CAMINO'],
            'ENTREGADOS': 'ENTREGADO',
            'DEVOLUCIONES': 'DEVOLUCION',
            'CANCELADOS': 'CANCELADO',
            'RECHAZADOS': 'RECHAZADO'
        }
        
        resultados = []
        
        for estado_nombre, estado_valor in estados_dashboard.items():
            if isinstance(estado_valor, list):
                # Múltiples estados
                df_estado = self.df[self.df[estado_col].isin(estado_valor)]
            else:
                df_estado = self.df[self.df[estado_col] == estado_valor]
            
            cantidad = df_estado['ID'].nunique()
            total = df_estado[total_col].sum() if total_col in self.df.columns else 0
            
            # "New" sería el valor nuevo (por ahora igual al total, ajustar según necesidad)
            nuevo = total  # Esto puede necesitar ajuste según lógica de negocio
            
            resultados.append({
                'ESTADO': estado_nombre,
                'CANTIDAD': cantidad,
                'TOTAL': round(total, 2),
                'NEW': round(nuevo, 2)
            })
        
        df_resultado = pd.DataFrame(resultados)
        
        self.logger.info(f"      [OK] Conteos por estado calculados: {len(df_resultado)} estados")
        return df_resultado
    
    def calculate_efectividad_transportadora(self):
        """
        Calcula la efectividad por transportadora
        
        Returns:
            pd.DataFrame: DataFrame con efectividad por transportadora
        """
        self.logger.info("   Calculando efectividad por transportadora...")
        
        transportadora_col = 'TRANSPORTADORA'
        estado_col = 'ESTATUS'
        
        if transportadora_col not in self.df.columns:
            self.logger.warning("      [WARN] Columna TRANSPORTADORA no encontrada")
            return pd.DataFrame()
        
        transportadoras = self.df[transportadora_col].unique()
        resultados = []
        
        for transportadora in transportadoras:
            if pd.isna(transportadora):
                continue
            
            df_transp = self.df[self.df[transportadora_col] == transportadora]
            
            enviados = df_transp['ID'].nunique()
            transito = df_transp[df_transp[estado_col].isin(['EN TRANSITO', 'EN BODEGA TRANSPORTADORA',
                                                              'EN BODEGA DESTINO', 'BODEGA DESTINO', 
                                                              'EN REPARTO', 'EN RUTA', 'EN CAMINO'])]['ID'].nunique()
            devoluciones = df_transp[df_transp[estado_col] == 'DEVOLUCION']['ID'].nunique()
            cancelados = df_transp[df_transp[estado_col] == 'CANCELADO']['ID'].nunique()
            rechazados = df_transp[df_transp[estado_col] == 'RECHAZADO']['ID'].nunique()
            entregados = df_transp[df_transp[estado_col] == 'ENTREGADO']['ID'].nunique()
            
            pct_efectividad = (entregados / enviados * 100) if enviados > 0 else 0
            pct_transito = (transito / enviados * 100) if enviados > 0 else 0
            pct_devoluciones = (devoluciones / enviados * 100) if enviados > 0 else 0
            
            resultados.append({
                'EMPRESA': transportadora,
                'ENVIADOS': enviados,
                'TRANSITO': transito,
                'PCT_TRANSITO': round(pct_transito, 1),
                'DEVOLUCIONES': devoluciones,
                'PCT_DEVOLUCIONES': round(pct_devoluciones, 1),
                'CANCELADOS': cancelados,
                'RECHAZADOS': rechazados,
                'ENTREGADOS': entregados,
                'PCT_EFECTIVIDAD': round(pct_efectividad, 1)
            })
        
        df_resultado = pd.DataFrame(resultados)
        df_resultado = df_resultado.sort_values('ENVIADOS', ascending=False)
        
        self.logger.info(f"      [OK] Efectividad por transportadora calculada: {len(df_resultado)} transportadoras")
        return df_resultado
    
    def calculate_rentabilidad_producto(self):
        """
        Calcula la rentabilidad por producto
        
        Returns:
            pd.DataFrame: DataFrame con rentabilidad por producto
        """
        self.logger.info("   Calculando rentabilidad por producto...")
        
        producto_col = 'PRODUCTO'
        variacion_col = 'VARIACION'
        cantidad_col = 'CANTIDAD'
        total_col = 'TOTAL DE LA ORDEN'
        ganancia_col = 'GANANCIA'
        estado_col = 'ESTATUS'
        
        if producto_col not in self.df.columns:
            self.logger.warning("      [WARN] Columna PRODUCTO no encontrada")
            return pd.DataFrame()
        
        # Agrupar por producto y variación
        if variacion_col in self.df.columns and self.df[variacion_col].notna().any():
            df_grouped = self.df.groupby([producto_col, variacion_col]).agg({
                'ID': 'nunique',
                cantidad_col: 'sum',
                total_col: 'sum',
                ganancia_col: 'sum' if ganancia_col in self.df.columns else lambda x: 0
            }).reset_index()
            
            df_grouped.columns = ['PRODUCTO', 'VARIACION', 'ENTR', 'CANTIDAD_TOTAL', 'VENTAS', 'UTILIDAD']
        else:
            df_grouped = self.df.groupby(producto_col).agg({
                'ID': 'nunique',
                cantidad_col: 'sum',
                total_col: 'sum',
                ganancia_col: 'sum' if ganancia_col in self.df.columns else lambda x: 0
            }).reset_index()
            
            df_grouped.columns = ['PRODUCTO', 'ENTR', 'CANTIDAD_TOTAL', 'VENTAS', 'UTILIDAD']
            df_grouped['VARIACION'] = ''
        
        # Calcular efectividad, tránsito y devoluciones por producto
        resultados = []
        
        for idx, row in df_grouped.iterrows():
            producto = row['PRODUCTO']
            variacion = row.get('VARIACION', '')
            
            # Filtrar por producto
            if variacion_col in self.df.columns and variacion:
                df_prod = self.df[(self.df[producto_col] == producto) & 
                                  (self.df[variacion_col] == variacion)]
            else:
                df_prod = self.df[self.df[producto_col] == producto]
            
            entr = row['ENTR']
            entregados = df_prod[df_prod[estado_col] == 'ENTREGADO']['ID'].nunique()
            pct_efec = (entregados / entr * 100) if entr > 0 else 0
            
            transito = df_prod[df_prod[estado_col].isin(['EN TRANSITO', 'EN BODEGA TRANSPORTADORA',
                                                          'EN BODEGA DESTINO', 'BODEGA DESTINO', 
                                                          'EN REPARTO', 'EN RUTA', 'EN CAMINO'])]['ID'].nunique()
            pct_tran = (transito / entr * 100) if entr > 0 else 0
            
            devoluciones = df_prod[df_prod[estado_col] == 'DEVOLUCION']['ID'].nunique()
            pct_dev = (devoluciones / entr * 100) if entr > 0 else 0
            
            ventas = row['VENTAS']
            utilidad = row['UTILIDAD'] if ganancia_col in self.df.columns else ventas * 0.30
            
            resultados.append({
                'PRODUCTO': f"{producto} {variacion}" if variacion else producto,
                'ENTR': entr,
                'PCT_EFEC': round(pct_efec, 1),
                'TRAN': transito,
                'PCT_TRAN': round(pct_tran, 1),
                'DEV': devoluciones,
                'PCT_DEV': round(pct_dev, 1),
                'VENTAS': round(ventas, 2),
                'PAUTA': 0,  # Ajustar según necesidad
                'UTILIDAD': round(utilidad, 2)
            })
        
        df_resultado = pd.DataFrame(resultados)
        if not df_resultado.empty and 'VENTAS' in df_resultado.columns:
            df_resultado = df_resultado.sort_values('VENTAS', ascending=False)
        
        self.logger.info(f"      [OK] Rentabilidad por producto calculada: {len(df_resultado)} productos")
        return df_resultado
    
    def save_csvs(self, output_dir=None):
        """
        Guarda todos los CSVs con las métricas calculadas
        
        Args:
            output_dir: Directorio donde guardar los CSVs (default: results/)
        
        Returns:
            dict: Diccionario con las rutas de los archivos generados
        """
        self.logger.info("="*80)
        self.logger.info("GUARDANDO CSVs")
        self.logger.info("="*80)
        
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent.parent / 'results'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archivos_generados = {}
        
        try:
            # 1. Métricas generales
            metricas = self.calculate_metricas_generales()
            df_metricas = pd.DataFrame([metricas])
            filepath = output_dir / f'metricas_generales_{timestamp}.csv'
            df_metricas.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['metricas_generales'] = str(filepath)
            self.logger.info(f"   [OK] Metricas generales: {filepath}")
            
            # 2. Finanzas generales
            finanzas_gen = self.calculate_finanzas_generales()
            # Utilidad proyectada
            df_utilidad = pd.DataFrame([finanzas_gen['UTILIDAD_PROYECTADA']])
            filepath = output_dir / f'utilidad_proyectada_{timestamp}.csv'
            df_utilidad.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['utilidad_proyectada'] = str(filepath)
            self.logger.info(f"   [OK] Utilidad proyectada: {filepath}")
            
            # Impacto cancelados
            df_impacto = pd.DataFrame([finanzas_gen['IMPACTO_CANCELADOS']])
            filepath = output_dir / f'impacto_cancelados_{timestamp}.csv'
            df_impacto.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['impacto_cancelados'] = str(filepath)
            self.logger.info(f"   [OK] Impacto cancelados: {filepath}")
            
            # 3. Finanzas reales
            finanzas_reales = self.calculate_finanzas_reales()
            df_finanzas = pd.DataFrame([finanzas_reales])
            filepath = output_dir / f'finanzas_reales_{timestamp}.csv'
            df_finanzas.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['finanzas_reales'] = str(filepath)
            self.logger.info(f"   [OK] Finanzas reales: {filepath}")
            
            # 4. Efectividad y resumen
            efectividad = self.calculate_efectividad_resumen()
            df_efectividad = pd.DataFrame([efectividad])
            filepath = output_dir / f'efectividad_resumen_{timestamp}.csv'
            df_efectividad.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['efectividad_resumen'] = str(filepath)
            self.logger.info(f"   [OK] Efectividad y resumen: {filepath}")
            
            # 5. Conteos por estado
            df_estados = self.calculate_conteos_por_estado()
            filepath = output_dir / f'conteos_por_estado_{timestamp}.csv'
            df_estados.to_csv(filepath, index=False, encoding='utf-8-sig')
            archivos_generados['conteos_por_estado'] = str(filepath)
            self.logger.info(f"   [OK] Conteos por estado: {filepath}")
            
            # 6. Efectividad por transportadora
            df_transportadoras = self.calculate_efectividad_transportadora()
            if not df_transportadoras.empty:
                filepath = output_dir / f'efectividad_transportadora_{timestamp}.csv'
                df_transportadoras.to_csv(filepath, index=False, encoding='utf-8-sig')
                archivos_generados['efectividad_transportadora'] = str(filepath)
                self.logger.info(f"   [OK] Efectividad por transportadora: {filepath}")
            
            # 7. Rentabilidad por producto
            df_productos = self.calculate_rentabilidad_producto()
            if not df_productos.empty:
                filepath = output_dir / f'rentabilidad_producto_{timestamp}.csv'
                df_productos.to_csv(filepath, index=False, encoding='utf-8-sig')
                archivos_generados['rentabilidad_producto'] = str(filepath)
                self.logger.info(f"   [OK] Rentabilidad por producto: {filepath}")
            
            self.logger.info("="*80)
            self.logger.info(f"[OK] {len(archivos_generados)} CSVs generados exitosamente")
            self.logger.info("="*80)
            
            return archivos_generados
            
        except Exception as e:
            self.logger.error(f"   [ERROR] Error al guardar CSVs: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def analyze_report(self, reporte_path, output_dir=None):
        """
        Analiza un reporte completo y genera todos los CSVs
        
        Args:
            reporte_path: Ruta al archivo Excel del reporte actual
            output_dir: Directorio donde guardar los CSVs
        
        Returns:
            dict: Diccionario con las rutas de los archivos generados
        """
        self.logger.info("="*80)
        self.logger.info("INICIANDO ANALISIS DE REPORTE")
        self.logger.info("="*80)
        
        # Cargar reporte
        if not self.load_report(reporte_path):
            return {}
        
        # Generar CSVs
        archivos = self.save_csvs(output_dir)
        
        return archivos


class Command(BaseCommand):
    """Comando de Django para analizar reportes de Dropi"""
    
    help = 'Analiza un reporte actual de Dropi y genera CSVs con todas las metricas del dashboard'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reporte',
            type=str,
            required=True,
            help='Ruta al archivo Excel del reporte actual'
        )
        
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Directorio donde guardar los CSVs (default: results/)'
        )
    
    def handle(self, *args, **options):
        reporte_path = options['reporte']
        output_dir = options.get('output_dir')
        
        # Crear y ejecutar el analizador
        analyzer = ReportAnalyzer()
        
        try:
            archivos = analyzer.analyze_report(reporte_path, output_dir)
            
            if archivos:
                self.stdout.write(
                    self.style.SUCCESS('[OK] Analisis completado exitosamente')
                )
                self.stdout.write(f'  CSVs generados: {len(archivos)}')
                for nombre, ruta in archivos.items():
                    self.stdout.write(f'    - {nombre}: {ruta}')
            else:
                self.stdout.write(
                    self.style.ERROR('[ERROR] Error al analizar el reporte')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al analizar reporte: {str(e)}')
            )
            raise

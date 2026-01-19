"""
Comparador de Reportes para Dropi
Este comando lee dos reportes de órdenes (base y actual), los compara para encontrar
órdenes sin movimiento, y genera un CSV con las órdenes sin movimiento en el mismo 
formato que el archivo de trazabilidad.

Lógica mejorada:
1. INNER JOIN por ID entre ambos reportes
2. Filtra por estados de interés en ambos reportes
3. Verifica que el ESTATUS sea igual (sin movimiento)
4. Genera CSV con columnas especificadas
5. Genera resumen estadístico

El CSV generado tiene las siguientes columnas (en orden):
1. ID Orden
2. Guía
3. Tipo Envío
4. Estado Actual
5. Estado Anterior
6. Transportadora
7. Cliente
8. Teléfono
9. Ciudad
10. Departamento
11. Producto
12. Cantidad
13. Total
14. Fecha
"""

import os
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand


class ReportComparator:
    """
    Comparador de reportes de Dropi
    
    Funcionalidad:
    1. Lee dos reportes Excel (base y actual)
    2. Compara ambos reportes para encontrar órdenes sin movimiento
    3. Genera un CSV con las órdenes sin movimiento
    """
    
    # Estados de interés para el filtrado
    ESTADOS_INTERES = [
        'BODEGA DESTINO',
        'DESPACHADA',
        'EN BODEGA ORIGEN',
        'EN BODEGA TRANSPORTADORA',
        'EN CAMINO',
        'EN DESPACHO',
        'EN PROCESAMIENTO',
        'EN PROCESO DE DEVOLUCION',
        'EN REPARTO',
        'EN RUTA',
        'EN TRANSITO',
        'ENTREGADA A CONEXIONES',
        'ENTREGADO A TRANSPORTADORA',
        'NOVEDAD SOLUCIONADA',
        'RECOGIDO POR DROPI',
        'TELEMERCADEO'
    ]
    
    def __init__(self):
        """Inicializa el comparador"""
        self.logger = self._setup_logger()
        self.stats = {
            'ordenes_base': 0,
            'ordenes_actual': 0,
            'ordenes_en_ambos': 0,
            'ordenes_con_estados_interes': 0,
            'ordenes_sin_movimiento': 0,
            'estado_mas_repetido': None,
            'conteo_estado_mas_repetido': 0
        }
    
    def _setup_logger(self):
        """Configura el logger para el comparador"""
        logger = logging.getLogger('ReportComparator')
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
            log_dir / f'reportcomparer_{timestamp}.log',
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
    
    def _safe_get(self, row, col, default=''):
        """Obtiene un valor de forma segura, manejando NaN"""
        if col is None or col not in row.index:
            return default
        value = row.get(col, default)
        if pd.isna(value):
            return default
        return str(value).strip() if value else default
    
    def _safe_num(self, row, col, default=0):
        """Obtiene un valor numérico de forma segura"""
        if col is None or col not in row.index:
            return default
        value = row.get(col, default)
        if pd.isna(value):
            return default
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).replace(',', '').strip()) if str(value).strip() else default
        except:
            return default
    
    def _safe_date(self, row, col, default=''):
        """Obtiene una fecha de forma segura"""
        if col is None or col not in row.index:
            return default
        value = row.get(col, default)
        if pd.isna(value):
            return default
        try:
            if isinstance(value, (pd.Timestamp, datetime)):
                return value.strftime('%d/%m/%Y')
            elif isinstance(value, str):
                # Intentar parsear
                date_obj = pd.to_datetime(value, dayfirst=True, errors='coerce')
                if pd.notna(date_obj):
                    return date_obj.strftime('%d/%m/%Y')
                return value
            return str(value)
        except:
            return str(value) if value else default
    
    def compare_reports(self, reporte_base_path, reporte_actual_path):
        """
        Compara los dos reportes para encontrar órdenes sin movimiento
        
        Lógica mejorada:
        - INNER JOIN por ID entre ambos reportes
        - Filtra por estados de interés en ambos reportes
        - Verifica que el ESTATUS sea igual (sin movimiento)
        
        Args:
            reporte_base_path: Ruta al reporte base (hace 2 días)
            reporte_actual_path: Ruta al reporte actual (hoy)
        
        Returns:
            pd.DataFrame: DataFrame con las órdenes sin movimiento
        """
        self.logger.info("="*80)
        self.logger.info("PASO 1: COMPARANDO REPORTES")
        self.logger.info("="*80)
        
        try:
            # 1. Leer reportes
            self.logger.info("   1) Leyendo reporte BASE...")
            df_base = pd.read_excel(reporte_base_path)
            df_base.columns = df_base.columns.str.strip()
            self.stats['ordenes_base'] = len(df_base)
            self.logger.info(f"      [OK] Reporte base cargado: {len(df_base)} filas")
            
            self.logger.info("   2) Leyendo reporte ACTUAL...")
            df_actual = pd.read_excel(reporte_actual_path)
            df_actual.columns = df_actual.columns.str.strip()
            self.stats['ordenes_actual'] = len(df_actual)
            self.logger.info(f"      [OK] Reporte actual cargado: {len(df_actual)} filas")
            
            # 2. Verificar columnas requeridas
            self.logger.info("   3) Verificando columnas requeridas...")
            id_col = 'ID'
            estado_col = 'ESTATUS'
            
            if id_col not in df_base.columns:
                raise ValueError(f"Columna '{id_col}' no encontrada en reporte BASE")
            if id_col not in df_actual.columns:
                raise ValueError(f"Columna '{id_col}' no encontrada en reporte ACTUAL")
            if estado_col not in df_base.columns:
                raise ValueError(f"Columna '{estado_col}' no encontrada en reporte BASE")
            if estado_col not in df_actual.columns:
                raise ValueError(f"Columna '{estado_col}' no encontrada en reporte ACTUAL")
            
            self.logger.info("      [OK] Columnas requeridas verificadas")
            
            # 3. Normalizar IDs y estados
            self.logger.info("   4) Normalizando IDs y estados...")
            df_base['ID_NORM'] = df_base[id_col].astype(str).str.strip()
            df_base['ESTATUS_NORM'] = df_base[estado_col].astype(str).str.strip()
            
            df_actual['ID_NORM'] = df_actual[id_col].astype(str).str.strip()
            df_actual['ESTATUS_NORM'] = df_actual[estado_col].astype(str).str.strip()
            
            # 4. Filtrar por estados de interés en ambos reportes
            self.logger.info("   5) Filtrando por estados de interés...")
            df_base_filtrado = df_base[
                df_base['ESTATUS_NORM'].isin(self.ESTADOS_INTERES)
            ].copy()
            
            df_actual_filtrado = df_actual[
                df_actual['ESTATUS_NORM'].isin(self.ESTADOS_INTERES)
            ].copy()
            
            self.logger.info(f"      - Órdenes BASE con estados de interés: {len(df_base_filtrado)}")
            self.logger.info(f"      - Órdenes ACTUAL con estados de interés: {len(df_actual_filtrado)}")
            
            # 4.5. Eliminar duplicados por ID (mantener solo la primera ocurrencia)
            self.logger.info("   5.5) Eliminando duplicados por ID...")
            duplicados_base_antes = len(df_base_filtrado)
            df_base_filtrado = df_base_filtrado.drop_duplicates(subset=['ID_NORM'], keep='first')
            duplicados_base_eliminados = duplicados_base_antes - len(df_base_filtrado)
            
            duplicados_actual_antes = len(df_actual_filtrado)
            df_actual_filtrado = df_actual_filtrado.drop_duplicates(subset=['ID_NORM'], keep='first')
            duplicados_actual_eliminados = duplicados_actual_antes - len(df_actual_filtrado)
            
            if duplicados_base_eliminados > 0:
                self.logger.info(f"      - Duplicados eliminados en BASE: {duplicados_base_eliminados}")
            if duplicados_actual_eliminados > 0:
                self.logger.info(f"      - Duplicados eliminados en ACTUAL: {duplicados_actual_eliminados}")
            self.logger.info(f"      - Órdenes BASE únicas: {len(df_base_filtrado)}")
            self.logger.info(f"      - Órdenes ACTUAL únicas: {len(df_actual_filtrado)}")
            
            # 5. Realizar INNER JOIN por ID
            self.logger.info("   6) Realizando INNER JOIN por ID...")
            df_merged = pd.merge(
                df_base_filtrado,
                df_actual_filtrado,
                on='ID_NORM',
                how='inner',
                suffixes=('_BASE', '_ACTUAL')
            )
            
            self.stats['ordenes_en_ambos'] = len(df_merged)
            self.logger.info(f"      [OK] Órdenes encontradas en ambos reportes: {len(df_merged)}")
            
            # 6. Filtrar órdenes sin movimiento (ESTATUS igual)
            self.logger.info("   7) Filtrando órdenes sin movimiento (ESTATUS igual)...")
            df_sin_movimiento = df_merged[
                df_merged['ESTATUS_NORM_BASE'] == df_merged['ESTATUS_NORM_ACTUAL']
            ].copy()
            
            self.stats['ordenes_sin_movimiento'] = len(df_sin_movimiento)
            self.logger.info(f"      [OK] Órdenes sin movimiento: {len(df_sin_movimiento)}")
            
            if len(df_sin_movimiento) == 0:
                self.logger.info("      [INFO] No se encontraron órdenes sin movimiento")
                return pd.DataFrame()
            
            # 7. Construir DataFrame resultado con columnas especificadas
            self.logger.info("   8) Construyendo DataFrame resultado...")
            ordenes_resultado = []
            
            # Función auxiliar para buscar columnas con posibles variaciones
            def find_column(df, possible_names):
                """Busca una columna entre varios nombres posibles"""
                for name in possible_names:
                    if name in df.columns:
                        return name
                return None
            
            for idx, row in df_sin_movimiento.iterrows():
                # Buscar cada columna con sus posibles variaciones
                col_guia = find_column(df_sin_movimiento, ['NÚMERO GUIA_ACTUAL', 'NÚMERO GUIA', 'GUIA_ACTUAL', 'GUIA'])
                col_tipo_envio = find_column(df_sin_movimiento, ['TIPO DE ENVIO_ACTUAL', 'TIPO DE ENVIO', 'TIPO ENVIO_ACTUAL', 'TIPO ENVIO'])
                col_transportadora = find_column(df_sin_movimiento, ['TRANSPORTADORA_ACTUAL', 'TRANSPORTADORA'])
                col_cliente = find_column(df_sin_movimiento, ['NOMBRE CLIENTE_ACTUAL', 'NOMBRE CLIENTE', 'CLIENTE_ACTUAL', 'CLIENTE'])
                col_telefono = find_column(df_sin_movimiento, ['TELÉFONO_ACTUAL', 'TELÉFONO', 'TELEFONO_ACTUAL', 'TELEFONO'])
                col_ciudad = find_column(df_sin_movimiento, ['CIUDAD DESTINO_ACTUAL', 'CIUDAD DESTINO', 'CIUDAD_ACTUAL', 'CIUDAD'])
                col_departamento = find_column(df_sin_movimiento, ['DEPARTAMENTO DESTINO_ACTUAL', 'DEPARTAMENTO DESTINO', 'DEPARTAMENTO_ACTUAL', 'DEPARTAMENTO'])
                col_producto = find_column(df_sin_movimiento, ['PRODUCTO_ACTUAL', 'PRODUCTO'])
                col_cantidad = find_column(df_sin_movimiento, ['CANTIDAD_ACTUAL', 'CANTIDAD'])
                col_total = find_column(df_sin_movimiento, ['TOTAL DE LA ORDEN_ACTUAL', 'TOTAL DE LA ORDEN', 'TOTAL_ACTUAL', 'TOTAL'])
                col_fecha = find_column(df_sin_movimiento, ['FECHA_ACTUAL', 'FECHA'])
                
                orden_data = {
                    'ID Orden': int(row['ID_NORM']) if row['ID_NORM'].isdigit() else row['ID_NORM'],
                    'Guía': self._safe_get(row, col_guia),
                    'Tipo Envío': self._safe_get(row, col_tipo_envio),
                    'Estado Actual': self._safe_get(row, 'ESTATUS_NORM_ACTUAL'),
                    'Estado Anterior': self._safe_get(row, 'ESTATUS_NORM_BASE'),
                    'Transportadora': self._safe_get(row, col_transportadora),
                    'Cliente': self._safe_get(row, col_cliente),
                    'Teléfono': self._safe_get(row, col_telefono),
                    'Ciudad': self._safe_get(row, col_ciudad),
                    'Departamento': self._safe_get(row, col_departamento),
                    'Producto': self._safe_get(row, col_producto),
                    'Cantidad': int(self._safe_num(row, col_cantidad, 0)),
                    'Total': self._safe_num(row, col_total, 0.0),
                    'Fecha': self._safe_date(row, col_fecha)
                }
                ordenes_resultado.append(orden_data)
            
            # Definir el orden exacto de las columnas como en trazabilidad
            columnas_orden = [
                'ID Orden',
                'Guía',
                'Tipo Envío',
                'Estado Actual',
                'Estado Anterior',
                'Transportadora',
                'Cliente',
                'Teléfono',
                'Ciudad',
                'Departamento',
                'Producto',
                'Cantidad',
                'Total',
                'Fecha'
            ]
            
            df_resultado = pd.DataFrame(ordenes_resultado)
            
            # Verificar que todas las columnas existan
            columnas_faltantes = [col for col in columnas_orden if col not in df_resultado.columns]
            if columnas_faltantes:
                self.logger.warning(f"      [WARNING] Columnas faltantes: {columnas_faltantes}")
            else:
                self.logger.info(f"      [OK] Todas las columnas requeridas están presentes")
            
            # Reordenar columnas
            df_resultado = df_resultado[columnas_orden]
            
            # 7.5. Eliminar duplicados finales por ID Orden (por si acaso)
            duplicados_antes = len(df_resultado)
            df_resultado = df_resultado.drop_duplicates(subset=['ID Orden'], keep='first')
            duplicados_eliminados = duplicados_antes - len(df_resultado)
            if duplicados_eliminados > 0:
                self.logger.info(f"      [INFO] Duplicados finales eliminados: {duplicados_eliminados}")
                self.logger.info(f"      - Órdenes únicas en resultado: {len(df_resultado)}")
            
            # 8. Calcular estadísticas
            self.logger.info("   9) Calculando estadísticas...")
            if len(df_resultado) > 0:
                estado_counts = df_resultado['Estado Actual'].value_counts()
                if len(estado_counts) > 0:
                    self.stats['estado_mas_repetido'] = estado_counts.index[0]
                    self.stats['conteo_estado_mas_repetido'] = int(estado_counts.iloc[0])
            
            self.logger.info("      [OK] DataFrame resultado creado")
            
            # Mostrar resumen detallado
            self.logger.info("")
            self.logger.info("      [OK] Comparación completada")
            self.logger.info("      " + "-"*70)
            self.logger.info(f"      RESUMEN DE COMPARACIÓN:")
            self.logger.info(f"      - Total órdenes en reporte BASE: {self.stats['ordenes_base']:,}")
            self.logger.info(f"      - Total órdenes en reporte ACTUAL: {self.stats['ordenes_actual']:,}")
            self.logger.info(f"      - Órdenes encontradas en ambos reportes: {self.stats['ordenes_en_ambos']:,}")
            self.logger.info(f"      - Órdenes sin movimiento detectadas: {self.stats['ordenes_sin_movimiento']:,}")
            if self.stats['estado_mas_repetido']:
                self.logger.info(f"      - Estado más repetido: {self.stats['estado_mas_repetido']} ({self.stats['conteo_estado_mas_repetido']:,} órdenes)")
            self.logger.info("      " + "-"*70)
            
            # Mostrar muestra de datos
            if len(df_resultado) > 0:
                self.logger.info(f"      Muestra de datos (primeras 3 filas):")
                for idx, row in df_resultado.head(3).iterrows():
                    self.logger.info(f"         - ID: {row['ID Orden']}, Estado: {row['Estado Actual']}, Fecha: {row['Fecha']}")
            
            self.logger.info("="*80)
            
            return df_resultado
            
        except Exception as e:
            self.logger.error(f"   [ERROR] Error al comparar reportes: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def save_result_csv(self, df_resultado):
        """
        Guarda el DataFrame resultado en un archivo CSV
        
        PASO 2: Guardar CSV resultante
        
        El CSV generado tiene el mismo formato que el archivo de trazabilidad:
        - Mismas columnas en el mismo orden
        - Formato compatible con Excel para visualización
        
        Args:
            df_resultado: DataFrame con las órdenes sin movimiento
        
        Returns:
            str: Ruta del archivo guardado
        """
        self.logger.info("="*80)
        self.logger.info("PASO 2: GUARDANDO CSV RESULTANTE")
        self.logger.info("="*80)
        
        try:
            if df_resultado.empty:
                self.logger.warning("   [WARNING] No hay datos para guardar")
                return None
            
            # Crear directorio de resultados si no existe
            self.logger.info("   1) Verificando directorio de resultados...")
            base_dir = Path(__file__).parent.parent.parent.parent
            results_dir = base_dir / 'results' / 'ordenes_sin_movimiento'
            results_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"      [OK] Directorio: {results_dir}")
            
            # Nombre del archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'ordenes_sin_movimiento_{timestamp}.csv'
            filepath = results_dir / filename
            
            # Verificar información del DataFrame antes de guardar
            self.logger.info("   2) Verificando DataFrame antes de guardar...")
            self.logger.info(f"      - Filas: {len(df_resultado)}")
            self.logger.info(f"      - Columnas: {len(df_resultado.columns)}")
            self.logger.info(f"      - Columnas: {list(df_resultado.columns)}")
            
            # Guardar CSV con encoding UTF-8 con BOM para compatibilidad con Excel
            self.logger.info("   3) Guardando archivo CSV...")
            self.logger.info(f"      Ruta completa: {filepath}")
            df_resultado.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            # Verificar que el archivo se creó correctamente
            if filepath.exists():
                file_size = filepath.stat().st_size
                self.logger.info(f"      [OK] Archivo guardado exitosamente")
                self.logger.info(f"      - Tamaño: {file_size:,} bytes ({file_size/1024:.2f} KB)")
                self.logger.info(f"      - Total de ordenes: {len(df_resultado)}")
            else:
                self.logger.error(f"      [ERROR] El archivo no se creó correctamente")
            
            self.logger.info("="*80)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"   [ERROR] Error al guardar CSV: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def generar_resumen(self):
        """
        Genera un resumen estadístico del proceso
        
        Returns:
            str: Resumen en formato texto
        """
        resumen = []
        resumen.append("="*80)
        resumen.append("RESUMEN ESTADÍSTICO")
        resumen.append("="*80)
        resumen.append(f"Órdenes en reporte BASE: {self.stats['ordenes_base']:,}")
        resumen.append(f"Órdenes en reporte ACTUAL: {self.stats['ordenes_actual']:,}")
        resumen.append(f"Órdenes encontradas en ambos reportes: {self.stats['ordenes_en_ambos']:,}")
        resumen.append(f"Órdenes sin movimiento detectadas: {self.stats['ordenes_sin_movimiento']:,}")
        
        if self.stats['estado_mas_repetido']:
            resumen.append("")
            resumen.append(f"Estado más repetido: {self.stats['estado_mas_repetido']}")
            resumen.append(f"  Cantidad: {self.stats['conteo_estado_mas_repetido']:,} órdenes")
        
        resumen.append("="*80)
        
        return "\n".join(resumen)
    
    def _move_to_processed(self, reporte_base_path, reporte_actual_path):
        """
        Mueve los archivos procesados a una subcarpeta 'procesados'
        
        Args:
            reporte_base_path: Ruta al reporte base
            reporte_actual_path: Ruta al reporte actual
        """
        try:
            # Crear carpeta 'procesados' si no existe
            base_dir = Path(__file__).parent.parent.parent.parent
            downloads_dir = base_dir / 'results' / 'downloads'
            procesados_dir = downloads_dir / 'procesados'
            procesados_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("MOVIENDO ARCHIVOS PROCESADOS")
            self.logger.info("="*80)
            
            # Mover reporte base
            base_path = Path(reporte_base_path)
            if base_path.exists():
                destino_base = procesados_dir / base_path.name
                base_path.rename(destino_base)
                self.logger.info(f"   ✅ Movido: {base_path.name}")
                self.logger.info(f"      → {procesados_dir}")
            
            # Mover reporte actual
            actual_path = Path(reporte_actual_path)
            if actual_path.exists():
                destino_actual = procesados_dir / actual_path.name
                actual_path.rename(destino_actual)
                self.logger.info(f"   ✅ Movido: {actual_path.name}")
                self.logger.info(f"      → {procesados_dir}")
            
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ No se pudieron mover los archivos: {str(e)}")
    
    def run(self, reporte_base_path, reporte_actual_path):
        """
        Ejecuta el proceso completo de comparación
        
        Args:
            reporte_base_path: Ruta al reporte base
            reporte_actual_path: Ruta al reporte actual
        
        Returns:
            str: Ruta del CSV resultante o None si falló
        """
        self.logger.info("="*80)
        self.logger.info("INICIANDO COMPARADOR DE REPORTES")
        self.logger.info("="*80)
        self.logger.info(f"   Reporte BASE: {reporte_base_path}")
        self.logger.info(f"   Reporte ACTUAL: {reporte_actual_path}")
        self.logger.info("="*80)
        
        # Verificar que los archivos existan
        self.logger.info("VERIFICANDO ARCHIVOS DE ENTRADA...")
        if not os.path.exists(reporte_base_path):
            self.logger.error(f"[ERROR] El archivo del reporte base no existe: {reporte_base_path}")
            return None
        else:
            file_size_base = os.path.getsize(reporte_base_path)
            self.logger.info(f"   [OK] Reporte BASE encontrado: {file_size_base:,} bytes")
        
        if not os.path.exists(reporte_actual_path):
            self.logger.error(f"[ERROR] El archivo del reporte actual no existe: {reporte_actual_path}")
            return None
        else:
            file_size_actual = os.path.getsize(reporte_actual_path)
            self.logger.info(f"   [OK] Reporte ACTUAL encontrado: {file_size_actual:,} bytes")
        
        self.logger.info("")
        
        # Comparar reportes
        df_resultado = self.compare_reports(reporte_base_path, reporte_actual_path)
        
        # Guardar CSV resultante
        if not df_resultado.empty:
            csv_path = self.save_result_csv(df_resultado)
            
            if csv_path:
                # Mover archivos procesados a subcarpeta
                self._move_to_processed(reporte_base_path, reporte_actual_path)
                
                self.logger.info("")
                self.logger.info("="*80)
                self.logger.info("[OK] PROCESO COMPLETADO EXITOSAMENTE")
                self.logger.info("="*80)
                self.logger.info(f"   Ordenes sin movimiento encontradas: {len(df_resultado)}")
                self.logger.info(f"   CSV resultante: {csv_path}")
                self.logger.info("")
                self.logger.info("   El CSV generado tiene el mismo formato que el archivo de trazabilidad")
                self.logger.info("="*80)
                
                # Generar y mostrar resumen
                resumen = self.generar_resumen()
                self.logger.info("")
                self.logger.info(resumen)
                
                return csv_path
            else:
                self.logger.error("[ERROR] No se pudo guardar el CSV resultante")
                return None
        else:
            # Mover archivos procesados incluso si no hay órdenes sin movimiento
            self._move_to_processed(reporte_base_path, reporte_actual_path)
            
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("[INFO] PROCESO COMPLETADO - NO HAY ORDENES SIN MOVIMIENTO")
            self.logger.info("="*80)
            self.logger.info("   No se encontraron ordenes sin movimiento")
            self.logger.info("="*80)
            
            # Generar y mostrar resumen
            resumen = self.generar_resumen()
            self.logger.info("")
            self.logger.info(resumen)
            
            return None


class Command(BaseCommand):
    """Comando de Django para comparar reportes de Dropi"""
    
    help = 'Compara dos reportes de Dropi para encontrar ordenes sin movimiento'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--base',
            type=str,
            required=False,
            help='Ruta al archivo Excel del reporte BASE (hace 2 días). Si no se proporciona, busca el más reciente en results/downloads/'
        )
        
        parser.add_argument(
            '--actual',
            type=str,
            required=False,
            help='Ruta al archivo Excel del reporte ACTUAL (hoy). Si no se proporciona, busca el más reciente en results/downloads/'
        )
    
    def _find_latest_file(self, directory, pattern):
        """Busca el archivo más reciente que coincida con el patrón"""
        dir_path = Path(directory)
        if not dir_path.exists():
            return None
        
        files = list(dir_path.glob(pattern))
        if not files:
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return str(files[0])
    
    def handle(self, *args, **options):
        reporte_base_path = options.get('base')
        reporte_actual_path = options.get('actual')
        
        # Si no se proporcionaron rutas, buscar automáticamente en results/downloads/
        base_dir = Path(__file__).parent.parent.parent.parent
        downloads_dir = base_dir / 'results' / 'downloads'
        
        if not reporte_base_path:
            self.stdout.write("   Buscando reporte BASE más reciente...")
            reporte_base_path = self._find_latest_file(downloads_dir, 'reporte_base_*.xlsx')
            if reporte_base_path:
                self.stdout.write(f"   [OK] Encontrado: {reporte_base_path}")
            else:
                self.stdout.write(
                    self.style.ERROR('[ERROR] No se encontró reporte BASE en results/downloads/')
                )
                return
        
        if not reporte_actual_path:
            self.stdout.write("   Buscando reporte ACTUAL más reciente...")
            reporte_actual_path = self._find_latest_file(downloads_dir, 'reporte_actual_*.xlsx')
            if reporte_actual_path:
                self.stdout.write(f"   [OK] Encontrado: {reporte_actual_path}")
            else:
                self.stdout.write(
                    self.style.ERROR('[ERROR] No se encontró reporte ACTUAL en results/downloads/')
                )
                return
        
        # Crear y ejecutar el comparador
        comparator = ReportComparator()
        
        try:
            csv_path = comparator.run(reporte_base_path, reporte_actual_path)
            if csv_path:
                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS('[OK] Comparacion completada exitosamente')
                )
                self.stdout.write(f'  CSV generado: {csv_path}')
                self.stdout.write("")
                self.stdout.write(comparator.generar_resumen())
            else:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING('[INFO] Comparacion completada - No hay ordenes sin movimiento')
                )
                self.stdout.write("")
                self.stdout.write(comparator.generar_resumen())
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al comparar reportes: {str(e)}')
            )
            raise

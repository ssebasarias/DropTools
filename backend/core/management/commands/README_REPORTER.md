# 🤖 Bot de Reportes Automáticos para Dropi

## 📋 Descripción

Este bot automatiza completamente el proceso de generación de observaciones en Dropi para productos sin movimiento. Lee un archivo Excel con datos de trazabilidad y crea reportes automáticamente en la plataforma Dropi.

## ✨ Características

- ✅ **Login automático** en Dropi
- ✅ **Navegación robusta** con múltiples estrategias de fallback:
  - Intento 1: Navegación tradicional por menú
  - Intento 2: Navegación directa por URL (fallback)
  - Intento 3: Navegación directa con espera extendida
- ✅ **Búsqueda de órdenes** por número de teléfono
- ✅ **Validación de estados** antes de procesar
- ✅ **Creación automática** de casos de consulta
- ✅ **Manejo de errores** robusto con reintentos automáticos
- ✅ **Logging completo** de todas las operaciones
- ✅ **Screenshots de debugging** en cada paso crítico
- ✅ **Estadísticas detalladas** al finalizar
- ✅ **Exportación de resultados** en CSV
- ✅ **Modo headless** para ejecución en servidor

## 🚀 Uso

> **💻 Nota importante**: Este bot está diseñado para ejecutarse **localmente en tu PC**, NO en Docker. Usa los recursos de tu computadora y por defecto **muestra el navegador Chrome** para que puedas ver exactamente qué está haciendo.

### Comando básico (navegador visible - RECOMENDADO)

```bash
python manage.py reporter --excel "ruta/al/archivo.xlsx"
```

**Esto abrirá Chrome en tu PC y podrás ver todo el proceso en tiempo real** 👀

### Con modo headless (sin ver el navegador)

```bash
python manage.py reporter --excel "ruta/al/archivo.xlsx" --headless
```

Solo usa `--headless` si quieres que el bot trabaje en segundo plano sin mostrar el navegador.

### Ejemplo real

```bash
python manage.py reporter --excel "C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-16.xlsx"
```

**Verás una ventana de Chrome abrirse automáticamente** y podrás observar cómo el bot:
- Inicia sesión en Dropi
- Navega a Mis Pedidos
- Busca cada orden
- Crea los reportes


## 📊 Formato del Excel

El archivo Excel debe contener las siguientes columnas:

- **Teléfono**: Número de teléfono del cliente
- **Estado Actual**: Estado actual de la orden

### Estados válidos procesados

El bot solo procesará órdenes con los siguientes estados:

- BODEGA DESTNO
- DESPACHADA
- EN BODEGA ORIGEN
- EN BODEGA TRANSPORTADORA
- EN DESPACHO
- EN CAMINO
- EN PROCESAMIENTO
- EN PROCESO DE DEVOLUCION
- EN REPARTO
- EN RUTA
- ENTREGADO A CONEXIONES
- ENTREGADO A TRANSPORTADORA
- INTENTO DE ENTREGA
- NOVEDAD SOLUCIONADA
- ENTREGA POR DROPI
- TELEMERCADEO

## 🔧 Configuración

### Credenciales

Las credenciales están configuradas en el código:

```python
DROPI_EMAIL = "dahellonline@gmail.com"
DROPI_PASSWORD = "Bigotes2001@"
```

> ⚠️ **Importante**: Para producción, considera mover las credenciales a variables de entorno.

### Mensaje de observación

El mensaje enviado a la transportadora es:

```
Pedido sin movimiento por mucho tiempo, favor salir a reparto urgente.
```

Puedes modificarlo en la constante `OBSERVATION_TEXT` del código.

## 📝 Proceso automatizado

Para cada orden, el bot realiza los siguientes pasos:

1. **Navega** a la sección "Mis Pedidos"
2. **Busca** la orden por número de teléfono
3. **Valida** que el estado coincida con el esperado
4. **Hace click** en "Nueva consulta"
5. **Selecciona** tipo de consulta: "Transportadora"
6. **Selecciona** motivo: "Ordenes sin movimiento"
7. **Hace click** en "Siguiente"
8. **Ingresa** el texto de observación
9. **Inicia** la conversación
10. **Maneja** el caso si la orden ya tiene un caso abierto

## 🛡️ Estrategia de navegación robusta

El bot implementa una estrategia de navegación multi-nivel inspirada en el worker scraper, con fallbacks automáticos para garantizar máxima confiabilidad:

### Nivel 1: Navegación tradicional por menú
```
1. Buscar menú "Mis Pedidos"
2. Click en el menú principal
3. Buscar submenú "Mis Pedidos"
4. Click en el submenú
5. Validar URL correcta
6. Esperar carga de tabla
```

**Ventaja**: Simula comportamiento humano natural  
**Desventaja**: Puede fallar si hay problemas de carga del menú

### Nivel 2: Navegación directa por URL (Fallback)
```
1. Esperar 10 segundos (ventana de carga)
2. Navegar directamente a: https://app.dropi.co/dashboard/orders
3. Validar URL
4. Esperar 15 segundos para carga de elementos
```

**Ventaja**: Más confiable, evita problemas de menú  
**Desventaja**: Menos "humano"

### Nivel 3: Navegación directa con espera extendida (Último recurso)
```
1. Esperar 15 segundos (ventana de carga extendida)
2. Navegar directamente a: https://app.dropi.co/dashboard/orders
3. Validar URL
4. Esperar 20 segundos para carga de elementos
```

**Ventaja**: Máxima confiabilidad en conexiones lentas  
**Desventaja**: Más lento

### Screenshots de debugging

En cada intento, el bot guarda screenshots automáticos:

- `orders_page_success.png` - Navegación exitosa (método tradicional)
- `orders_menu_error.png` - Error en navegación por menú
- `orders_page_direct_1.png` - Navegación directa (intento 2)
- `orders_page_direct_2.png` - Navegación directa (intento 3)
- `orders_error_final_X.png` - Error final después de todos los intentos

Estos screenshots se guardan en: `backend/logs/`


## 📊 Resultados

### Logs

Los logs se guardan en: `backend/logs/dropi_reporter_YYYYMMDD_HHMMSS.log`

Ejemplo de log:
```
2026-01-16 14:45:23 - DropiReporterBot - INFO - Procesando orden 1/50
2026-01-16 14:45:23 - DropiReporterBot - INFO - Teléfono: 3219683976 | Estado: EN BODEGA ORIGEN
2026-01-16 14:45:25 - DropiReporterBot - INFO - ✓ Orden encontrada para teléfono: 3219683976
2026-01-16 14:45:26 - DropiReporterBot - INFO - ✓ Estado validado: EN BODEGA ORIGEN
2026-01-16 14:45:30 - DropiReporterBot - INFO - ✓ ÉXITO: Reporte creado exitosamente
```

### Archivo de resultados

Los resultados se exportan a: `backend/results/dropi_reporter_results_YYYYMMDD_HHMMSS.csv`

Columnas del CSV:
- `phone`: Número de teléfono
- `state`: Estado de la orden
- `success`: True/False
- `message`: Mensaje descriptivo del resultado

### Estadísticas finales

Al terminar, el bot muestra estadísticas como:

```
================================================================================
ESTADÍSTICAS FINALES
================================================================================
Total de órdenes:           50
Procesados exitosamente:    42
Ya tenían caso abierto:     5
No encontrados:             2
Errores:                    1
================================================================================
Tasa de éxito: 84.00%
================================================================================
```

## 🛡️ Manejo de errores

El bot maneja automáticamente los siguientes casos:

### 1. Orden ya tiene un caso abierto
- Detecta el popup de "Orden ya tiene un caso"
- Hace click en "Cancelar"
- Continúa con la siguiente orden
- Incrementa el contador `ya_tienen_caso`

### 2. Orden no encontrada
- Registra en el log
- Incrementa el contador `no_encontrados`
- Continúa con la siguiente orden

### 3. Estado no coincide
- Valida que el estado en Dropi coincida con el del Excel
- Si no coincide, registra el error y continúa
- Incrementa el contador `errores`

### 4. Errores de navegación
- Timeouts
- Elementos no encontrados
- Errores de click
- Todos son registrados en el log con detalles completos

## 🔍 Debugging

### Ver logs en tiempo real

Los logs se muestran en consola mientras el bot se ejecuta. Para ver más detalles, revisa el archivo de log generado.

### Ejecutar sin headless

Para ver el navegador en acción (útil para debugging):

```bash
python manage.py reporter --excel "ruta/al/archivo.xlsx"
```

### Procesar solo algunas órdenes

Puedes modificar temporalmente el Excel para incluir solo las órdenes que quieres probar.

## 💻 Rendimiento y Recursos Locales

### Ejecución 100% Local (No Docker)

Este bot está **optimizado para ejecutarse directamente en tu PC**, no requiere Docker:

✅ **Usa recursos de tu computadora**:
- CPU local
- RAM local
- Conexión a internet directa
- ChromeDriver local

✅ **Ventajas de ejecución local**:
- ⚡ **Más rápido**: No hay overhead de Docker
- 👀 **Visible**: Ves exactamente qué hace el bot
- 🔧 **Fácil de debuggear**: Puedes pausar, inspeccionar, etc.
- 💾 **Menos recursos**: No necesita contenedores

### Navegador Visible por Defecto

Por defecto, el bot **abre Chrome en tu pantalla** para que puedas:
- Ver el login en tiempo real
- Observar cómo busca las órdenes
- Verificar que todo funciona correctamente
- Detectar problemas visualmente

Si prefieres que trabaje en segundo plano, usa `--headless`.

### Recursos Recomendados

Para un rendimiento óptimo:
- **RAM**: 4GB mínimo (8GB recomendado)
- **CPU**: Cualquier procesador moderno
- **Conexión**: Internet estable
- **Chrome**: Versión actualizada


## ⚙️ Requisitos técnicos

### Python packages
- selenium
- pandas
- openpyxl (para leer Excel)
- webdriver-manager (opcional, para gestión automática de ChromeDriver)

### ChromeDriver

El bot usa Chrome. Asegúrate de tener:
- Google Chrome instalado
- ChromeDriver compatible con tu versión de Chrome

Si usas `webdriver-manager`, esto se gestiona automáticamente.

## 🚨 Consideraciones importantes

1. **Rate limiting**: El bot incluye pausas entre operaciones para evitar ser detectado como bot
2. **Sesión única**: Cada ejecución inicia una nueva sesión en Dropi
3. **Duplicados**: El bot elimina duplicados por teléfono automáticamente
4. **Orden de procesamiento**: Procesa las órdenes en el orden que aparecen en el Excel

## 📞 Soporte

Si encuentras algún problema:

1. Revisa el archivo de log generado
2. Verifica que el Excel tenga el formato correcto
3. Asegúrate de que las credenciales sean correctas
4. Prueba ejecutar sin `--headless` para ver qué está pasando

## 🔄 Actualizaciones futuras

Posibles mejoras:
- [ ] Credenciales desde variables de entorno
- [ ] Soporte para múltiples tipos de consulta
- [ ] Reintentos automáticos en caso de error
- [ ] Notificaciones por email al terminar
- [ ] Dashboard web para monitoreo en tiempo real
- [ ] Programación de ejecuciones automáticas

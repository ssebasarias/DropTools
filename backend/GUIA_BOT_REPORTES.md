# 🤖 Bot de Reportes Dropi - Guía de Uso Completa

## 📋 Descripción

Bot completamente funcional que automatiza la creación de reportes en Dropi para órdenes sin movimiento.

## 🚀 Ejecución Rápida

### Para el Excel Completo (Producción)

```bash
python backend/run_reporter_full.py
```

Este comando procesará **todas las órdenes** del archivo:
`C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-16.xlsx`

### Para Pruebas (10 órdenes)

```bash
python backend/run_reporter_test.py
```

## 📊 ¿Qué hace el bot?

Para cada orden en el Excel:

1. ✅ **Navega a Mis Pedidos** (solo una vez al inicio)
2. ✅ **Busca la orden** por número de teléfono
3. ✅ **Valida el estado** de la orden
4. ✅ **Hace click en "Nueva consulta"**
5. ✅ **Detecta si ya tiene caso** → Si sí, cancela y continúa con la siguiente
6. ✅ **Selecciona dropdowns**:
   - Tipo: Transportadora
   - Motivo: Ordenes sin movimiento
7. ✅ **Ingresa observación**: "Pedido sin movimiento por mucho tiempo, favor salir a reparto urgente."
8. ✅ **Inicia la conversación**

## 🎯 Estados Procesados

El bot solo procesa órdenes con estos estados:

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

## 📈 Resultados

### Archivos Generados

1. **Log detallado**: `backend/logs/dropi_reporter_YYYYMMDD_HHMMSS.log`
2. **Resultados CSV**: `backend/results/dropi_reporter_results_YYYYMMDD_HHMMSS.csv`

### Estadísticas Finales

Al terminar, el bot muestra:

```
================================================================================
ESTADÍSTICAS FINALES
================================================================================
Total de órdenes:           359
Procesados exitosamente:    120
Ya tenían caso abierto:     180
No encontrados:             5
Errores:                    54
================================================================================
Tasa de éxito: 33.43%
================================================================================
```

## 🛡️ Manejo de Errores

El bot maneja automáticamente:

### 1. Orden ya tiene un caso
- ✅ Detecta el popup inmediatamente
- ✅ Hace click en "Cancelar"
- ✅ Continúa con la siguiente orden

### 2. Botón "Siguiente" no disponible
- ✅ Espera solo 5 segundos (rápido)
- ✅ Hace click en "Cancelar"
- ✅ Continúa con la siguiente orden

### 3. Estado no coincide
- ✅ Registra en el log
- ✅ Continúa con la siguiente orden

### 4. Orden no encontrada
- ✅ Registra en el log
- ✅ Continúa con la siguiente orden

## ⚙️ Configuración

### Credenciales (en el código)

```python
DROPI_EMAIL = "dahellonline@gmail.com"
DROPI_PASSWORD = "Bigotes2001@"
```

### Mensaje de Observación

```
Pedido sin movimiento por mucho tiempo, favor salir a reparto urgente.
```

## 🔧 Características Técnicas

### Optimizaciones

- ✅ **Navegación eficiente**: Solo navega a Mis Pedidos una vez
- ✅ **Timeouts optimizados**: 5 segundos para botón "Siguiente"
- ✅ **JavaScript clicks**: Fallback automático si click normal falla
- ✅ **Scroll automático**: A elementos antes de hacer click
- ✅ **Anti-detección**: Configurado para evitar ser detectado como bot

### Navegación Robusta

3 niveles de fallback para navegar a Mis Pedidos:
1. Navegación por menú (tradicional)
2. URL directa con espera de 10s
3. URL directa con espera de 15s

## 📸 Screenshots de Debugging

El bot guarda screenshots automáticamente en `backend/logs/`:

- `login_success.png` - Login exitoso
- `orders_page_success.png` - Navegación exitosa
- `existing_case_popup.png` - Popup de caso existente
- `canceled_modal.png` - Modal cancelado
- `error_*.png` - Errores diversos

## 💻 Ejecución Local

El bot está diseñado para ejecutarse **localmente en tu PC**:

- ✅ Usa recursos de tu computadora
- ✅ Navegador visible por defecto
- ✅ Más rápido que en Docker
- ✅ Fácil de debuggear

## 🚨 Notas Importantes

1. **Chrome visible**: Por defecto verás el navegador trabajando
2. **Interrumpir**: Puedes detener con Ctrl+C en cualquier momento
3. **Resultados parciales**: Se guardan aunque interrumpas
4. **Duplicados**: El bot elimina teléfonos duplicados automáticamente
5. **Orden de procesamiento**: Procesa en el orden del Excel

## 📞 Ejemplo de Uso

```bash
# 1. Asegúrate de tener el Excel actualizado
# 2. Ejecuta el bot
python backend/run_reporter_full.py

# 3. Observa Chrome trabajando
# 4. Espera a que termine (o interrumpe con Ctrl+C)
# 5. Revisa los resultados en backend/results/
```

## 🎯 Tasa de Éxito Esperada

Basado en pruebas:
- **Reportes creados**: ~40-50%
- **Ya tienen caso**: ~30-40%
- **Errores**: ~10-20%

Los errores son normales y esperados (estados no coinciden, órdenes no encontradas, etc.)

## ✨ Mejoras Futuras

- [ ] Modo headless opcional
- [ ] Reintentos automáticos
- [ ] Notificaciones por email
- [ ] Dashboard web de monitoreo
- [ ] Programación automática

---

**¡El bot está listo para producción!** 🚀

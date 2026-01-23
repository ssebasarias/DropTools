# Checklist de Verificación - Sistema de Progreso de Workflow

## ✅ Verificaciones Completadas

### 1. Base de Datos
- [x] Tabla `workflow_progress` existe
- [x] Todas las columnas están correctas (11 columnas)
- [x] Índices creados correctamente
- [x] Migración 0015 aplicada

### 2. Modelo WorkflowProgress
- [x] Modelo definido correctamente
- [x] Campos: status, current_message, messages, timestamps
- [x] STATUS_CHOICES definidos correctamente
- [x] db_table = 'workflow_progress' ✅

### 3. Backend - Views
- [x] `ReporterStartView` crea WorkflowProgress al iniciar
- [x] `ReporterStatusView` devuelve workflow_progress
- [x] `ReporterListView` devuelve days_without_movement calculado
- [x] Email de DropiAccount se obtiene correctamente (cuenta secundaria)
- [x] Comando workflow_orchestrator se ejecuta con --user-email del DropiAccount

### 4. Backend - Workflow Orchestrator
- [x] Inicializa progreso al comenzar (usa el creado por ReporterStartView)
- [x] Actualiza progreso en cada paso con mensajes específicos:
  - Paso 1: "Descargando reportes..." → "Se ha creado el reporte del día..."
  - Paso 2: "Comparando reportes..." → "Se han obtenido las órdenes sin movimiento"
  - Paso 3: "Comenzando a reportar CAS..." → "Proceso de reporte CAS completado"
- [x] Maneja errores y actualiza estado a 'failed'
- [x] Usa correctamente el email de DropiAccount

### 5. Frontend
- [x] Estado workflowProgress definido
- [x] Panel de progreso agregado manualmente
- [x] Polling cada 3 segundos cuando workflow está corriendo
- [x] Polling cada 10 segundos cuando está inactivo
- [x] Muestra mensajes de progreso en tiempo real
- [x] Muestra órdenes reportadas con days_without_movement

### 6. Nombres de Columnas Verificados

#### WorkflowProgress (Backend → Frontend)
- `status` → `workflowProgress.status` ✅
- `current_message` → `workflowProgress.current_message` ✅
- `messages` → `workflowProgress.messages` ✅

#### OrderReport (Backend → Frontend)
- `order_phone` → `report.order_phone` ✅
- `customer_name` → `report.customer_name` ✅
- `product_name` → `report.product_name` ✅
- `status` → `report.status` ✅
- `days_without_movement` → `report.days_without_movement` ✅ (calculado dinámicamente)

### 7. Flujo de Mensajes
- [x] "Esto puede tardar unos minutos..." (al iniciar)
- [x] "Se ha creado el reporte del día..." (paso 1 completado)
- [x] "Se han obtenido las órdenes sin movimiento" (paso 2 completado)
- [x] "Comenzando a reportar CAS..." (paso 3 iniciado)
- [x] "Proceso de reporte CAS completado" (paso 3 completado)

## 🚀 Estado Final

**✅ SISTEMA LISTO PARA PRUEBAS DESDE EL FRONTEND**

### Próximos Pasos

1. **Reiniciar contenedor backend Docker** (si aplica):
   ```powershell
   docker-compose restart backend
   ```

2. **Probar desde el frontend**:
   - Ir a la página de Reporter Configuration
   - Hacer clic en "Iniciar a Reportar"
   - Verificar que aparece el panel de progreso
   - Verificar que los mensajes se actualizan en tiempo real
   - Verificar que las órdenes reportadas aparecen en el panel

### Notas Importantes

- El email usado es el de la **cuenta Dropi (cuenta secundaria)**, no el email del usuario
- El sistema busca primero una cuenta con `is_default=True`, luego cualquier cuenta del usuario
- El cálculo de `days_without_movement` se hace dinámicamente basado en `created_at`
- El panel de progreso solo aparece cuando hay un workflow activo o reciente

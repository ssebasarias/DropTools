# 🎯 PLAN DE IMPLEMENTACIÓN DETALLADO - REPORTER SETUP

**Fecha:** 2026-02-05  
**Objetivo:** Implementar mejoras en Reporter Setup siguiendo la visión del usuario  
**Tiempo estimado total:** 4-5 horas

---

## 🔒 FASE 1: BLOQUEAR PÁGINAS NO FUNCIONALES (30-45 minutos)

### **Historia 1.1: Deshabilitar "Winner Products" y "Análisis de Reportes" en el Sidebar**

**Archivo a modificar:** `frontend/src/components/layout/UserSidebar.jsx`

**Ubicación exacta:** Líneas 13-17 (array `navItems`)

---

#### ✅ PASO 1.1.1: Agregar propiedad `disabled` a los nav items

**Líneas a modificar:** 13-17

**CÓDIGO ANTES:**
```javascript
const navItems = [
    { path: '/user/dashboard', label: 'Winner Products', icon: Trophy, glow: true },
    { path: '/user/reporter-setup', label: 'Configuración Reporter', icon: Bot },
    { path: '/user/analysis', label: 'Análisis de Reportes', icon: BarChart3 },
];
```

**CÓDIGO DESPUÉS:**
```javascript
const navItems = [
    { 
        path: '/user/dashboard', 
        label: 'Winner Products', 
        icon: Trophy, 
        glow: true,
        disabled: true, // ← AGREGAR
        disabledMessage: 'Esta función estará disponible próximamente. Estamos trabajando en traerte los mejores productos ganadores.' // ← AGREGAR
    },
    { 
        path: '/user/reporter-setup', 
        label: 'Configuración Reporter', 
        icon: Bot 
    },
    { 
        path: '/user/analysis', 
        label: 'Análisis de Reportes', 
        icon: BarChart3,
        disabled: true, // ← AGREGAR
        disabledMessage: 'Análisis avanzado disponible próximamente. Podrás ver estadísticas detalladas de tus reportes.' // ← AGREGAR
    },
];
```

**Qué hace:** Agrega dos propiedades nuevas a los items que queremos deshabilitar:
- `disabled: true` → Marca el item como deshabilitado
- `disabledMessage` → Mensaje que aparecerá en el tooltip

---

#### ✅ PASO 1.1.2: Importar el icono Lock

**Línea a modificar:** 3

**CÓDIGO ANTES:**
```javascript
import { Trophy, Bot, BarChart3, Zap } from 'lucide-react';
```

**CÓDIGO DESPUÉS:**
```javascript
import { Trophy, Bot, BarChart3, Zap, Lock } from 'lucide-react';
```

**Qué hace:** Importa el icono de candado que usaremos para indicar que la página está bloqueada.

---

#### ✅ PASO 1.1.3: Modificar el renderizado de NavLink

**Líneas a modificar:** 32-43

**CÓDIGO ANTES:**
```javascript
<nav className="nav-menu">
    {navItems.map((item) => (
        <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''} ${item.glow ? 'glow-effect' : ''}`
            }
        >
            <item.icon size={20} />
            <span>{item.label}</span>
        </NavLink>
    ))}
</nav>
```

**CÓDIGO DESPUÉS:**
```javascript
<nav className="nav-menu">
    {navItems.map((item) => {
        // Si está deshabilitado, renderizar como div en lugar de NavLink
        if (item.disabled) {
            return (
                <div
                    key={item.path}
                    className="nav-item nav-item-disabled"
                    title={item.disabledMessage}
                    style={{
                        opacity: 0.5,
                        cursor: 'not-allowed',
                        position: 'relative',
                        pointerEvents: 'none',
                        filter: 'grayscale(0.3)'
                    }}
                >
                    <item.icon size={20} />
                    <span>{item.label}</span>
                    
                    {/* Badge "Próximamente" */}
                    <span style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(245, 158, 11, 0.2)',
                        color: '#f59e0b',
                        border: '1px solid rgba(245, 158, 11, 0.3)'
                    }}>
                        Próximamente
                    </span>
                    
                    {/* Icono de candado */}
                    <Lock 
                        size={14} 
                        style={{
                            position: 'absolute',
                            bottom: '8px',
                            right: '8px',
                            color: 'rgba(245, 158, 11, 0.6)'
                        }}
                    />
                </div>
            );
        }
        
        // Si NO está deshabilitado, renderizar NavLink normal
        return (
            <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                    `nav-item ${isActive ? 'active' : ''} ${item.glow ? 'glow-effect' : ''}`
                }
            >
                <item.icon size={20} />
                <span>{item.label}</span>
            </NavLink>
        );
    })}
</nav>
```

**Qué hace:**
1. Verifica si el item tiene `disabled: true`
2. Si está deshabilitado:
   - Renderiza un `<div>` en lugar de `<NavLink>` (para que no sea clicable)
   - Aplica estilos: opacidad 50%, cursor not-allowed, grayscale
   - Agrega badge amarillo "Próximamente" en esquina superior derecha
   - Agrega icono de candado en esquina inferior derecha
   - Muestra tooltip con el mensaje explicativo
3. Si NO está deshabilitado, renderiza el NavLink normal

---

#### ✅ PASO 1.1.4: Agregar estilos CSS para nav-item-disabled

**Archivo a modificar:** `frontend/src/components/layout/Sidebar.css`

**Ubicación:** Al final del archivo

**CÓDIGO A AGREGAR:**
```css
/* Estilo para items deshabilitados del sidebar */
.nav-item-disabled {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.nav-item-disabled:hover {
    background: rgba(255, 255, 255, 0.03) !important;
    transform: none !important;
}
```

**Qué hace:**
- Define estilos específicos para items deshabilitados
- Evita que se animen al hacer hover
- Mantiene un fondo sutil para que se vean "apagados"

---

### ✅ RESULTADO ESPERADO DE FASE 1:

Al completar esta fase, deberías ver:

1. **Winner Products:**
   - Opacidad 50%
   - Badge amarillo "Próximamente" arriba a la derecha
   - Candado pequeño abajo a la derecha
   - No se puede hacer click
   - Tooltip al hacer hover: "Esta función estará disponible próximamente..."

2. **Análisis de Reportes:**
   - Mismos efectos visuales
   - Tooltip diferente: "Análisis avanzado disponible próximamente..."

3. **Configuración Reporter:**
   - Sin cambios, sigue funcionando normal

---

## 💬 FASE 2: MEJORAR MENSAJES EN REPORTER SETUP (1 hora)

### **Historia 2.1: Reemplazar mensajes técnicos por amigables**

**Archivo a modificar:** `frontend/src/pages/user/ReporterConfig.jsx`

---

#### ✅ PASO 2.1.1: Importar icono Package si no existe

**Línea a modificar:** 2

**CÓDIGO ANTES:**
```javascript
import { Save, Info, Clock, Mail, Key, Plus, CheckCircle2, XCircle, RefreshCw, FileText, Phone, User, Package, Square, Calendar, BarChart3, Lock } from 'lucide-react';
```

**VERIFICAR:** Que `Package` esté en la lista de imports. Si no está, agregarlo.

---

#### ✅ PASO 2.1.2: Cambiar label de "Órdenes mensuales aproximadas"

**Línea a modificar:** 562

**CÓDIGO ANTES:**
```javascript
<label className="form-label" style={{ display: 'block', marginBottom: '0.35rem' }}>Órdenes mensuales aproximadas</label>
```

**CÓDIGO DESPUÉS:**
```javascript
<label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
    <Package size={16} style={{ color: 'var(--primary)' }} />
    Cuéntanos cuántas órdenes aproximadas tienes al mes
</label>
```

**Qué hace:**
- Cambia el texto técnico por uno más amigable
- Agrega icono de paquete para dar contexto visual
- Usa flexbox para alinear icono y texto

---

#### ✅ PASO 2.1.3: Agregar tooltip explicativo al input de órdenes

**Ubicación:** Después de la línea 562 (después del label, antes del input)

**CÓDIGO A AGREGAR:**
```javascript
<p className="text-muted" style={{ fontSize: '0.8rem', margin: '0.25rem 0 0.5rem 0' }}>
    Esto nos ayuda a asignar la mejor hora para que tu reporte termine a tiempo 🚀
</p>
```

**Qué hace:**
- Explica por qué pedimos este dato
- Usa emoji para dar personalidad
- Texto pequeño y sutil (no invasivo)

---

#### ✅ PASO 2.1.4: Cambiar mensaje de "Reserva por hora diaria"

**Línea a modificar:** 515-517

**CÓDIGO ANTES:**
```javascript
<p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
    Elige la hora en que se ejecutará tu reporter cada día. La capacidad se calcula por volumen de órdenes. Si una hora está llena, se muestra con candado.
</p>
```

**CÓDIGO DESPUÉS:**
```javascript
<p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: '1.6' }}>
    ⏰ <strong>A esta hora se reportará automáticamente tu CAS todos los días.</strong><br/>
    Selecciona la hora que mejor se ajuste a tu operación. Si una hora está llena por alta demanda, aparecerá con candado 🔒
</p>
```

**Qué hace:**
- Enfatiza el beneficio principal (reporte automático diario)
- Usa emojis para dar personalidad
- Explica de forma simple el sistema de candados
- Mejora legibilidad con line-height

---

#### ✅ PASO 2.1.5: Cambiar título de sección de slots

**Línea a modificar:** 511-513

**CÓDIGO ANTES:**
```javascript
<h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
    <Calendar size={22} style={{ color: 'var(--primary)' }} />
    Reserva por hora diaria
</h3>
```

**CÓDIGO DESPUÉS:**
```javascript
<h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
    <Clock size={22} style={{ color: 'var(--primary)' }} />
    Selecciona tu hora de reporte automático
</h3>
```

**Qué hace:**
- Cambia icono de Calendar a Clock (más apropiado)
- Título más claro y orientado a la acción

---

#### ✅ PASO 2.1.6: Cambiar mensaje cuando no hay reportes

**Línea a modificar:** 778-782

**CÓDIGO ANTES:**
```javascript
<EmptyState
    icon={Package}
    title="No hay órdenes reportadas aún"
    description="Los reportes se ejecutan automáticamente según tu reserva por hora."
/>
```

**CÓDIGO DESPUÉS:**
```javascript
<EmptyState
    icon={Package}
    title="No hay reportes por el momento"
    description="Revisa después de tu hora asignada. Estaremos reportando automáticamente tus órdenes sin movimiento 📦"
/>
```

**Qué hace:**
- Mensaje más positivo ("por el momento" vs "aún")
- Indica cuándo revisar (después de la hora asignada)
- Refuerza el beneficio (automático)
- Emoji para dar personalidad

---

#### ✅ PASO 2.1.7: Mejorar mensaje de confirmación de reserva

**Línea a modificar:** 295-297

**CÓDIGO ANTES:**
```javascript
<p style={{ margin: 0, fontSize: '1rem', color: 'var(--success)', fontWeight: 600 }}>
    Tu reporte se ejecuta diariamente a las {myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`}.
</p>
```

**CÓDIGO DESPUÉS:**
```javascript
<p style={{ margin: 0, fontSize: '1rem', color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
    <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
    ¡Todo listo! Tu reporte se ejecutará automáticamente todos los días a las {myReservation.slot?.hour_label ?? `${String(myReservation.slot?.hour ?? '').padStart(2, '0')}:00`} 🎉
</p>
```

**Qué hace:**
- Agrega icono de check para reforzar éxito
- Mensaje celebratorio ("¡Todo listo!")
- Emoji de celebración
- Enfatiza "automáticamente todos los días"

---

### ✅ RESULTADO ESPERADO DE FASE 2:

Al completar esta fase, todos los mensajes deberían:
- Ser más cálidos y amigables
- Tener emojis donde sea apropiado
- Explicar el "por qué" no solo el "qué"
- Dar sensación de acompañamiento

---

## 🔄 FASE 3: REORGANIZAR FLUJO Y BLOQUEO DE SLOTS (2-3 horas)

### **Historia 3.1: Implementar lógica de bloqueo de slots hasta ingresar órdenes**

**Archivo a modificar:** `frontend/src/pages/user/ReporterConfig.jsx`

---

#### ✅ PASO 3.1.1: Agregar mensaje explicativo cuando no hay órdenes ingresadas

**Ubicación:** Después de la línea 521 (antes del grid de slots)

**CÓDIGO A AGREGAR:**
```javascript
{/* Mensaje de advertencia si no hay órdenes ingresadas */}
{(!monthlyOrdersEstimate || monthlyOrdersEstimate === 0) && (
    <div style={{
        padding: '1rem',
        background: 'rgba(245, 158, 11, 0.1)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        borderRadius: '12px',
        marginBottom: '1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
    }}>
        <Info size={20} style={{ color: '#f59e0b', flexShrink: 0 }} />
        <p style={{ margin: 0, fontSize: '0.9rem', color: '#f59e0b' }}>
            <strong>Primero ingresa tus órdenes mensuales aproximadas</strong> para ver las horas disponibles según tu volumen de operación.
        </p>
    </div>
)}
```

**Qué hace:**
- Muestra un banner amarillo de advertencia
- Solo aparece si NO hay órdenes ingresadas
- Explica por qué los slots están bloqueados
- Usa icono de Info para llamar la atención

---

#### ✅ PASO 3.1.2: Modificar renderizado de slots con lógica de bloqueo

**Líneas a modificar:** 522-559

**CÓDIGO ANTES:**
```javascript
{slots.map((s) => (
    <button
        key={s.id}
        type="button"
        onClick={() => !s.available ? null : setSelectedSlotId(s.id)}
        disabled={!s.available}
        style={{
            padding: '0.6rem',
            borderRadius: '10px',
            border: selectedSlotId === s.id ? '2px solid var(--primary)' : '1px solid var(--glass-border)',
            background: selectedSlotId === s.id ? 'rgba(99,102,241,0.2)' : (s.available ? 'var(--glass-bg)' : 'rgba(239,68,68,0.1)'),
            color: s.available ? 'var(--text-main)' : 'var(--text-muted)',
            cursor: s.available ? 'pointer' : 'not-allowed',
            fontSize: '0.85rem',
            fontWeight: 600
        }}
        title={s.available ? `${s.hour_label} — ${s.used_points ?? 0}/${s.capacity_points ?? 6} puntos` : 'Hora llena por alta demanda'}
    >
        {s.available ? (
            <>
                {s.hour_label}
                <div style={{ fontSize: '0.7rem', fontWeight: 400, marginTop: '0.2rem', color: 'var(--text-muted)' }}>
                    {(s.used_points ?? 0)}/{(s.capacity_points ?? 6)}
                </div>
            </>
        ) : (
            <>
                <Lock size={18} style={{ marginBottom: '0.2rem' }} />
                {s.hour_label}
                <div style={{ fontSize: '0.7rem', fontWeight: 400, marginTop: '0.2rem', color: 'var(--text-muted)' }}>
                    Hora llena
                </div>
            </>
        )}
    </button>
))}
```

**CÓDIGO DESPUÉS:**
```javascript
{slots.map((s) => {
    // Determinar si está bloqueado por falta de input de órdenes
    const blockedByNoInput = !monthlyOrdersEstimate || monthlyOrdersEstimate === 0;
    // Determinar si está bloqueado por capacidad
    const blockedByCapacity = !s.available;
    // Está bloqueado si cualquiera de las dos condiciones es verdadera
    const isBlocked = blockedByNoInput || blockedByCapacity;
    
    // Determinar el mensaje del tooltip
    let tooltipMessage = '';
    if (blockedByNoInput) {
        tooltipMessage = '⚠️ Primero ingresa tus órdenes mensuales aproximadas';
    } else if (blockedByCapacity) {
        tooltipMessage = '🔒 Hora llena por alta demanda. Intenta otra hora';
    } else {
        tooltipMessage = `${s.hour_label} — ${s.used_points ?? 0}/${s.capacity_points ?? 6} puntos disponibles`;
    }
    
    // Determinar el color de fondo
    let backgroundColor = 'var(--glass-bg)';
    if (selectedSlotId === s.id) {
        backgroundColor = 'rgba(99,102,241,0.2)';
    } else if (isBlocked) {
        backgroundColor = 'rgba(100,100,100,0.1)';
    }
    
    return (
        <button
            key={s.id}
            type="button"
            onClick={() => isBlocked ? null : setSelectedSlotId(s.id)}
            disabled={isBlocked}
            style={{
                padding: '0.6rem',
                borderRadius: '10px',
                border: selectedSlotId === s.id ? '2px solid var(--primary)' : '1px solid var(--glass-border)',
                background: backgroundColor,
                color: isBlocked ? 'var(--text-muted)' : 'var(--text-main)',
                cursor: isBlocked ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                fontWeight: 600,
                opacity: isBlocked ? 0.5 : 1,
                transition: 'all 0.3s ease'
            }}
            title={tooltipMessage}
        >
            {isBlocked ? (
                <>
                    <Lock size={18} style={{ marginBottom: '0.2rem' }} />
                    {s.hour_label}
                    <div style={{ fontSize: '0.7rem', fontWeight: 400, marginTop: '0.2rem', color: 'var(--text-muted)' }}>
                        {blockedByNoInput ? 'Bloqueado' : 'Hora llena'}
                    </div>
                </>
            ) : (
                <>
                    {s.hour_label}
                    <div style={{ fontSize: '0.7rem', fontWeight: 400, marginTop: '0.2rem', color: 'var(--text-muted)' }}>
                        {(s.used_points ?? 0)}/{(s.capacity_points ?? 6)}
                    </div>
                </>
            )}
        </button>
    );
})}
```

**Qué hace:**
1. Define tres variables de control:
   - `blockedByNoInput`: true si no hay órdenes ingresadas
   - `blockedByCapacity`: true si la hora está llena
   - `isBlocked`: true si cualquiera de las dos anteriores es true

2. Determina el mensaje del tooltip según el tipo de bloqueo

3. Aplica estilos diferentes según el estado:
   - Bloqueado por input: opacidad 50%, candado, texto "Bloqueado"
   - Bloqueado por capacidad: opacidad 50%, candado, texto "Hora llena"
   - Disponible: normal con contador de puntos

4. Agrega transición suave de 0.3s

---

#### ✅ PASO 3.1.3: Deshabilitar botón "Confirmar reserva" si no hay órdenes

**Líneas a modificar:** 573-582

**CÓDIGO ANTES:**
```javascript
<button
    type="button"
    className="btn-primary"
    disabled={!selectedSlotId || reservationSaving}
    onClick={handleConfirmReservation}
    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
>
    {reservationSaving ? <RefreshCw size={18} className="spinning" /> : <CheckCircle2 size={18} />}
    {reservationSaving ? 'Guardando...' : 'Confirmar reserva'}
</button>
```

**CÓDIGO DESPUÉS:**
```javascript
<button
    type="button"
    className="btn-primary"
    disabled={!selectedSlotId || reservationSaving || !monthlyOrdersEstimate || monthlyOrdersEstimate === 0}
    onClick={handleConfirmReservation}
    style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '0.5rem',
        opacity: (!selectedSlotId || !monthlyOrdersEstimate || monthlyOrdersEstimate === 0) ? 0.5 : 1,
        cursor: (!selectedSlotId || !monthlyOrdersEstimate || monthlyOrdersEstimate === 0) ? 'not-allowed' : 'pointer'
    }}
    title={
        !monthlyOrdersEstimate || monthlyOrdersEstimate === 0 
            ? 'Primero ingresa tus órdenes mensuales' 
            : (!selectedSlotId ? 'Selecciona una hora' : 'Confirmar y guardar configuración')
    }
>
    {reservationSaving ? <RefreshCw size={18} className="spinning" /> : <CheckCircle2 size={18} />}
    {reservationSaving ? 'Guardando...' : 'Confirmar reserva'}
</button>
```

**Qué hace:**
- Deshabilita el botón si no hay órdenes ingresadas
- Reduce opacidad a 50% cuando está deshabilitado
- Muestra tooltip explicativo según el motivo del bloqueo
- Cambia cursor a not-allowed

---

### ✅ RESULTADO ESPERADO DE FASE 3:

Al completar esta fase:

1. **Sin órdenes ingresadas:**
   - Banner amarillo visible explicando que debe ingresar órdenes
   - TODOS los slots con candado y opacidad 50%
   - Tooltip: "⚠️ Primero ingresa tus órdenes mensuales aproximadas"
   - Botón confirmar deshabilitado

2. **Con órdenes ingresadas:**
   - Banner amarillo desaparece
   - Slots disponibles se habilitan (sin candado)
   - Slots llenos por capacidad siguen con candado
   - Tooltip diferenciado: "🔒 Hora llena" vs "X/6 puntos disponibles"
   - Botón confirmar habilitado al seleccionar hora

---

## 🎨 FASE 4: REFINAMIENTO DE UX (1 hora)

### **Historia 4.1: Agregar transiciones y animaciones suaves**

**Archivo a modificar:** `frontend/src/pages/user/ReporterConfig.jsx`

---

#### ✅ PASO 4.1.1: Agregar keyframes de animación

**Ubicación:** Línea 234 (dentro del tag `<style>`)

**CÓDIGO ANTES:**
```javascript
<style>{`
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spinning {
        animation: spin 1s linear infinite;
    }
`}</style>
```

**CÓDIGO DESPUÉS:**
```javascript
<style>{`
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spinning {
        animation: spin 1s linear infinite;
    }
    
    /* Animación fade-in con movimiento hacia arriba */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Animación slide-in desde la izquierda */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
`}</style>
```

**Qué hace:**
- Define animación `fadeInUp` para paneles que aparecen
- Define animación `slideIn` para elementos que se habilitan

---

#### ✅ PASO 4.1.2: Aplicar animación a panel de información de cuenta

**Línea a modificar:** 270

**CÓDIGO ANTES:**
```javascript
{myReservation && (
    <div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(16,185,129,0.25)' }}>
```

**CÓDIGO DESPUÉS:**
```javascript
{myReservation && (
    <div 
        className="glass-card" 
        style={{ 
            marginBottom: '2rem', 
            border: '2px solid rgba(16,185,129,0.25)',
            animation: 'fadeInUp 0.5s ease-out'
        }}
    >
```

**Qué hace:**
- Aplica animación fade-in con movimiento hacia arriba
- Duración 0.5 segundos
- Solo se anima cuando aparece (cuando hay reserva)

---

#### ✅ PASO 4.1.3: Aplicar animación a paneles de KPIs

**Líneas a modificar:** 629, 660, 750

**Buscar estas líneas y agregar la propiedad `animation`:**

```javascript
// Panel de KPIs (línea 629)
<div className="glass-card" style={{ marginBottom: '2rem', animation: 'fadeInUp 0.6s ease-out' }}>

// Panel de progreso (línea 660)
<div className="glass-card" style={{ marginBottom: '2rem', border: '2px solid rgba(99,102,241,0.3)', animation: 'fadeInUp 0.7s ease-out' }}>

// Panel de tabla (línea 750)
<div className="glass-card" style={{ animation: 'fadeInUp 0.8s ease-out' }}>
```

**Qué hace:**
- Anima cada panel con un delay progresivo (0.6s, 0.7s, 0.8s)
- Crea efecto de cascada al aparecer

---

### **Historia 4.2: Agregar validaciones y feedback visual**

---

#### ✅ PASO 4.2.1: Validar rango de órdenes mensuales

**Líneas a modificar:** 563-571

**CÓDIGO ANTES:**
```javascript
<input
    type="number"
    min={0}
    className="glass-input"
    value={monthlyOrdersEstimate || ''}
    onChange={(e) => setMonthlyOrdersEstimate(parseInt(e.target.value, 10) || 0)}
    placeholder="Ej. 500"
    style={{ width: '100%', maxWidth: '180px' }}
/>
```

**CÓDIGO DESPUÉS:**
```javascript
<input
    type="number"
    min={0}
    max={50000}
    className="glass-input"
    value={monthlyOrdersEstimate || ''}
    onChange={(e) => {
        const value = parseInt(e.target.value, 10) || 0;
        // Validar rango
        if (value < 0) {
            setMonthlyOrdersEstimate(0);
        } else if (value > 50000) {
            setMonthlyOrdersEstimate(50000);
            // Mostrar mensaje temporal
            setError('El máximo de órdenes mensuales es 50,000. Si tienes más, contacta soporte.');
            setTimeout(() => setError(''), 3000);
        } else {
            setMonthlyOrdersEstimate(value);
        }
    }}
    placeholder="Ej. 500"
    style={{ 
        width: '100%', 
        maxWidth: '180px',
        borderColor: monthlyOrdersEstimate > 50000 ? 'var(--danger)' : 'var(--glass-border)',
        transition: 'border-color 0.3s ease'
    }}
/>
```

**Qué hace:**
- Valida que el valor esté entre 0 y 50,000
- Si excede 50,000, lo limita y muestra mensaje de error
- Mensaje de error desaparece después de 3 segundos
- Cambia color del borde si hay error

---

#### ✅ PASO 4.2.2: Agregar indicador visual de volumen

**Ubicación:** Después del input de órdenes (línea 571)

**CÓDIGO A AGREGAR:**
```javascript
{/* Indicador de volumen */}
{monthlyOrdersEstimate > 0 && (
    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
        <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginBottom: '0.25rem',
            color: 'var(--text-muted)'
        }}>
            <span>Volumen estimado:</span>
            <span style={{ 
                fontWeight: 600, 
                color: monthlyOrdersEstimate <= 2000 ? 'var(--success)' : 
                       monthlyOrdersEstimate <= 5000 ? 'var(--warning)' : 
                       'var(--primary)'
            }}>
                {monthlyOrdersEstimate <= 2000 ? '🟢 Bajo (peso 1)' : 
                 monthlyOrdersEstimate <= 5000 ? '🟡 Medio (peso 2)' : 
                 '🔵 Alto (peso 3)'}
            </span>
        </div>
        <div style={{
            height: '4px',
            background: 'rgba(255,255,255,0.1)',
            borderRadius: '2px',
            overflow: 'hidden'
        }}>
            <div style={{
                height: '100%',
                width: `${Math.min((monthlyOrdersEstimate / 10000) * 100, 100)}%`,
                background: monthlyOrdersEstimate <= 2000 ? 'var(--success)' :
                           monthlyOrdersEstimate <= 5000 ? 'var(--warning)' :
                           'var(--primary)',
                transition: 'width 0.3s ease, background 0.3s ease',
                borderRadius: '2px'
            }}></div>
        </div>
    </div>
)}
```

**Qué hace:**
- Muestra indicador de volumen solo si hay órdenes ingresadas
- Clasifica en Bajo (0-2000), Medio (2001-5000), Alto (5001+)
- Muestra emoji de color según el nivel
- Barra de progreso visual que crece con el número
- Transiciones suaves al cambiar

---

### ✅ RESULTADO ESPERADO DE FASE 4:

Al completar esta fase:

1. **Animaciones:**
   - Paneles aparecen con fade-in suave
   - Efecto cascada en paneles con reserva
   - Transiciones suaves en todos los cambios de estado

2. **Validaciones:**
   - Input de órdenes limitado a 0-50,000
   - Mensaje de error temporal si excede
   - Borde rojo si hay error

3. **Feedback visual:**
   - Indicador de volumen (Bajo/Medio/Alto)
   - Barra de progreso que crece
   - Colores según nivel (verde/amarillo/azul)

---

## ✅ CHECKLIST FINAL DE VERIFICACIÓN

### Visual:
- [ ] Items deshabilitados tienen opacidad 50%
- [ ] Badge "Próximamente" visible en esquina superior derecha
- [ ] Icono de candado visible en esquina inferior derecha
- [ ] Cursor cambia a `not-allowed` en items deshabilitados
- [ ] Slots bloqueados tienen candado y opacidad 50%
- [ ] Banner amarillo aparece cuando no hay órdenes
- [ ] Indicador de volumen visible con colores correctos

### Funcional:
- [ ] No se puede hacer click en items deshabilitados del sidebar
- [ ] Tooltip aparece al hacer hover en items deshabilitados
- [ ] TODOS los slots bloqueados hasta ingresar órdenes
- [ ] Slots se habilitan al ingresar órdenes
- [ ] Diferenciación entre bloqueo por input vs capacidad
- [ ] Botón confirmar deshabilitado sin datos completos
- [ ] Validación de rango 0-50,000 funciona
- [ ] Mensaje de error aparece y desaparece

### Mensajes:
- [ ] Todos los mensajes son amigables y claros
- [ ] Emojis presentes donde corresponde
- [ ] Tooltips informativos en todos los elementos interactivos
- [ ] Mensajes explican el "por qué" no solo el "qué"

### Animaciones:
- [ ] Fade-in suave en paneles con reserva
- [ ] Efecto cascada en paneles (0.6s, 0.7s, 0.8s)
- [ ] Transiciones de 0.3s en cambios de estado
- [ ] Barra de progreso se anima suavemente

---

## 🚀 ORDEN RECOMENDADO DE IMPLEMENTACIÓN

1. **Empezar por FASE 1** (30-45 min)
   - Es la más simple
   - Resultados visibles inmediatamente
   - No afecta lógica existente

2. **Continuar con FASE 2** (1 hora)
   - Solo cambios de texto
   - Bajo riesgo de errores
   - Mejora percepción inmediata

3. **Seguir con FASE 3** (2-3 horas)
   - Requiere más atención
   - Cambios en lógica de negocio
   - Probar exhaustivamente

4. **Terminar con FASE 4** (1 hora)
   - Pulir detalles
   - Agregar animaciones
   - Validaciones finales

**Tiempo total estimado:** 4.5 - 5.5 horas

---

## 📝 NOTAS IMPORTANTES

1. **Probar después de cada fase:** No esperes a terminar todo para probar
2. **Hacer commits frecuentes:** Un commit por fase mínimo
3. **Verificar en diferentes navegadores:** Chrome, Firefox, Edge
4. **Probar flujo completo:** Desde usuario nuevo hasta reserva confirmada
5. **Verificar responsive:** Aunque no es prioridad, revisar que no se rompa en móvil

---

**¿Listo para empezar? Comienza con FASE 1 y avísame cuando termines para revisar antes de continuar.** 🚀

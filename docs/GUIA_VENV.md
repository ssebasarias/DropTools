# 🔧 GUÍA DE USO DEL ENTORNO VIRTUAL (venv)

## ✅ Estado Actual

- **Python:** 3.12.7
- **venv:** Configurado y funcional
- **Encoding:** UTF-8 en todo el sistema

---

## 🚀 Activación del Entorno Virtual

### Opción 1: Script Automático (Recomendado)
```bash
.\activate_env.bat
```

Este script:
- Activa el venv
- Configura UTF-8 como encoding por defecto
- Muestra información del entorno

### Opción 2: Activación Manual
```bash
.\venv\Scripts\activate
```

Luego configurar UTF-8:
```bash
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
```

---

## 📦 Instalación de Dependencias

### Instalar TODAS las dependencias (Primera vez)
```bash
# Activar venv primero
.\activate_env.bat

# Instalar dependencias completas
pip install -r requirements_complete.txt
```

### Instalar dependencias faltantes específicas
```bash
pip install selenium transformers sentence-transformers torchvision
```

### Verificar dependencias instaladas
```bash
pip list
pip check
```

---

## 🔍 Verificación del Entorno

### Verificar que estás en el venv
```bash
# Deberías ver (venv) al inicio de la línea de comandos
# Ejemplo: (venv) C:\Users\guerr\Documents\AnalisisDeDatos\Dahell>

# Verificar Python
python --version
# Debería mostrar: Python 3.12.7

# Verificar pip
pip --version
# Debería mostrar: pip 24.2 from ...\Dahell\venv\Lib\site-packages\pip
```

### Verificar encoding UTF-8
```bash
python -c "import sys; print(f'Encoding: {sys.stdout.encoding}')"
# Debería mostrar: Encoding: utf-8
```

---

## 🎯 Ejecutar Scripts con el venv

### Scripts de Management (Django)
```bash
# Activar venv
.\activate_env.bat

# Ejecutar management commands
python backend/manage.py scraper
python backend/manage.py loader
python backend/manage.py vectorizer
python backend/manage.py clusterizer
python backend/manage.py diagnose_stats
```

### Scripts Standalone
```bash
# Activar venv
.\activate_env.bat

# Ejecutar scripts
python scripts/diagnose_system.py
python scripts/test_db_encoding.py
```

### Servidor Django
```bash
# Activar venv
.\activate_env.bat

# Ejecutar servidor de desarrollo
cd backend
python manage.py runserver
```

---

## 🐛 Solución de Problemas

### Problema: "pip install" falla con error de permisos
**Solución:**
1. Cerrar todos los terminales y editores
2. Abrir PowerShell como Administrador
3. Navegar al proyecto: `cd C:\Users\guerr\Documents\AnalisisDeDatos\Dahell`
4. Activar venv: `.\venv\Scripts\activate`
5. Intentar instalar de nuevo

### Problema: "ModuleNotFoundError" al ejecutar scripts
**Solución:**
1. Verificar que el venv está activado: `.\activate_env.bat`
2. Instalar la dependencia faltante: `pip install [nombre_paquete]`
3. Actualizar `requirements_complete.txt` si es necesario

### Problema: Errores de encoding (UnicodeDecodeError)
**Solución:**
1. Verificar que `config_encoding.py` está importado en el script
2. Ejecutar: `python -c "from config_encoding import setup_utf8; setup_utf8()"`
3. Verificar variables de entorno:
   ```bash
   echo %PYTHONIOENCODING%  # Debería ser utf-8
   echo %PYTHONUTF8%        # Debería ser 1
   ```

### Problema: venv corrupto o no funciona
**Solución - Recrear venv:**
```bash
# 1. Desactivar venv si está activo
deactivate

# 2. Eliminar venv antiguo
rmdir /s /q venv

# 3. Crear nuevo venv
python -m venv venv

# 4. Activar nuevo venv
.\venv\Scripts\activate

# 5. Actualizar pip
python -m pip install --upgrade pip

# 6. Instalar dependencias
pip install -r requirements_complete.txt
```

---

## 📝 Buenas Prácticas

### ✅ SIEMPRE hacer:
1. **Activar el venv** antes de ejecutar cualquier script
2. **Usar `requirements_complete.txt`** para instalar dependencias
3. **Verificar encoding UTF-8** al inicio de cada sesión
4. **Ejecutar `pip check`** después de instalar paquetes

### ❌ NUNCA hacer:
1. **NO instalar paquetes** sin activar el venv
2. **NO usar Python global** para scripts del proyecto
3. **NO mezclar encodings** (latin-1, cp1252, etc.)
4. **NO editar archivos** con editores que no soporten UTF-8

---

## 🔄 Actualizar Dependencias

### Actualizar un paquete específico
```bash
pip install --upgrade [nombre_paquete]
```

### Actualizar todas las dependencias
```bash
pip install --upgrade -r requirements_complete.txt
```

### Generar nuevo requirements.txt
```bash
pip freeze > requirements_frozen.txt
```

---

## 🎓 Comandos Útiles

```bash
# Ver paquetes instalados
pip list

# Buscar un paquete
pip search [nombre]

# Ver información de un paquete
pip show [nombre_paquete]

# Desinstalar un paquete
pip uninstall [nombre_paquete]

# Limpiar caché de pip
pip cache purge

# Verificar integridad
pip check
```

---

## 📊 Estructura del Proyecto con venv

```
Dahell/
├── venv/                          # Entorno virtual (NO subir a Git)
│   ├── Scripts/
│   │   ├── activate.bat           # Activador de venv
│   │   ├── python.exe             # Python del venv
│   │   └── pip.exe                # pip del venv
│   └── Lib/                       # Librerías instaladas
├── activate_env.bat               # Script de activación personalizado
├── config_encoding.py             # Configuración UTF-8 global
├── requirements.txt               # Dependencias básicas
├── requirements_complete.txt      # Dependencias completas
├── backend/                       # Django backend
├── scripts/                       # Scripts standalone
└── .env                           # Variables de entorno
```

---

## ✨ Resumen Rápido

```bash
# 1. Activar venv
.\activate_env.bat

# 2. Verificar entorno
python --version
pip --version

# 3. Instalar dependencias (si es necesario)
pip install -r requirements_complete.txt

# 4. Ejecutar scripts
python backend/manage.py [comando]
python scripts/[script].py

# 5. Desactivar venv (al terminar)
deactivate
```

---

**¡Listo! Ahora tu entorno virtual está configurado correctamente con UTF-8 en todo el sistema.**

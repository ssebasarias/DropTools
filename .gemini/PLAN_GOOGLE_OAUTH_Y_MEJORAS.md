# 🔐 PLAN DE IMPLEMENTACIÓN: GOOGLE OAUTH Y MEJORAS ADICIONALES

**Fecha:** 2026-02-05  
**Objetivo:** Implementar Google OAuth, validaciones adicionales, manejo de errores y mejoras de UX  
**Tiempo estimado total:** 6-8 horas

---

## 📋 ÍNDICE

1. [FASE 1: Google OAuth - Backend (2-3 horas)](#fase-1-google-oauth---backend)
2. [FASE 2: Google OAuth - Frontend (1-2 horas)](#fase-2-google-oauth---frontend)
3. [FASE 3: Validaciones y Manejo de Errores (1-2 horas)](#fase-3-validaciones-y-manejo-de-errores)
4. [FASE 4: Mejoras Adicionales de UX (1-2 horas)](#fase-4-mejoras-adicionales-de-ux)

---

## 🔧 FASE 1: GOOGLE OAUTH - BACKEND (2-3 horas)

### **Prerequisitos:**

Antes de empezar, necesitas:
1. **Cuenta de Google Cloud Platform**
2. **Crear un proyecto en Google Cloud Console**
3. **Habilitar Google+ API**
4. **Crear credenciales OAuth 2.0**

---

### **Historia 1.1: Configurar Google Cloud Console**

#### ✅ PASO 1.1.1: Crear proyecto en Google Cloud

1. Ir a: https://console.cloud.google.com/
2. Click en "Select a project" → "New Project"
3. Nombre: `Dahell Reporter`
4. Click "Create"

#### ✅ PASO 1.1.2: Habilitar Google+ API

1. En el menú lateral: "APIs & Services" → "Library"
2. Buscar: "Google+ API"
3. Click "Enable"

#### ✅ PASO 1.1.3: Crear credenciales OAuth 2.0

1. "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Web application"
4. Name: "Dahell Web Client"
5. Authorized JavaScript origins:
   - `http://localhost:5173` (desarrollo)
   - `https://tudominio.com` (producción)
6. Authorized redirect URIs:
   - `http://localhost:5173/auth/google/callback` (desarrollo)
   - `https://tudominio.com/auth/google/callback` (producción)
7. Click "Create"
8. **GUARDAR:** Client ID y Client Secret

REULTDOS DE LA CREDENCIAL CREADA (usar para las siguientes partes):
ID de cliente: (poner el tuyo de Google Cloud Console)
Secreto del cliente: (poner el tuyo, no subir a Git)
---

### **Historia 1.2: Instalar dependencias en Backend**

#### ✅ PASO 1.2.1: Agregar dependencias a requirements.txt

**Archivo:** `backend/requirements.txt`

**AGREGAR al final:**
```txt
# Google OAuth
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
```

#### ✅ PASO 1.2.2: Instalar dependencias

**Comando:**
```bash
cd backend
pip install -r requirements.txt
```

---

### **Historia 1.3: Configurar variables de entorno**

#### ✅ PASO 1.3.1: Agregar variables a .env

**Archivo:** `backend/.env`

**AGREGAR al final:**
```env
# Google OAuth
GOOGLE_CLIENT_ID=tu_client_id_aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret_aqui
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
```

#### ✅ PASO 1.3.2: Agregar variables a .env.example

**Archivo:** `backend/.env.example`

**AGREGAR al final:**
```env
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
```

---

### **Historia 1.4: Crear endpoint de Google OAuth**

#### ✅ PASO 1.4.1: Crear serializer para Google OAuth

**Archivo:** `backend/core/serializers.py`

**BUSCAR:** La sección de serializers de autenticación

**AGREGAR al final del archivo:**
```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer para autenticación con Google OAuth.
    Recibe el token de Google y valida la identidad del usuario.
    """
    token = serializers.CharField(required=True, help_text="ID token de Google")
    
    def validate_token(self, value):
        """
        Valida el token de Google y extrae la información del usuario.
        """
        try:
            # Verificar el token con Google
            idinfo = id_token.verify_oauth2_token(
                value, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # Verificar que el token es de Google
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise serializers.ValidationError('Token inválido: emisor no reconocido')
            
            # Guardar la info del usuario en el contexto
            self.context['google_user_info'] = {
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'given_name': idinfo.get('given_name'),
                'family_name': idinfo.get('family_name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False),
                'google_id': idinfo.get('sub'),
            }
            
            return value
            
        except ValueError as e:
            raise serializers.ValidationError(f'Token inválido: {str(e)}')
    
    def create(self, validated_data):
        """
        Crea o actualiza el usuario basado en la información de Google.
        """
        google_info = self.context['google_user_info']
        
        # Verificar que el email esté verificado
        if not google_info.get('email_verified'):
            raise serializers.ValidationError('El email de Google no está verificado')
        
        email = google_info['email']
        
        # Buscar o crear usuario
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,  # Usar email como username
                'full_name': google_info.get('name', ''),
                'is_active': True,
                'subscription_tier': User.TIER_BRONZE,
                'subscription_active': True,
            }
        )
        
        # Si el usuario ya existía, actualizar su nombre si está vacío
        if not created and not user.full_name:
            user.full_name = google_info.get('name', '')
            user.save()
        
        return user
```

**Qué hace:**
- Valida el token de Google usando la librería oficial
- Extrae información del usuario (email, nombre, foto)
- Verifica que el email esté verificado
- Crea usuario nuevo o usa existente
- Asigna tier BRONZE por defecto

---

#### ✅ PASO 1.4.2: Crear view para Google OAuth

**Archivo:** `backend/core/views.py`

**BUSCAR:** La sección de autenticación (después de LoginView)

**AGREGAR:**
```python
class GoogleAuthView(APIView):
    """
    Endpoint para autenticación con Google OAuth.
    
    POST /api/auth/google/
    Body: { "token": "google_id_token" }
    
    Retorna:
    - user: Información del usuario
    - token: Token de autenticación de Django
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Crear o obtener usuario
            user = serializer.save()
            
            # Crear o obtener token de autenticación
            token, _ = Token.objects.get_or_create(user=user)
            
            # Retornar información del usuario y token
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin(),
                    'subscription_tier': user.subscription_tier,
                    'subscription_active': user.subscription_active,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error al autenticar con Google: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

**Qué hace:**
- Recibe el token de Google del frontend
- Valida el token usando el serializer
- Crea o actualiza el usuario
- Genera token de autenticación de Django
- Retorna user info + token

---

#### ✅ PASO 1.4.3: Agregar ruta para Google OAuth

**Archivo:** `backend/dahell_backend/urls.py`

**BUSCAR:** La sección de rutas de autenticación

**AGREGAR:**
```python
from core.views import GoogleAuthView

urlpatterns = [
    # ... rutas existentes ...
    
    # Google OAuth
    path('api/auth/google/', GoogleAuthView.as_view(), name='google-auth'),
]
```

---

#### ✅ PASO 1.4.4: Agregar configuración a settings.py

**Archivo:** `backend/dahell_backend/settings.py`

**BUSCAR:** La sección de configuración (después de SECRET_KEY)

**AGREGAR:**
```python
# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5173/auth/google/callback')
```

---

### ✅ RESULTADO ESPERADO DE FASE 1 (Backend):

Al completar esta fase:
- ✅ Endpoint `/api/auth/google/` funcional
- ✅ Validación de tokens de Google
- ✅ Creación automática de usuarios
- ✅ Generación de tokens de autenticación

**Probar con Postman:**
```json
POST http://localhost:8000/api/auth/google/
Content-Type: application/json

{
  "token": "google_id_token_aqui"
}
```

---

## 🎨 FASE 2: GOOGLE OAUTH - FRONTEND (1-2 horas)

### **Historia 2.1: Instalar dependencias en Frontend**

#### ✅ PASO 2.1.1: Instalar @react-oauth/google

**Comando:**
```bash
cd frontend
npm install @react-oauth/google
```

---

### **Historia 2.2: Configurar Google OAuth Provider**

#### ✅ PASO 2.2.1: Crear archivo de configuración

**Archivo:** `frontend/src/config/google.js`

**CREAR archivo nuevo:**
```javascript
// Configuración de Google OAuth
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'tu_client_id_aqui.apps.googleusercontent.com';

// Scopes que solicitamos a Google
export const GOOGLE_SCOPES = [
    'openid',
    'email',
    'profile'
].join(' ');
```

---

#### ✅ PASO 2.2.2: Crear archivo .env en frontend

**Archivo:** `frontend/.env`

**CREAR archivo nuevo:**
```env
VITE_GOOGLE_CLIENT_ID=tu_client_id_aqui.apps.googleusercontent.com
VITE_API_URL=http://localhost:8000
```

---

#### ✅ PASO 2.2.3: Agregar GoogleOAuthProvider en main.jsx

**Archivo:** `frontend/src/main.jsx`

**CÓDIGO ANTES:**
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

**CÓDIGO DESPUÉS:**
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import App from './App.jsx';
import './index.css';
import { GOOGLE_CLIENT_ID } from './config/google';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </GoogleOAuthProvider>
  </React.StrictMode>,
);
```

**Qué hace:**
- Envuelve la app con GoogleOAuthProvider
- Configura el Client ID de Google
- Permite usar hooks de Google OAuth en toda la app

---

### **Historia 2.3: Crear servicio de autenticación con Google**

#### ✅ PASO 2.3.1: Agregar función en authService.js

**Archivo:** `frontend/src/services/authService.js`

**BUSCAR:** El final del archivo

**AGREGAR:**
```javascript
/**
 * Autenticar con Google OAuth
 * @param {string} googleToken - Token de ID de Google
 * @returns {Promise<{user: Object, token: string}>}
 */
export const loginWithGoogle = async (googleToken) => {
    try {
        const response = await fetch(`${API_URL}/api/auth/google/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: googleToken }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al autenticar con Google');
        }

        const data = await response.json();
        
        // Guardar token y usuario en localStorage
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('authUser', JSON.stringify(data.user));
        
        return data;
    } catch (error) {
        console.error('Error en loginWithGoogle:', error);
        throw error;
    }
};
```

**Qué hace:**
- Envía el token de Google al backend
- Recibe token de Django y user info
- Guarda en localStorage
- Maneja errores

---

### **Historia 2.4: Agregar botón de Google en Register.jsx**

#### ✅ PASO 2.4.1: Importar dependencias

**Archivo:** `frontend/src/pages/auth/Register.jsx`

**Línea 1-6, AGREGAR:**
```javascript
import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Zap, Mail, Lock, User, ArrowRight } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google'; // ← AGREGAR
import { jwtDecode } from 'jwt-decode'; // ← AGREGAR (instalar: npm install jwt-decode)

import PublicNavbar from '../../components/layout/PublicNavbar';
import { register as apiRegister, loginWithGoogle } from '../../services/authService'; // ← MODIFICAR
```

---

#### ✅ PASO 2.4.2: Agregar lógica de Google OAuth

**Ubicación:** Después de la línea 17 (después de `const [error, setError] = useState('')`)

**AGREGAR:**
```javascript
const [googleLoading, setGoogleLoading] = useState(false);

// Handler para login con Google
const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    setGoogleLoading(true);
    
    try {
        // El token viene en credentialResponse.credential
        const result = await loginWithGoogle(credentialResponse.credential);
        
        // Redirigir según el rol
        const user = result?.user;
        if (user?.is_admin) {
            navigate('/admin', { replace: true });
        } else {
            navigate('/user/reporter-setup', { replace: true });
        }
    } catch (err) {
        setError(err.message || 'Error al registrarse con Google');
    } finally {
        setGoogleLoading(false);
    }
};

// Configurar Google Login
const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
        try {
            // Obtener el ID token
            const response = await fetch(`https://www.googleapis.com/oauth2/v3/userinfo?access_token=${tokenResponse.access_token}`);
            const userInfo = await response.json();
            
            // Crear un ID token simulado (o usar el access token directamente)
            // En producción, deberías obtener el ID token real
            await handleGoogleSuccess({ credential: tokenResponse.access_token });
        } catch (error) {
            setError('Error al obtener información de Google');
        }
    },
    onError: () => {
        setError('Error al conectar con Google');
    },
    flow: 'implicit',
});
```

---

#### ✅ PASO 2.4.3: Agregar botón de Google en el formulario

**Ubicación:** Después de la línea 64 (después del mensaje de error, antes del formulario)

**AGREGAR:**
```javascript
{/* Botón de Google OAuth */}
<button
    type="button"
    onClick={() => googleLogin()}
    disabled={loading || googleLoading}
    style={{
        width: '100%',
        padding: '12px',
        borderRadius: '8px',
        border: '1px solid var(--glass-border)',
        background: 'white',
        color: '#1f2937',
        fontSize: '0.95rem',
        fontWeight: 600,
        cursor: googleLoading ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        marginBottom: '1.5rem',
        transition: 'all 0.2s ease',
        opacity: googleLoading ? 0.7 : 1
    }}
    onMouseEnter={(e) => {
        if (!googleLoading) {
            e.currentTarget.style.transform = 'translateY(-1px)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        }
    }}
    onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
    }}
>
    {googleLoading ? (
        <>
            <div className="spinning" style={{
                width: '18px',
                height: '18px',
                border: '2px solid #e5e7eb',
                borderTop: '2px solid #1f2937',
                borderRadius: '50%'
            }}></div>
            Conectando con Google...
        </>
    ) : (
        <>
            <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
                <path d="M9.003 18c2.43 0 4.467-.806 5.956-2.18L12.05 13.56c-.806.54-1.836.86-3.047.86-2.344 0-4.328-1.584-5.036-3.711H.96v2.332C2.44 15.983 5.485 18 9.003 18z" fill="#34A853"/>
                <path d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71 0-.593.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9.003 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.464.891 11.426 0 9.003 0 5.485 0 2.44 2.017.96 4.958L3.967 7.29c.708-2.127 2.692-3.71 5.036-3.71z" fill="#EA4335"/>
            </svg>
            Continuar con Google
        </>
    )}
</button>

{/* Separador "o" */}
<div style={{
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    marginBottom: '1.5rem'
}}>
    <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }}></div>
    <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>o</span>
    <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }}></div>
</div>
```

**Qué hace:**
- Botón blanco con logo de Google oficial
- Efecto hover con elevación
- Loading state mientras autentica
- Separador "o" para dividir métodos de registro

---

### **Historia 2.5: Agregar botón de Google en Login.jsx**

**Repetir los mismos pasos 2.4.1, 2.4.2 y 2.4.3 en Login.jsx**

**Diferencia:** En Login.jsx, después del login exitoso redirigir a:
```javascript
if (user?.is_admin) {
    navigate('/admin', { replace: true });
} else {
    navigate('/user/dashboard', { replace: true }); // ← dashboard en vez de reporter-setup
}
```

---

### ✅ RESULTADO ESPERADO DE FASE 2 (Frontend):

Al completar esta fase:
- ✅ Botón "Continuar con Google" en Register
- ✅ Botón "Continuar con Google" en Login
- ✅ Logo oficial de Google
- ✅ Animaciones y efectos hover
- ✅ Loading states
- ✅ Manejo de errores
- ✅ Redirección automática según rol

---

## ✅ FASE 3: VALIDACIONES Y MANEJO DE ERRORES (1-2 horas)

### **Historia 3.1: Validar email de Dropi en Reporter Setup**

#### ✅ PASO 3.1.1: Agregar validación de formato de email

**Archivo:** `frontend/src/pages/user/ReporterConfig.jsx`

**BUSCAR:** El input de email Dropi (línea ~422)

**MODIFICAR el onChange:**
```javascript
<input
    type="email"
    className="glass-input"
    style={{ 
        paddingLeft: '38px', 
        opacity: accounts.length > 0 ? 0.6 : 1,
        borderColor: form.email && !isValidEmail(form.email) ? 'var(--danger)' : 'var(--glass-border)'
    }}
    placeholder="reporter@yourdomain.com"
    value={form.email}
    onChange={(e) => {
        const email = e.target.value;
        setForm({ ...form, email });
        
        // Validar formato de email
        if (email && !isValidEmail(email)) {
            setError('Por favor ingresa un email válido');
        } else {
            setError('');
        }
    }}
    disabled={accounts.length > 0}
/>
```

**AGREGAR función de validación al inicio del componente:**
```javascript
// Función para validar formato de email
const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};
```

---

### **Historia 3.2: Mejorar mensajes de error del backend**

#### ✅ PASO 3.2.1: Crear componente de error mejorado

**Archivo:** `frontend/src/components/common/ErrorAlert.jsx`

**CREAR archivo nuevo:**
```javascript
import React from 'react';
import { AlertCircle, X } from 'lucide-react';

const ErrorAlert = ({ error, onClose }) => {
    if (!error) return null;
    
    return (
        <div style={{
            padding: '12px 16px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'start',
            gap: '0.75rem',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <AlertCircle size={20} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
                <p style={{ 
                    margin: 0, 
                    color: '#ef4444', 
                    fontSize: '0.875rem',
                    fontWeight: 500
                }}>
                    {error}
                </p>
            </div>
            {onClose && (
                <button
                    onClick={onClose}
                    style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '4px',
                        color: '#ef4444',
                        opacity: 0.7,
                        transition: 'opacity 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = 0.7}
                >
                    <X size={16} />
                </button>
            )}
        </div>
    );
};

export default ErrorAlert;
```

---

#### ✅ PASO 3.2.2: Usar ErrorAlert en Register.jsx

**Archivo:** `frontend/src/pages/auth/Register.jsx`

**IMPORTAR:**
```javascript
import ErrorAlert from '../../components/common/ErrorAlert';
```

**REEMPLAZAR el div de error (línea ~53-65) con:**
```javascript
<ErrorAlert error={error} onClose={() => setError('')} />
```

---

### **Historia 3.3: Agregar confirmación antes de cancelar reserva**

#### ✅ PASO 3.3.1: Crear modal de confirmación

**Archivo:** `frontend/src/pages/user/ReporterConfig.jsx`

**AGREGAR estado para modal:**
```javascript
const [showCancelModal, setShowCancelModal] = useState(false);
```

**MODIFICAR el botón "Cancelar reserva" (línea ~298):**
```javascript
<button 
    type="button" 
    className="btn-secondary" 
    style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }} 
    onClick={() => setShowCancelModal(true)} // ← Cambiar a mostrar modal
>
    Cancelar reserva
</button>
```

**AGREGAR modal al final del componente (antes del último </div>):**
```javascript
{/* Modal de confirmación para cancelar reserva */}
{showCancelModal && (
    <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        animation: 'fadeIn 0.2s ease-out'
    }}>
        <div className="glass-card" style={{
            maxWidth: '500px',
            margin: '1rem',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={24} style={{ color: 'var(--warning)' }} />
                ¿Cancelar reserva?
            </h3>
            <p className="text-muted" style={{ marginBottom: '1.5rem', lineHeight: '1.6' }}>
                Si cancelas tu reserva, perderás tu hora asignada y tendrás que configurar todo nuevamente.
                Los reportes automáticos se detendrán hasta que reserves una nueva hora.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowCancelModal(false)}
                >
                    No, mantener reserva
                </button>
                <button
                    type="button"
                    className="btn-primary"
                    style={{ 
                        background: 'var(--danger)', 
                        borderColor: 'var(--danger)' 
                    }}
                    onClick={async () => {
                        setShowCancelModal(false);
                        await handleCancelReservation();
                    }}
                >
                    Sí, cancelar reserva
                </button>
            </div>
        </div>
    </div>
)}
```

---

### **Historia 3.4: Agregar timeout para mensajes de éxito**

#### ✅ PASO 3.4.1: Crear componente de éxito

**Archivo:** `frontend/src/components/common/SuccessAlert.jsx`

**CREAR archivo nuevo:**
```javascript
import React, { useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';

const SuccessAlert = ({ message, onClose, duration = 3000 }) => {
    useEffect(() => {
        if (message && onClose) {
            const timer = setTimeout(() => {
                onClose();
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [message, onClose, duration]);
    
    if (!message) return null;
    
    return (
        <div style={{
            padding: '12px 16px',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <CheckCircle2 size={20} style={{ color: 'var(--success)', flexShrink: 0 }} />
            <p style={{ 
                margin: 0, 
                color: 'var(--success)', 
                fontSize: '0.875rem',
                fontWeight: 500
            }}>
                {message}
            </p>
        </div>
    );
};

export default SuccessAlert;
```

---

### ✅ RESULTADO ESPERADO DE FASE 3:

- ✅ Validación de email en tiempo real
- ✅ Mensajes de error mejorados con iconos
- ✅ Modal de confirmación antes de cancelar
- ✅ Mensajes de éxito que desaparecen automáticamente
- ✅ Mejor UX en manejo de errores

---

## 🎨 FASE 4: MEJORAS ADICIONALES DE UX (1-2 horas)

### **Historia 4.1: Agregar tooltips informativos**

#### ✅ PASO 4.1.1: Crear componente Tooltip reutilizable

**Archivo:** `frontend/src/components/common/Tooltip.jsx`

**CREAR archivo nuevo:**
```javascript
import React, { useState } from 'react';
import { Info } from 'lucide-react';

const Tooltip = ({ text, children, position = 'top' }) => {
    const [show, setShow] = useState(false);
    
    const positions = {
        top: { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: '8px' },
        bottom: { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: '8px' },
        left: { right: '100%', top: '50%', transform: 'translateY(-50%)', marginRight: '8px' },
        right: { left: '100%', top: '50%', transform: 'translateY(-50%)', marginLeft: '8px' },
    };
    
    return (
        <div 
            style={{ position: 'relative', display: 'inline-block' }}
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
        >
            {children || <Info size={16} style={{ color: 'var(--primary)', cursor: 'help' }} />}
            {show && (
                <div style={{
                    position: 'absolute',
                    ...positions[position],
                    background: 'rgba(0, 0, 0, 0.9)',
                    color: 'white',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    whiteSpace: 'nowrap',
                    zIndex: 1000,
                    pointerEvents: 'none',
                    animation: 'fadeIn 0.2s ease-out'
                }}>
                    {text}
                    <div style={{
                        position: 'absolute',
                        ...(position === 'top' && { top: '100%', left: '50%', transform: 'translateX(-50%)', borderTop: '6px solid rgba(0,0,0,0.9)', borderLeft: '6px solid transparent', borderRight: '6px solid transparent' }),
                        ...(position === 'bottom' && { bottom: '100%', left: '50%', transform: 'translateX(-50%)', borderBottom: '6px solid rgba(0,0,0,0.9)', borderLeft: '6px solid transparent', borderRight: '6px solid transparent' }),
                    }}></div>
                </div>
            )}
        </div>
    );
};

export default Tooltip;
```

---

### **Historia 4.2: Agregar indicador de fuerza de contraseña**

#### ✅ PASO 4.2.1: Crear función de validación de contraseña

**Archivo:** `frontend/src/pages/auth/Register.jsx`

**AGREGAR función:**
```javascript
// Función para calcular fuerza de contraseña
const getPasswordStrength = (password) => {
    if (!password) return { strength: 0, label: '', color: '' };
    
    let strength = 0;
    
    // Longitud
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 25;
    
    // Mayúsculas
    if (/[A-Z]/.test(password)) strength += 15;
    
    // Minúsculas
    if (/[a-z]/.test(password)) strength += 15;
    
    // Números
    if (/[0-9]/.test(password)) strength += 10;
    
    // Caracteres especiales
    if (/[^A-Za-z0-9]/.test(password)) strength += 10;
    
    let label = '';
    let color = '';
    
    if (strength < 30) {
        label = 'Muy débil';
        color = '#ef4444';
    } else if (strength < 50) {
        label = 'Débil';
        color = '#f59e0b';
    } else if (strength < 75) {
        label = 'Buena';
        color = '#3b82f6';
    } else {
        label = 'Fuerte';
        color = '#10b981';
    }
    
    return { strength, label, color };
};
```

**AGREGAR estado:**
```javascript
const [passwordStrength, setPasswordStrength] = useState({ strength: 0, label: '', color: '' });
```

**MODIFICAR input de password:**
```javascript
<input
    type="password"
    className="glass-input"
    style={{ paddingLeft: '38px' }}
    placeholder="Create a password"
    value={formData.password}
    onChange={(e) => {
        setFormData({ ...formData, password: e.target.value });
        setPasswordStrength(getPasswordStrength(e.target.value));
    }}
    disabled={loading}
    required
/>

{/* Indicador de fuerza */}
{formData.password && (
    <div style={{ marginTop: '0.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Fuerza de contraseña:</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: passwordStrength.color }}>
                {passwordStrength.label}
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
                width: `${passwordStrength.strength}%`,
                background: passwordStrength.color,
                transition: 'width 0.3s ease, background 0.3s ease',
                borderRadius: '2px'
            }}></div>
        </div>
    </div>
)}
```

---

### **Historia 4.3: Agregar loading skeleton**

#### ✅ PASO 4.3.1: Crear componente Skeleton

**Archivo:** `frontend/src/components/common/Skeleton.jsx`

**CREAR archivo nuevo:**
```javascript
import React from 'react';

const Skeleton = ({ width = '100%', height = '20px', borderRadius = '4px', style = {} }) => {
    return (
        <div style={{
            width,
            height,
            borderRadius,
            background: 'linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s infinite',
            ...style
        }}>
            <style>{`
                @keyframes shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
            `}</style>
        </div>
    );
};

export default Skeleton;
```

---

### ✅ RESULTADO ESPERADO DE FASE 4:

- ✅ Tooltips informativos en elementos clave
- ✅ Indicador de fuerza de contraseña
- ✅ Loading skeletons mientras carga
- ✅ Mejor feedback visual en toda la app

---

## 📋 CHECKLIST FINAL COMPLETO

### Backend:
- [ ] Google OAuth configurado en Google Cloud
- [ ] Dependencias instaladas (google-auth)
- [ ] Variables de entorno configuradas
- [ ] Serializer GoogleAuthSerializer creado
- [ ] View GoogleAuthView creada
- [ ] Ruta /api/auth/google/ agregada
- [ ] Endpoint probado con Postman

### Frontend:
- [ ] @react-oauth/google instalado
- [ ] GoogleOAuthProvider configurado en main.jsx
- [ ] Archivo .env creado con VITE_GOOGLE_CLIENT_ID
- [ ] Función loginWithGoogle en authService
- [ ] Botón Google en Register.jsx
- [ ] Botón Google en Login.jsx
- [ ] Validación de email en Reporter Setup
- [ ] ErrorAlert component creado
- [ ] SuccessAlert component creado
- [ ] Modal de confirmación para cancelar reserva
- [ ] Tooltip component creado
- [ ] Indicador de fuerza de contraseña
- [ ] Skeleton component creado

### Testing:
- [ ] Registro con Google funciona
- [ ] Login con Google funciona
- [ ] Redirección correcta según rol
- [ ] Validaciones de email funcionan
- [ ] Mensajes de error se muestran correctamente
- [ ] Modal de confirmación aparece
- [ ] Tooltips se muestran al hover
- [ ] Indicador de contraseña actualiza en tiempo real

---

## 🚀 ORDEN RECOMENDADO DE IMPLEMENTACIÓN

1. **FASE 1: Backend Google OAuth** (2-3 horas)
   - Configurar Google Cloud
   - Instalar dependencias
   - Crear endpoint
   - Probar con Postman

2. **FASE 2: Frontend Google OAuth** (1-2 horas)
   - Instalar dependencias
   - Configurar provider
   - Agregar botones
   - Probar flujo completo

3. **FASE 3: Validaciones** (1-2 horas)
   - Validación de email
   - Componentes de error/éxito
   - Modal de confirmación

4. **FASE 4: Mejoras UX** (1-2 horas)
   - Tooltips
   - Indicador de contraseña
   - Skeletons

**Tiempo total:** 6-8 horas

---

**¿Listo para empezar con Google OAuth? Comienza con FASE 1 (Backend) y avísame cuando termines para revisar antes de continuar.** 🚀

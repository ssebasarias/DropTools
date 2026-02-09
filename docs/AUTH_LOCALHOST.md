# Login y registro en localhost (desarrollo)

Guía para que login (email y Google) funcione en tu máquina antes de tener servidor/dominio.

## 1. Ver si ya te registraste

Si intentaste registrarte y la app se quedó en blanco o no redirigió, es posible que **sí** te hayas registrado y solo falló la redirección. Para comprobarlo:

Desde la raíz del proyecto (con el backend activo):

```powershell
cd backend
python manage.py check_user
```

Lista los últimos 20 usuarios. Si quieres buscar un email concreto:

```powershell
python manage.py check_user tu_correo@gmail.com
```

- Si **aparece** y dice "puede entrar con contraseña: no (solo Google)" → tu cuenta se creó con Google. Entra solo con **"Iniciar sesión con Google"** (no con email/contraseña).
- Si **aparece** y dice "puede entrar con contraseña: sí" → puedes entrar con email y contraseña.
- Si **no aparece** → no hay cuenta con ese email; puedes registrarte de nuevo.

## 2. Configurar Google OAuth para localhost

El archivo `client_secret_...json` que descargas de Google suele traer solo `http://localhost:5173` en "javascript_origins". Si tu app corre en **5174** (u otro puerto), hay que añadirlo a mano:

1. Entra en [Google Cloud Console](https://console.cloud.google.com/) → **APIs y servicios** → **Credenciales**.
2. Abre el **mismo** cliente OAuth 2.0 (el que tiene el client_id del JSON).
3. En **Orígenes JavaScript autorizados** asegura tener:
   - `http://localhost:5173`
   - `http://localhost:5174`
   - (Cualquier otro puerto donde abras la app.)
4. Guarda. Los cambios pueden tardar un par de minutos.

Si no añades el origen exacto (por ejemplo `http://localhost:5174`), verás: *"The given origin is not allowed for the given client ID"*.

## 3. Usar un solo navegador para probar

- El **navegador embebido de Cursor** a veces da problemas con OAuth o redirecciones (pantalla en blanco).
- **Recomendado:** usar siempre el mismo navegador para desarrollo, por ejemplo **Chrome** o **Brave**, y abrir la app en `http://localhost:5173` (o el puerto que use tu frontend).
- Si te autenticaste con Google en el **móvil** pero la app se abría en el **PC**, el token se genera en el flujo del PC; si la ventana del PC se quedó en blanco, puede que el registro sí se haya creado en el backend (comprueba con `check_user`).

## 4. Variables de entorno

En la raíz del proyecto, archivo `.env` (o el que use tu backend):

- `GOOGLE_CLIENT_ID`: debe ser el **mismo** que en el frontend (o el que tengas en `.env.example`).
- Si no está definido, el backend usa un valor por defecto; en producción conviene definirlo.

El frontend usa `VITE_GOOGLE_CLIENT_ID`; si no está, usa el de `frontend/src/config/google.js`.

## 5. Login con email y redirección admin

- Si inicias sesión con **email y contraseña** (por ejemplo `guerreroarias20@gmail.com`), el backend detecta si el usuario es **admin** (`role == ADMIN`) y devuelve `is_admin: true`. El frontend redirige a **`/admin`** para admins y a **`/user/reporter-setup`** para clientes. No hace falta hacer nada extra: el mismo login ya te manda al panel correcto.

## 6. Si Google sigue fallando: mismo Client ID en frontend y backend

Si en la consola sigue saliendo *"The given origin is not allowed for the given client ID"* aunque ya añadiste los localhost en Google:

- En **Credenciales** de Google Cloud, en la misma ficha donde pusiste los orígenes, copia el **ID de cliente** (algo como `xxxxx.apps.googleusercontent.com`).
- En tu proyecto:
  - **Backend:** en el `.env` de la raíz: `GOOGLE_CLIENT_ID=<ese ID>`.
  - **Frontend:** en `.env` (en la raíz o en `frontend/`) pon `VITE_GOOGLE_CLIENT_ID=<ese mismo ID>`.
- Reinicia backend y frontend. Si el ID no coincidía, el token lo genera un cliente y el backend lo verifica con otro; al usar el mismo, el error de “origen no permitido” o “Wrong audience” debería desaparecer.

Si el backend devuelve error 500, en la consola del **servidor** (donde corre `python manage.py runserver` o Django) aparecerá el traceback. El mensaje también se envía en la respuesta; la app lo muestra en rojo en la pantalla de login.

## 7. Resumen rápido

| Problema | Qué hacer |
|----------|-----------|
| "¿Me registré o no?" | `python manage.py check_user` o `python manage.py check_user tu@email.com` |
| "Error al autenticar con Google" / "origin not allowed" | Añadir orígenes en Google y usar **el mismo** Client ID en backend y frontend (ver sección 6). |
| Pantalla en blanco después de login | Redirección con recarga completa; usa un navegador normal (Chrome/Brave) en localhost. |
| Entré con Google pero no con email/contraseña | Si la cuenta se creó solo con Google, no tiene contraseña; usa "Iniciar sesión con Google". |
| Login con mi correo admin | Con email/contraseña te redirige a `/admin` automáticamente (sección 5). |

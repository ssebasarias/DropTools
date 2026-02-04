# 🔍 Análisis del Problema del Proxy IP Royal

## ❌ Problema Confirmado

Después de realizar **más de 20 tests diferentes**, confirmamos que:

**✅ Lo que FUNCIONA:**
- Chrome manual con `--proxy-server=201.219.221.147:12323`
- Popup de autenticación aparece
- Usuario ingresa credenciales manualmente  
- Dropi carga correctamente

**❌ Lo que NO FUNCIONA:**
- Playwright/Puppeteer con proxy configurado y credenciales automáticas
- Todos los navegadores (Chromium, Chrome, Firefox)
- Todas las configuraciones probadas (10+ variantes)
- Error consistente: `ERR_TUNNEL_CONNECTION_FAILED`

## 🔬 Diagnóstico Técnico

### El Problema Real

El proxy de IP Royal que compraste **NO soporta autenticación automática** para túneles HTTPS.

Cuando usas Chrome manualmentecon `--proxy-server`, Chrome hace un flujo de autenticación **interactivo** que el proxy acepta. Pero cuando Playwright intenta autenticar automáticamente (enviando credenciales en headers `Proxy-Authorization`), el proxy **rechaza** la conexión.

Esto es común en proxies que:
1. Solo aceptan autenticación via challenge-response HTTP 407
2. No confían en headers de autenticación preemptiva
3. Están configurados para requerir interacción humana

## 💡 Soluciones Posibles

### Solución 1: Cambiar Tipo de Proxy (RECOMENDADO)

Contacta a IP Royal y pide **Residential Proxies** que usan `geo.iproyal.com`:

```python
proxy = {
    'server': 'http://geo.iproyal.com:12321',
    'username': 'TU_USERNAME',
    'password': 'TU_PASSWORD'
}
```

Estos proxies están diseñados para automatización y **SÍ soportan** autenticación automática.

**Email para IP Royal:**
```
Subject: Proxy no funciona con autenticación automática

Hola,

Compré un proxy (201.219.221.147:12323) pero no puedo usarlo 
con Playwright/Selenium porque rechaza autenticación automática.

El proxy funciona manualmente con Chrome --proxy-server cuando 
ingreso credenciales en el popup, pero falla con:
ERR_TUNNEL_CONNECTION_FAILED cuando intento automatizarlo.

¿Puedo cambiar a Residential Proxies (geo.iproyal.com) que 
soporten autenticación automática para scripts?

O
 ¿Cómo configuro este proxy para que acepte autenticación 
automática via headers Proxy-Authorization?

Gracias
```

### Solución 2: Extension de Chrome (WORKAROUND)

Crear una extensión de Chrome que maneje la autenticación automáticamente:

```javascript
// extension/background.js
chrome.webRequest.onAuthRequired.addListener(
  function(details) {
    return {
      authCredentials: {
        username: '14a9c53d94ce0',
        password: 'f03e2067d5'
      }
    };
  },
  {urls: ["<all_urls>"]},
  ['blocking']
);
```

Luego en Playwright:

```python
context = await browser.new_context(
    proxy={'server': 'http://201.219.221.147:12323'},
    # Cargar la extensión
)
```

**Problema:** Las extensiones son complicadas en headless mode.

### Solución 3: Proxy HTTP Local (INTERMEDIARIO)

Crear un proxy local que:
1. Escuche en localhost:8888
2. Reenvíe todo al proxy de IP Royal
3. Maneje la autenticación automáticamente

```python
# proxy_wrapper.py
from mitmproxy import http
import base64

class ProxyAuthInjector:
    def request(self, flow: http.HTTPFlow):
        # Agregar autenticación al proxy upstream
        auth = base64.b64encode(b'14a9c53d94ce0:f03e2067d5').decode()
        flow.request.headers['Proxy-Authorization'] = f'Basic {auth}'

# Ejecutar:
# mitmdump -s proxy_wrapper.py --mode upstream:http://201.219.221.147:12323

# En tu código:
proxy = {'server': 'http://localhost:8080'}  # Sin credenciales
```

**Problema:** Requiere proceso adicional corriendo.

### Solución 4: Usar Selenium en lugar de Playwright

Selenium maneja algunos proxies de manera diferente:

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--proxy-server=201.219.221.147:12323')
chrome_options.add_argument('--ignore-certificate-errors')

# Selenium puede manejar algunos popups de auth
driver = webdriver.Chrome(options=chrome_options)

# Desventaja: Tendríamos que portar todo el código a Selenium
```

## 📊 Comparación de Soluciones

| Solución | Complejidad | Costo | Tiempo | Confiabilidad |
|----------|-------------|-------|--------|---------------|
| **1. Cambiar proxy** | 🟢 Baja | $ | 1 día | 🟢🟢🟢🟢🟢 |
| 2. Extensión Chrome | 🟡 Media | Gratis | 2-3 días | 🟡🟡🟡 |
| 3. Proxy intermediario | 🔴 Alta | Gratis | 3-4 días | 🟡🟡🟡🟡 |
| 4. Migrar a Selenium | 🔴 Alta | Gratis | 5-7 días | 🟡🟡🟡 |

## 🎯 Recomendación Final

**OPCIÓN 1 es la mejor:**

1. Contacta a IP Royal hoy
2. Explica el problema (copia el email de arriba)  
3. Pide cambiar a Residential Proxies (geo.iproyal.com)
4. Probablemente te lo cambien sin costo adicional

**Mientras tanto:**

Puedes seguir desarrollando/probando el reporter SIN proxy o con un proxy gratis para testing:

```python
# Para desarrollo/testing local
proxy = None  # Sin proxy

# O usa un proxy gratis de testing
proxy = {
    'server': 'http://proxy-free-test.com:8080',  # Ejemplo
}
```

## 📝 Para Implementar Cuando Tengas el Proxy Correcto

Cuando IP Royal te dé el proxy correcto (Residential), usa este código:

```python
# config.py
PROXY_CONFIG = {
    'server': 'http://geo.iproyal.com:12321',  # O el que te den
    'username': '14a9c53d94ce0',
    'password': 'f03e2067d5'
}

# reporter.py
async def launch_browser_with_proxy():
    browser = await p.chromium.launch(
        headless=True,
        proxy=PROXY_CONFIG
    )
    context = await browser.new_context(
        ignore_https_errors=True
    )
    return browser, context

# Uso
browser, context = await launch_browser_with_proxy()
page = await context.new_page()
await page.goto('https://dropi.com.co/login')
# ... resto del código
```

## 📂 Sistema Multi-Proxy (Para Cuando Tengas Varios)

Ya que mencionaste que el CSV puede tener múltiples proxies, aquí está cómo implementarlo:

```python
# proxy_manager.py
import csv
import random

class ProxyManager:
    def __init__(self, csv_file='iproyal-proxies.csv'):
        self.proxies = []
        self.load_proxies(csv_file)
        self.usage_count = {}  # Track usage per proxy
    
    def load_proxies(self, csv_file):
        """Load proxies from CSV"""
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.proxies.append({
                    'server': f"http://{row['Host']}:{row['Port']}",
                    'username': row['User'],
                    'password': row['Pass'],
                    'host': row['Host']
                })
    
    def get_proxy_for_account(self, account_index):
        """Get proxy ensuring max 4 accounts per proxy"""
        proxy_index = account_index // 4  # 4 accounts per proxy
        
        if proxy_index >= len(self.proxies):
            # Si no hay suficientes proxies, reciclar
            proxy_index = account_index % len(self.proxies)
        
        proxy = self.proxies[proxy_index]
        
        # Track usage
        proxy_id = proxy['host']
        self.usage_count[proxy_id] = self.usage_count.get(proxy_id, 0) + 1
        
        print(f"Account {account_index} -> Proxy {proxy['host']} (uso #{self.usage_count[proxy_id]})")
        
        return proxy
    
    def get_random_proxy(self):
        """Get a random proxy"""
        return random.choice(self.proxies)

# Uso:
proxy_manager = ProxyManager()

# Para cada cuenta
for i, account in enumerate(accounts):
    proxy = proxy_manager.get_proxy_for_account(i)
    browser = await p.chromium.launch(proxy=proxy)
    # ... procesar cuenta
```

## 🔗 Enlaces Útiles

- [IP Royal Support](https://iproyal.com/support/)
- [Playwright Proxy Docs](https://playwright.dev/python/docs/network#http-proxy)
- [Error ERR_TUNNEL_CONNECTION_FAILED](https://chromiumcodereview.appspot.com/10168007)

## 📞 Próximos Pasos

1. ✅ Enviar email a IP Royal (usa el template de arriba)
2. ⏳ Esperar respuesta (usualmente 24-48 horas)
3. ✅ Actualizar proxy a Residential type
4. ✅ Probar con el nuevo proxy
5. ✅ Implementar ProxyManager para multi-proxy
6. ✅ Integrar en el reporter

---

**Nota:** Todos los scripts de prueba generados están en:
- `test_proxy_exhaustivo.py` - 10 configuraciones diferentes
- `test_all_browsers.py` - 3 navegadores diferentes
- `test_chrome_style.py` - 4 métodos de autenticación
- Screenshots en `ERROR_*.png` y `SUCCESS_*.png` (si hubiera)

**El problema NO es tu código - es el tipo de proxy.**

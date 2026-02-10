#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test único para verificar que el proxy Bright Data navega correctamente por internet.
Verifica:
1. Acceso a internet (verificación de IP)
2. Navegación a Google
3. Navegación a página de inicio de sesión de Dropi

Ejecutar desde la raíz del proyecto:
  python backend/scripts/test_brightdata_navegacion.py

O desde backend/:
  python scripts/test_brightdata_navegacion.py
"""
import os
import sys
import time
import django
from pathlib import Path

# Configurar Django
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'droptools_backend.settings')
django.setup()

from core.utils.stdio import configure_utf8_stdio
configure_utf8_stdio()  # Evita UnicodeEncodeError con emojis en Windows (cp1252)

from core.reporter_bot.driver_manager import DriverManager
from core.services.proxy_dev_loader import get_dev_proxy_config
from core.reporter_bot.utils import setup_logger

def test_navegacion_proxy():
    """Verifica que el proxy Bright Data navega correctamente por internet"""
    
    print("="*80)
    print("TEST DE NAVEGACIÓN CON PROXY BRIGHT DATA")
    print("="*80)
    
    user_id = 2  # Usuario de prueba
    logger = setup_logger('TestBrightDataNavegacion')
    
    # Obtener configuración del proxy (primero desde proxy_dev_config.json, luego desde env)
    proxy_config = get_dev_proxy_config(user_id)
    
    # Si no hay config desde JSON, intentar desde variables de entorno
    if not proxy_config:
        host = os.environ.get("DROPI_PROXY_HOST")
        port = os.environ.get("DROPI_PROXY_PORT")
        username = os.environ.get("DROPI_PROXY_USER")
        password = os.environ.get("DROPI_PROXY_PASS")
        
        if host and port:
            proxy_config = {
                "host": host,
                "port": int(port),
                "username": username or "",
                "password": password or ""
            }
            print("\n✅ Proxy cargado desde variables de entorno")
    
    if not proxy_config:
        print("\n❌ ERROR: No se pudo cargar la configuración del proxy")
        print("\nVerifica que:")
        print("  1. DROPTOOLS_ENV=development esté en .env")
        print("  2. backend/proxy_dev_config.json exista")
        print(f"  3. user_id {user_id} esté en la lista de user_ids")
        print("\nO configura variables de entorno:")
        print("  DROPI_PROXY_HOST=brd.superproxy.io")
        print("  DROPI_PROXY_PORT=33335")
        print("  DROPI_PROXY_USER=brd-customer-XXX-zone-isp_proxy1-country-co")
        print("  DROPI_PROXY_PASS=tu_password")
        return False
    
    print(f"\n✅ Proxy configurado:")
    print(f"   Host: {proxy_config['host']}:{proxy_config['port']}")
    print(f"   Usuario: {proxy_config.get('username', 'N/A')[:50]}...")
    print("="*80)
    
    driver = None
    resultados = {
        'ip_check': False,
        'google': False,
        'dropi_login': False
    }
    
    try:
        # Resetear singleton para nueva instancia
        DriverManager.reset_singleton()
        
        print("\n🚀 Inicializando navegador con proxy (MODO VISIBLE)...")
        print("   (Podrás ver todo el proceso en el navegador)")
        
        dm = DriverManager(
            headless=False,  # VISIBLE para ver qué pasa
            logger=logger,
            download_dir=None,
            browser='chrome',  # Chrome funciona bien con Bright Data
            proxy_config=proxy_config,
        )
        
        driver = dm.init_driver(browser_priority=['chrome', 'edge'])
        
        if not driver:
            print("❌ ERROR: No se pudo inicializar el driver")
            return False
        
        print("   ✅ Navegador iniciado")
        print("\n   ⏳ Esperando 3 segundos para que la extensión del proxy se cargue...")
        time.sleep(3)
        
        # ============================================================
        # TEST 1: Verificar IP (acceso a internet)
        # ============================================================
        print("\n" + "="*80)
        print("TEST 1: Verificar acceso a internet (IP del proxy)")
        print("="*80)
        try:
            print("\n📍 Navegando a https://api.ipify.org...")
            driver.get('https://api.ipify.org')
            time.sleep(3)
            
            ip = driver.find_element('tag name', 'body').text.strip()
            if ip:
                print(f"   ✅ IP detectada: {ip}")
                print("   ✅ Proxy funcionando - acceso a internet OK")
                resultados['ip_check'] = True
            else:
                print("   ⚠️ No se pudo obtener IP")
        except Exception as e:
            print(f"   ❌ Error verificando IP: {e}")
        
        # ============================================================
        # TEST 2: Navegar a Google
        # ============================================================
        print("\n" + "="*80)
        print("TEST 2: Navegar a Google")
        print("="*80)
        try:
            print("\n📍 Navegando a https://www.google.com...")
            driver.get('https://www.google.com')
            time.sleep(5)  # Dar tiempo a que cargue
            
            # Verificar que cargó Google (buscar elementos característicos)
            title = driver.title.lower()
            current_url = driver.current_url.lower()
            
            print(f"   Título: {driver.title}")
            print(f"   URL actual: {current_url}")
            
            if 'google' in title or 'google.com' in current_url:
                print("   ✅ Google cargado correctamente")
                resultados['google'] = True
                
                # Intentar buscar el campo de búsqueda
                try:
                    search_box = driver.find_element('name', 'q')
                    if search_box:
                        print("   ✅ Campo de búsqueda encontrado")
                except:
                    print("   ⚠️ Campo de búsqueda no encontrado (puede ser página de consentimiento)")
            else:
                print("   ⚠️ Google puede no haber cargado completamente")
                
        except Exception as e:
            print(f"   ❌ Error navegando a Google: {e}")
            # Guardar captura
            try:
                screenshot_path = Path("results/screenshots/test_google_error.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                driver.save_screenshot(str(screenshot_path))
                print(f"   📸 Captura guardada: {screenshot_path}")
            except:
                pass
        
        # ============================================================
        # TEST 3: Navegar a página de inicio de sesión de Dropi
        # ============================================================
        print("\n" + "="*80)
        print("TEST 3: Navegar a página de inicio de sesión de Dropi")
        print("="*80)
        try:
            print("\n📍 Navegando a https://dropi.co/inicio-de-sesion/...")
            driver.get('https://dropi.co/inicio-de-sesion/')
            time.sleep(5)  # Dar tiempo a que cargue
            
            title = driver.title
            current_url = driver.current_url
            page_source_length = len(driver.page_source)
            
            print(f"   Título: {title}")
            print(f"   URL actual: {current_url}")
            print(f"   Tamaño del HTML: {page_source_length} caracteres")
            
            # Verificar que no es 403 Forbidden
            if '403' in title or 'forbidden' in title.lower():
                print("   ❌ ERROR: 403 Forbidden - Dropi está bloqueando el proxy")
                resultados['dropi_login'] = False
            elif 'dropi' in title.lower() or 'inicio' in title.lower() or 'login' in title.lower():
                print("   ✅ Página de Dropi cargada")
                resultados['dropi_login'] = True
                
                # Intentar encontrar campos de login
                try:
                    # Buscar campos comunes de login
                    email_inputs = driver.find_elements('css selector', 'input[type="email"], input[name*="email"], input[id*="email"]')
                    password_inputs = driver.find_elements('css selector', 'input[type="password"]')
                    
                    if email_inputs or password_inputs:
                        print(f"   ✅ Campos de login encontrados ({len(email_inputs)} email, {len(password_inputs)} password)")
                    else:
                        print("   ⚠️ Campos de login no encontrados (puede ser estructura diferente)")
                except Exception as e:
                    print(f"   ⚠️ Error buscando campos: {e}")
            else:
                print(f"   ⚠️ Página cargada pero título inesperado: {title}")
                resultados['dropi_login'] = page_source_length > 1000  # Si tiene contenido, probablemente OK
            
            # Guardar captura siempre
            try:
                screenshot_path = Path("results/screenshots/test_dropi_login.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                driver.save_screenshot(str(screenshot_path))
                print(f"   📸 Captura guardada: {screenshot_path}")
            except Exception as e:
                print(f"   ⚠️ No se pudo guardar captura: {e}")
                
        except Exception as e:
            print(f"   ❌ Error navegando a Dropi: {e}")
            # Guardar captura del error
            try:
                screenshot_path = Path("results/screenshots/test_dropi_error.png")
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                driver.save_screenshot(str(screenshot_path))
                print(f"   📸 Captura guardada: {screenshot_path}")
            except:
                pass
        
        # ============================================================
        # RESUMEN
        # ============================================================
        print("\n" + "="*80)
        print("RESUMEN DE RESULTADOS")
        print("="*80)
        print(f"✅ Acceso a internet (IP): {'OK' if resultados['ip_check'] else 'FALLÓ'}")
        print(f"✅ Navegación a Google: {'OK' if resultados['google'] else 'FALLÓ'}")
        print(f"✅ Navegación a Dropi login: {'OK' if resultados['dropi_login'] else 'FALLÓ'}")
        
        todos_ok = all(resultados.values())
        if todos_ok:
            print("\n🎉 ¡TODOS LOS TESTS PASARON! El proxy Bright Data funciona correctamente.")
            print("   Puedes proceder a usar el proxy con el reporter.")
        else:
            print("\n⚠️ ALGUNOS TESTS FALLARON. Revisa los logs arriba y las capturas en results/screenshots/")
            if not resultados['ip_check']:
                print("   - Verifica que el proxy esté activo y las credenciales sean correctas")
            if not resultados['google']:
                print("   - Google puede estar bloqueando o el proxy puede tener problemas de conectividad")
            if not resultados['dropi_login']:
                print("   - Dropi puede estar bloqueando el proxy (403) o puede haber problemas de carga")
        
        return todos_ok
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if driver:
            print("\n🔌 Cerrando navegador...")
            try:
                driver.quit()
                print("   ✅ Navegador cerrado")
            except:
                pass

if __name__ == "__main__":
    success = test_navegacion_proxy()
    sys.exit(0 if success else 1)

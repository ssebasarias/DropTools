# 📊 Reporte de Pruebas - Proxy IP Royal para Dropi

## ✅ Resultados de las Pruebas

### Configuración Probada
- **Host:** 201.219.221.147
- **Port:** 12323
- **Username:** 14a9c53d94ce0
- **Password:** f03e2067d5

### Tests Realizados

#### 1. HTTP Simple
- **Estado:** ✅ FUNCIONA
- **IP Verificada:** 201.219.221.147
- **Detalles:** El proxy enmascara correctamente la IP para conexiones HTTP

#### 2. HTTPS con sitios simples (httpbin.org, ipify.org)
- **Estado:** ✅ FUNCIONA
- **Detalles:** Conexiones HTTPS básicas funcionan

#### 3. HTTPS con Dropi (https://dropi.com.co)
- **Estado:** ❌ FALLA
- **Error:** `ERR_TUNNEL_CONNECTION_FAILED`
- **Detalles:** El proxy no puede establecer un túnel HTTPS a Dropi

## 🔍 Diagnóstico

### Problema Identificado
El proxy NO soporta el **método CONNECT** necesario para túneles HTTPS completos.
Esto es común en proxies HTTP básicos o Datacenter proxies económicos.

### Por qué falla con Dropi
1. Dropi usa HTTPS (obligatorio)
2. HTTPS requiere que el proxy establezca un "túnel" (método CONNECT)
3. Este proxy rechaza las peticiones CONNECT con error 502 Bad Gateway

## 💡 Soluciones

### Opción 1: Contactar a IP Royal (RECOMENDADO)

**Qué preguntar:**
```
Hola, necesito que mi proxy soporte túneles HTTPS (método CONNECT) 
para acceder a sitios como dropi.com.co. 

Mi proxy actual (201.219.221.147:12323) funciona para HTTP pero 
falla con "ERR_TUNNEL_CONNECTION_FAILED" al intentar HTTPS.

¿Qué tipo de proxy necesito comprar para tener soporte HTTPS completo?
¿Debo usar geo.iproyal.com en lugar de la IP directa?
```

### Opción 2: Cambiar a Residential Proxies

Según la documentación de IP Royal, los **Residential Proxies** soportan 
HTTPS completo y usan el formato:

```python
proxy = {
    'server': 'http://geo.iproyal.com:12321',  # Puerto estándar residential
    'username': 'TU_USERNAME',
    'password': 'TU_PASSWORD'
}
```

### Opción 3: Verificar tipo de proxy comprado

En tu dashboard de IP Royal, verifica qué tipo de proxy compraste:
- Si dice "Datacenter" → Probablemente no tiene HTTPS completo
- Si dice "Residential" → Deberías usar geo.iproyal.com como servidor
- Si dice "Static Residential" → Deberías tener HTTPS completo

## 📝 Configuración Funcionando (Solo HTTP)

Si solo necesitas HTTP, esta configuración funciona:

```python
# Python requests
proxies = {
    'http': 'http://14a9c53d94ce0:f03e2067d5@201.219.221.147:12323'
}

response = requests.get('http://sitio.com', proxies=proxies)
```

```python
# Playwright
proxy = {
    'server': 'http://201.219.221.147:12323',
    'username': '14a9c53d94ce0',
    'password': 'f03e2067d5'
}

browser = await p.chromium.launch(proxy=proxy)
```

## 🎯 Próximos Pasos

1. **Inmediato:** Contacta a IP Royal con las preguntas arriba
2. **Alternativa:** Si compraste el proxy incorrecto, solicita cambio/actualización
3. **Verificar:** Pide específicamente "residential proxies" con soporte HTTPS
4. **Confirmar:** Que el nuevo proxy use geo.iproyal.com o que soporte CONNECT

## 📧 Template de Email para IP Royal

```
Subject: Proxy no soporta HTTPS - Necesito asistencia

Hola equipo de IP Royal,

Compré un proxy pero tengo problemas para conectarme a sitios HTTPS.

Proxy actual:
- IP: 201.219.221.147
- Puerto: 12323
- Username: 14a9c53d94ce0

Problema:
- HTTP funciona perfectamente
- HTTPS falla con error "ERR_TUNNEL_CONNECTION_FAILED"
- Necesito acceder a https://dropi.com.co

Preguntas:
1. ¿Este proxy soporta el método CONNECT para túneles HTTPS?
2. ¿Debo cambiar a un tipo diferente de proxy?
3. ¿Debo usar geo.iproyal.com en lugar de la IP directa?

Por favor indíquenme qué configuración necesito para acceder 
a sitios HTTPS completos con Playwright/Selenium.

Gracias
```

## 📊 Archivos Generados

Durante las pruebas se generaron estos archivos:
- `dropi_attempt_1.png` - Screenshot de intento 1
- `dropi_attempt_2.png` - Screenshot de intento 2  
- `dropi_attempt_3.png` - Screenshot de intento 3
- `dropi_error_*.png` - Screenshots de errores

## 🔗 Referencias

- [IP Royal Documentation](https://iproyal.com/documentation/)
- [IP Royal Residential Proxies](https://iproyal.com/residential-proxies/)
- [Error ERR_TUNNEL_CONNECTION_FAILED](https://chromiumcodereview.appspot.com/10168007)

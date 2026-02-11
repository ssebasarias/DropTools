# Instrucciones de Diagnóstico - KPIs Usuario 2

Hemos realizado varias mejoras para diagnosticar por qué no aparecen las órdenes reportadas. Por favor sigue estos pasos:

1. **Reinicia el servidor backend**:
   - Detén el comando actual (`Ctrl+C`).
   - Ejecuta de nuevo: `python manage.py runserver`

2. **Abre el Frontend y recarga la página**:
   - Ve a la sección del Reporter.
   - Presiona F5 para recargar.

3. **Revisa la consola del Backend**:
   - Deberías ver logs nuevos que empiezan con `[ReporterStatusView]`.
   - Busca líneas como:
     - `[ReporterStatusView] Usuario: 2 ...`
     - `[ReporterStatusView] total_reported (hoy): ...`
     - `[ReporterStatusView] Enviando response - ...`

4. **Si ves ceros en los logs**:
   - Significa que la base de datos no tiene registros con estado 'reportado' para hoy.
   - Posible causa: El bot guardó con otro estado o fecha.
   - **Solución**: Ejecuta el bot de nuevo para una sola orden y mira los logs que dicen `[ReportResultManager] Guardando OrderReport`. Ahí veremos qué está intentando guardar.

5. **Si ves datos en los logs pero ceros en el Frontend**:
   - Significa que el frontend no está leyendo bien la respuesta.
   - Comprueba la consola del navegador (F12 > Console / Network) para ver qué llegó.

## Qué hemos agregado:
- Logs detallados al consultar el estado.
- Logs detallados al guardar un reporte nuevo.
- Desglose de "conteo por estado" en la respuesta del servidor (visible en logs).
- Lista de las últimas 5 órdenes reportadas (visible en debug).

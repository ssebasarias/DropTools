# Dahell - Guía de Inicio Rápido 🚀

## Estado del Proyecto (V1.2 - Hybrid Core)
El sistema se encuentra operativo con su motor de análisis de competencia de 3ra generación (Híbrido Imagen+Texto).

### Requisitos Previos
- Docker Desktop instalado y corriendo.
- Git.
- Puerto 8000 (Backend) y 5173 (Frontend) libres.

### Pasos para Arrancar

1.  **Clonar y configurar entorno:**
    ```bash
    git clone <repo_url>
    cd Dahell
    # Asegúrate de tener tu archivo .env configurado (ver .env.example)
    ```

2.  **Iniciar Docker (La Manera Fácil):**
    ```powershell
    docker-compose up -d --build
    ```
    *Esto levantará: Base de datos, Backend, Frontend, Scraper, Vectorizer y Clusterizer.*

3.  **Acceder a la Plataforma:**
    - **Frontend (Gold Mine):** [http://localhost:5173](http://localhost:5173)
    - **Backend API:** [http://localhost:8000/api/](http://localhost:8000/api/)
    - **Cluster Lab (Auditoría):** [http://localhost:5173/cluster-lab](http://localhost:5173/cluster-lab)
    - **PgAdmin (DB):** [http://localhost:5050](http://localhost:5050)

### Solución de Problemas Comunes

*   **"No veo datos en Gold Mine":**
    *   Asegúrate de que el `clusterizer` haya terminado su ciclo inicial. Revisa los logs:
        `docker logs -f dahell-clusterizer-1`
*   **"La distribución de competidores se ve rara":**
    *   El sistema aprende progresivamente. Si acabas de reiniciar, dale 10-15 minutos para que la IA procese las nuevas uniones con la lógica híbrida.
*   **Error de conexión DB:**
    *   Verifica que el contenedor `dahell_db` esté en estado `Up`.

### Comandos Útiles de Desarrollo

| Acción | Comando |
| :--- | :--- |
| **Ver logs del Clusterizer** | `docker logs -f dahell-clusterizer-1` |
| **Reiniciar Backend** | `docker restart dahell_backend` |
| **Auditar decisiones IA** | `tail -f logs/cluster_audit.jsonl` |
| **Detener todo** | `docker-compose down` |

---
**Recuerda:** Este sistema utiliza modelos de IA pesados (CLIP). Asegúrate de asignar al menos 4GB de RAM a Docker Desktop para un rendimiento fluido.

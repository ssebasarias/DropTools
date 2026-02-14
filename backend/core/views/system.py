# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..docker_utils import get_container_stats, control_container, get_docker_logs
from ..permissions import IsAdminRole


class HealthView(APIView):
    """Endpoint para healthcheck (Docker, load balancers). Sin autenticación."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class SystemLogsView(APIView):
    permission_classes = [IsAdminRole]
    
    def get(self, request):
        """
        Retorna logs directamente desde Docker (Paralelizado).
        Devuelve Diccionario: { "scraper": [line1, line2...], ... }
        """
        # Mapeo Service ID -> Container Name
        services = {
            "scraper": "droptools_scraper",
            "loader": "droptools_loader",
            "vectorizer": "droptools_vectorizer",
            "classifier": "droptools_classifier",
            "classifier_2": "droptools_classifier_2",
            "clusterizer": "droptools_clusterizer",
            "shopify_auditor": "droptools_shopify_auditor",
            "market_trender": "droptools_market_trender",
            "meta_scholar": "droptools_meta_scholar",
            "celery_worker": "droptools_celery_worker",
        }
        
        results = {}

        def fetch_logs(service_id, container_name):
            try:
                raw_lines = get_docker_logs(container_name, tail=50)
                return service_id, [{"message": l, "service": service_id} for l in raw_lines]
            except Exception as e:
                return service_id, [{"message": f"Error fetching logs: {str(e)}", "service": service_id}]

        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            future_map = {
                executor.submit(fetch_logs, s_id, c_name): s_id 
                for s_id, c_name in services.items()
            }
            
            for future in as_completed(future_map):
                s_id, logs = future.result()
                results[s_id] = logs
        
        return Response(results)


class ContainerStatsView(APIView):
    permission_classes = [IsAdminRole]
    
    def get(self, request):
        """
        Retorna estado robusto de los contenedores (CPU, RAM, Status).
        """
        containers = {
            "scraper": "droptools_scraper",
            "loader": "droptools_loader",
            "vectorizer": "droptools_vectorizer",
            "classifier": "droptools_classifier",
            "classifier_2": "droptools_classifier_2",
            "clusterizer": "droptools_clusterizer",
            "market_trender": "droptools_market_trender",
            "meta_scholar": "droptools_meta_scholar",
            "shopify_auditor": "droptools_shopify_auditor",
            "celery_worker": "droptools_celery_worker",
            "db": "droptools_db"
        }
        
        data = {}
        for friendly_name, c_name in containers.items():
            data[friendly_name] = get_container_stats(c_name)
            
        return Response(data)


class ContainerControlView(APIView):
    permission_classes = [IsAdminRole]
    
    def post(self, request, service, action):
        """
        Controla encendido/apagado de servicios.
        URL: /api/control/container/<service>/<action>
        """
        # Map logical service ids -> container names
        mapping = {
            "scraper": ["droptools_scraper"],
            "loader": ["droptools_loader"],
            "vectorizer": ["droptools_vectorizer"],
            # For 'classifier' we intentionally map to BOTH classifier containers
            "classifier": ["droptools_classifier", "droptools_classifier_2"],
            "clusterizer": ["droptools_clusterizer"],
            "market_trender": ["droptools_market_trender"],
            "meta_scholar": ["droptools_meta_scholar"],
            "shopify_auditor": ["droptools_shopify_auditor"],
            "celery_worker": ["droptools_celery_worker"]
        }

        container_names = mapping.get(service)
        if not container_names:
            return Response({"error": "Invalid service"}, status=400)

        results = {}
        any_success = False
        for c_name in container_names:
            success, msg = control_container(c_name, action)
            results[c_name] = {"success": success, "message": msg}
            any_success = any_success or success

        if any_success:
            return Response({"status": "ok", "results": results})
        else:
            # If none of the requested actions succeeded, return error with details
            return Response({"error": "All actions failed", "results": results}, status=500)

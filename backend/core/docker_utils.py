
import docker
import logging
import threading
import time

logger = logging.getLogger(__name__)

# --- GLOBAL ASYNC CACHE ---
# Structure: { "container_name": { "status": "running", "cpu": 1.2, ... } }
# Initial state: Empty, filled by background thread
STATS_CACHE = {}
CACHE_LOCK = threading.Lock()

# Configuration
MONITORING_INTERVAL = 3  # Seconds between updates
CONTAINERS_TO_MONITOR = [
    "dahell_scraper", 
    "dahell_shopify",  # Changed from dahell_market_agent / dahell_amazon_explorer
    "dahell_loader", 
    "dahell_vectorizer", 
    "dahell_classifier",
    "dahell_clusterizer", 
    "dahell_ai_trainer",
    "dahell_celery_worker",
    "dahell_db"
]

_docker_error_logged = False

def get_docker_client():
    global _docker_error_logged
    try:
        c = docker.from_env(timeout=10)
        if _docker_error_logged:
            logger.info("✅ Docker connection re-established.")
            _docker_error_logged = False
        return c
    except Exception as e:
        if not _docker_error_logged:
            logger.error(f"Error connecting to Docker: {e} (Will suppress further errors until fixed)")
            _docker_error_logged = True
        return None

def _fetch_single_container_stats(client, container_name):
    """
    Internal helper to fetch stats for one container.
    """
    result = {"status": "error", "cpu": 0, "ram_mb": 0, "ram_percent": 0}
    try:
        try:
            container = client.containers.get(container_name)
            result["status"] = container.status
        except docker.errors.NotFound:
             result["status"] = "not_found"
             return result

        if result["status"] == 'running':
            try:
                # stream=False is critical to avoid blocking forever
                stats = container.stats(stream=False)
                
                # CPU Calculation
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                number_cpus = stats['cpu_stats'].get('online_cpus', 1)
                
                cpu_pct = 0.0
                if system_cpu_delta > 0.0 and cpu_delta > 0.0:
                    cpu_pct = (cpu_delta / system_cpu_delta) * number_cpus * 100.0

                # Memory Calculation
                usage = stats['memory_stats'].get('usage', 0)
                limit = stats['memory_stats'].get('limit', 1)
                cache = stats['memory_stats'].get('stats', {}).get('cache', 0)
                used_mem = usage - cache
                
                result["cpu"] = round(cpu_pct, 1)
                result["ram_mb"] = int(used_mem / (1024 * 1024))
                result["ram_percent"] = round((used_mem / limit) * 100.0, 1)
                
            except Exception:
                # If stats fail but container is running (e.g. starting up), 
                # keep status=running/starting but 0 metrics to avoid UI flickering to "error"
                result["cpu"] = 0
                result["ram_mb"] = 0
                result["ram_percent"] = 0
                # result["status"] is already 'running' from line 49

    except Exception as e:
        logger.warning(f"Error monitoring {container_name}: {e}")
        # If completely failed (e.g. timeout), default to error
        result["status"] = "error"
    
    return result

def monitoring_loop():
    """
    Background Daemon that updates STATS_CACHE forever.
    """
    logger.info("📡 Docker Monitoring Thread Started")
    while True:
        client = get_docker_client()
        if client:
            new_stats = {}
            for c_name in CONTAINERS_TO_MONITOR:
                new_stats[c_name] = _fetch_single_container_stats(client, c_name)
            
            client.close()
            
            # Atomic Update
            with CACHE_LOCK:
                STATS_CACHE.update(new_stats)
        
        time.sleep(MONITORING_INTERVAL)

def start_monitoring_thread():
    """
    Called by AppConfig.ready() to start the background worker.
    """
    t = threading.Thread(target=monitoring_loop, daemon=True)
    t.start()

def get_container_stats(container_name):
    """
    Non-blocking retrieval from cache.
    Returns 0/Stopped if cache is empty (system starting up).
    """
    with CACHE_LOCK:
        return STATS_CACHE.get(container_name, {
            "status": "loading...", 
            "cpu": 0, 
            "ram_mb": 0, 
            "ram_percent": 0
        })

def control_container(container_name, action):
    """
    Direct control (Blocking is fine here as it's a user action).
    """
    client = get_docker_client()
    if not client: return False, "Docker unreachable"
    
    try:
        container = client.containers.get(container_name)
        if action == "start": container.start()
        elif action == "stop": container.stop()
        elif action == "restart": container.restart()
        else: return False, "Invalid action"
        
        # Immediate cache update for responsiveness
        with CACHE_LOCK:
            if container_name in STATS_CACHE:
                STATS_CACHE[container_name]["status"] = "updating..."
                
        return True, f"Action {action} executed"
    except Exception as e:
        # Better error handling for already stopped/started containers
        if "No such container" in str(e):
             return False, "Container not found"
        return False, str(e)

# NEW: Helper to get logs directly from Docker (No files)
def get_docker_logs(container_name, tail=50):
    client = get_docker_client()
    if not client: return []
    
    try:
        container = client.containers.get(container_name)
        # Get logs as bytes
        raw_logs = container.logs(tail=tail, stderr=True, stdout=True)
        # Decode and split
        decoded = raw_logs.decode('utf-8', errors='replace').splitlines()
        return [line for line in decoded if line.strip()]
    except Exception as e:
        logger.warning(f"Error fetching logs for {container_name}: {e}")
        return []

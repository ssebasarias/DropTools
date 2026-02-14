import React from "react";
import { Database, Server, Activity, Cpu } from "lucide-react";
import UnifiedWorkerCard from "../components/domain/system/UnifiedWorkerCard";
import ServiceCard from "../components/domain/system/ServiceCard";
import { useSystemStatus } from "../hooks/useSystemStatus";

const servicesConfig = [
  { id: "backend", name: "Backend API", icon: Server, actions: ["restart"] },
  { id: "db", name: "PostgreSQL", icon: Database },
  { id: "redis", name: "Redis", icon: Activity },
  { id: "celery_worker", name: "Celery Worker", icon: Cpu, actions: ["restart"] },
];

const workersConfig = [
  { id: "scraper", name: "Scraper", icon: Activity, color: "#38bdf8" },
  { id: "loader", name: "Loader", icon: Activity, color: "#22c55e" },
  { id: "vectorizer", name: "Vectorizer", icon: Activity, color: "#a78bfa" },
  { id: "clusterizer", name: "Clusterizer", icon: Activity, color: "#f59e0b" },
  { id: "classifier", name: "Classifier", icon: Activity, color: "#f97316" },
  { id: "classifier_2", name: "Classifier 2", icon: Activity, color: "#ef4444" },
  { id: "market_trender", name: "Market Trender", icon: Activity, color: "#14b8a6" },
  { id: "meta_scholar", name: "Meta Scholar", icon: Activity, color: "#ec4899" },
  { id: "shopify_auditor", name: "Shopify Auditor", icon: Activity, color: "#84cc16" },
];

export default function SystemStatus() {
  const { logs, stats, loading } = useSystemStatus();

  if (loading) {
    return (
      <div className="glass-card" style={{ padding: "1.5rem", color: "#94a3b8" }}>
        Cargando estado del sistema...
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <section className="glass-card" style={{ padding: "1.25rem" }}>
        <h3 style={{ margin: 0, color: "#e2e8f0" }}>Core Services</h3>
        <p style={{ margin: "0.5rem 0 1rem", color: "#94a3b8" }}>
          Estado operativo de servicios base y controles rápidos.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1rem",
          }}
        >
          {servicesConfig.map((svc) => (
            <ServiceCard
              key={svc.id}
              id={svc.id}
              name={svc.name}
              icon={svc.icon}
              actions={svc.actions || []}
              displayParams={stats?.[svc.id] || { status: "unknown", cpu: 0, ram_mb: 0 }}
            />
          ))}
        </div>
      </section>

      <section className="glass-card" style={{ padding: "1.25rem" }}>
        <h3 style={{ margin: 0, color: "#e2e8f0" }}>Workers 24/7</h3>
        <p style={{ margin: "0.5rem 0 1rem", color: "#94a3b8" }}>
          Monitoreo en vivo y terminal embebida por worker.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: "1rem",
          }}
        >
          {workersConfig.map((worker) => (
            <UnifiedWorkerCard
              key={worker.id}
              id={worker.id}
              name={worker.name}
              icon={worker.icon}
              color={worker.color}
              logs={logs || {}}
              actions={["restart"]}
              displayParams={stats?.[worker.id] || { status: "unknown", cpu: 0, ram_mb: 0 }}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

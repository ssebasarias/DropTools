import React, { useEffect, useMemo, useState } from "react";
import { RefreshCw, Save } from "lucide-react";
import { fetchAdminUsers, setUserSubscription } from "../../../services/adminService";

const TIERS = ["BRONZE", "SILVER", "GOLD", "PLATINUM"];

export default function AdminUsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState({});
  const [filter, setFilter] = useState("");

  const load = async () => {
    setError("");
    setLoading(true);
    try {
      const list = await fetchAdminUsers();
      setUsers(list);
    } catch (e) {
      setError(e.message || "Error cargando usuarios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) => (u.email || u.username || "").toLowerCase().includes(q));
  }, [users, filter]);

  return (
    <div className="glass-card fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <h3 style={{ marginBottom: "0.25rem", fontSize: "1.25rem", fontWeight: 600 }}>Admin: Users & Subscriptions</h3>
          <p className="text-muted" style={{ margin: 0 }}>
            Cambia tier y activa/desactiva suscripción (sin pagos).
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <input
            className="glass-input"
            placeholder="Buscar por email..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ width: 240 }}
          />
          <button className="btn-secondary" onClick={load} disabled={loading} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {error && <div style={{ marginTop: "1rem", color: "#ef4444" }}>{error}</div>}

      <div style={{ marginTop: "1.5rem", overflowX: "auto" }}>
        {loading ? (
          <div className="text-muted">Cargando...</div>
        ) : (
          <table className="glass-table" style={{ minWidth: 900 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Role</th>
                <th>Tier</th>
                <th>Active</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <AdminUserRow
                  key={u.id}
                  u={u}
                  saving={!!saving[u.id]}
                  onSave={async (payload) => {
                    setSaving((s) => ({ ...s, [u.id]: true }));
                    try {
                      await setUserSubscription(u.id, payload);
                      await load();
                    } catch (e) {
                      setError(e.message || "Error actualizando");
                    } finally {
                      setSaving((s) => ({ ...s, [u.id]: false }));
                    }
                  }}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function AdminUserRow({ u, saving, onSave }) {
  const p = u.profile || {};
  const [tier, setTier] = useState(p.subscription_tier || "BRONZE");
  const [active, setActive] = useState(!!p.subscription_active);

  useEffect(() => {
    setTier(p.subscription_tier || "BRONZE");
    setActive(!!p.subscription_active);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [u.id]);

  const isAdmin = p.role === "ADMIN";

  return (
    <tr>
      <td>{u.id}</td>
      <td>{u.email || u.username}</td>
      <td>{p.role || "CLIENT"}</td>
      <td>
        <select className="glass-select" value={tier} onChange={(e) => setTier(e.target.value)} disabled={saving || isAdmin}>
          {TIERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </td>
      <td>
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} disabled={saving || isAdmin} />
      </td>
      <td>
        <button
          className="btn-primary"
          disabled={saving || isAdmin}
          onClick={() => onSave({ subscription_tier: tier, subscription_active: active })}
          style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
        >
          <Save size={16} /> Save
        </button>
        {isAdmin && <span className="text-muted" style={{ marginLeft: "0.75rem" }}>ADMIN locked</span>}
      </td>
    </tr>
  );
}


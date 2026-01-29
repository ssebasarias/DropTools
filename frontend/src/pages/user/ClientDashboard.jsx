import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Package,
    XCircle,
    CheckCircle,
    Truck,
    MapPin,
    BarChart3,
    Zap,
    DollarSign,
} from 'lucide-react';
import { fetchClientDashboardAnalytics } from '../../services/api';
import GlassCard from '../../components/common/GlassCard';
import ErrorState from '../../components/common/ErrorState';
import EmptyState from '../../components/common/EmptyState';
import ColombiaMap from '../../components/domain/market/ColombiaMap';

const timeFilters = [
    { value: 'day', label: 'Día' },
    { value: 'week', label: 'Semana' },
    { value: 'fortnight', label: 'Quincena' },
    { value: 'month', label: 'Mes' },
];

function formatCurrency(value) {
    if (value == null || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
}

function formatNumber(value) {
    if (value == null || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 }).format(value);
}

const ClientDashboard = () => {
    const navigate = useNavigate();
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [timeFilter, setTimeFilter] = useState('week');

    const loadAnalytics = useCallback(async () => {
        setError(null);
        try {
            const data = await fetchClientDashboardAnalytics(timeFilter);
            setAnalytics(data);
        } catch (err) {
            setError(err?.message || 'Error al cargar los datos del dashboard');
        } finally {
            setLoading(false);
        }
    }, [timeFilter]);

    useEffect(() => {
        setLoading(true);
        loadAnalytics();
    }, [loadAnalytics]);

    if (error) {
        return (
            <ErrorState
                error={error}
                onRetry={loadAnalytics}
                title="Error al cargar datos"
            />
        );
    }

    if (loading && !analytics) {
        return (
            <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh' }}>
                <Zap className="spin" size={48} style={{ color: 'var(--primary)' }} />
                <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Cargando analytics...</p>
                <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    const hasData = analytics?.kpis?.total_orders > 0;
    if (!hasData) {
        return (
            <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto' }}>
                <EmptyState
                    icon={BarChart3}
                    title="Aún no hay reportes"
                    description="Los datos del dashboard se generan a partir de los reportes de Dropi. Ejecuta el reporter para cargar datos."
                    action={{
                        label: 'Ir a configuración del Reporter',
                        onClick: () => navigate('/user/reporter-setup'),
                    }}
                />
            </div>
        );
    }

    const { kpis, by_region, top_products, by_carrier, last_updated } = analytics;
    const topProduct = top_products?.[0] ?? null;
    const carrierEffectivenessPct = by_carrier?.length
        ? (by_carrier.reduce((acc, c) => acc + c.delivered, 0) / by_carrier.reduce((acc, c) => acc + c.total, 0) * 100).toFixed(1)
        : 0;

    return (
        <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Dashboard</h1>
                    <p className="text-muted" style={{ marginTop: '0.5rem' }}>Análisis de rendimiento y estadísticas de tu negocio</p>
                    {last_updated && (
                        <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                            Datos del reporte: {new Date(last_updated).toLocaleDateString('es-CO', { dateStyle: 'medium' })}
                        </p>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--glass-bg)', padding: '0.5rem', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                    {timeFilters.map((filter) => (
                        <button
                            key={filter.value}
                            onClick={() => setTimeFilter(filter.value)}
                            style={{
                                padding: '0.5rem 1rem',
                                borderRadius: '8px',
                                background: timeFilter === filter.value ? 'linear-gradient(135deg, var(--primary), #4f46e5)' : 'transparent',
                                color: timeFilter === filter.value ? 'white' : 'var(--text-muted)',
                                border: 'none',
                                cursor: 'pointer',
                                fontWeight: timeFilter === filter.value ? 600 : 400,
                                transition: 'all 0.2s',
                            }}
                        >
                            {filter.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* KPIs */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Total pedidos</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                            <Package size={20} style={{ color: 'var(--primary)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.total_orders)}</h2>
                </GlassCard>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Entregados</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(16,185,129,0.2)', borderRadius: '12px' }}>
                            <CheckCircle size={20} style={{ color: 'var(--success)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.delivered)}</h2>
                </GlassCard>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Productos vendidos</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                            <Package size={20} style={{ color: 'var(--primary)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.products_sold)}</h2>
                </GlassCard>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Ingresos totales</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(16,185,129,0.2)', borderRadius: '12px' }}>
                            <DollarSign size={20} style={{ color: 'var(--success)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 'bold', wordBreak: 'break-all' }}>{formatCurrency(kpis.total_revenue)}</h2>
                </GlassCard>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Confirmación</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(16,185,129,0.2)', borderRadius: '12px' }}>
                            <CheckCircle size={20} style={{ color: 'var(--success)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>{kpis.confirmation_pct}%</h2>
                </GlassCard>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Cancelación</p>
                        <div style={{ padding: '0.5rem', background: 'rgba(239,68,68,0.2)', borderRadius: '12px' }}>
                            <XCircle size={20} style={{ color: 'var(--danger)' }} />
                        </div>
                    </div>
                    <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--danger)' }}>{kpis.cancellation_pct}%</h2>
                </GlassCard>
            </div>

            {/* Producto más vendido + Mapa por departamento */}
            <div className="dashboard-two-col" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ padding: '0.75rem', background: 'rgba(245,158,11,0.2)', borderRadius: '12px' }}>
                            <Package size={24} style={{ color: 'var(--warning)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Producto más vendido</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>Más vendido del período</p>
                        </div>
                    </div>
                    {topProduct ? (
                        <>
                            <h4 style={{ fontSize: '1rem', marginBottom: '0.5rem', wordBreak: 'break-word' }}>
                                {topProduct.product_name.length > 60 ? `${topProduct.product_name.slice(0, 60)}…` : topProduct.product_name}
                            </h4>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
                                <div>
                                    <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>Unidades</p>
                                    <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{formatNumber(topProduct.quantity)}</p>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>Facturación</p>
                                    <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{formatCurrency(topProduct.revenue)}</p>
                                </div>
                            </div>
                        </>
                    ) : (
                        <p className="text-muted" style={{ margin: 0 }}>Sin datos</p>
                    )}
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ padding: '0.75rem', background: 'rgba(16,185,129,0.2)', borderRadius: '12px' }}>
                            <MapPin size={24} style={{ color: 'var(--success)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Zonas que más compran</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>Por departamento — clic en zona para ver pedidos y facturación</p>
                        </div>
                    </div>
                    <ColombiaMap byRegion={by_region} style={{ minHeight: '320px' }} />
                    {by_region?.length > 0 && (
                        <ul style={{ margin: '1rem 0 0', paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1rem' }}>
                            {by_region.slice(0, 6).map((r, i) => (
                                <li key={i}>
                                    <strong style={{ color: 'var(--text-main)' }}>{r.department}</strong>: {formatNumber(r.orders)} pedidos — {formatCurrency(r.revenue)}
                                </li>
                            ))}
                        </ul>
                    )}
                </GlassCard>
            </div>

            {/* Efectividad transportadoras */}
            <GlassCard style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                    <div style={{ padding: '0.75rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                        <Truck size={24} style={{ color: 'var(--primary)' }} />
                    </div>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Efectividad por transportadora</h3>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>Entregados / total — Global: {carrierEffectivenessPct}%</p>
                    </div>
                </div>
                {by_carrier?.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
                                    <th style={{ textAlign: 'left', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Transportadora</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Envíos</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Entregados</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>% Efectividad</th>
                                </tr>
                            </thead>
                            <tbody>
                                {by_carrier.map((c, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '0.75rem', color: 'var(--text-main)' }}>{c.carrier}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(c.total)}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(c.delivered)}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right', color: c.effectiveness_pct >= 80 ? 'var(--success)' : 'var(--text-muted)' }}>{c.effectiveness_pct}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-muted" style={{ margin: 0 }}>Sin datos de transportadoras</p>
                )}
            </GlassCard>

            {/* Top productos */}
            <GlassCard>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                    <div style={{ padding: '0.75rem', background: 'rgba(245,158,11,0.2)', borderRadius: '12px' }}>
                        <BarChart3 size={24} style={{ color: 'var(--warning)' }} />
                    </div>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Top productos</h3>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>Por unidades vendidas</p>
                    </div>
                </div>
                {top_products?.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
                                    <th style={{ textAlign: 'left', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Producto</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Unidades</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Facturación</th>
                                </tr>
                            </thead>
                            <tbody>
                                {top_products.map((p, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '0.75rem', color: 'var(--text-main)', maxWidth: '320px' }} title={p.product_name}>
                                            {(p.product_name || '').length > 50 ? `${(p.product_name || '').slice(0, 50)}…` : (p.product_name || '—')}
                                        </td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(p.quantity)}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatCurrency(p.revenue)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-muted" style={{ margin: 0 }}>Sin datos de productos</p>
                )}
            </GlassCard>

            <style>{`
                .text-gradient {
                    background: linear-gradient(to right, #fff, #94a3b8);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                @media (max-width: 900px) {
                    .dashboard-two-col {
                        grid-template-columns: 1fr !important;
                    }
                }
            `}</style>
        </div>
    );
};

export default ClientDashboard;

import React, { useEffect, useState, useCallback } from 'react';
import {
    Package,
    XCircle,
    CheckCircle,
    Truck,
    MapPin,
    BarChart3,
    Zap,
    DollarSign,
    TrendingUp,
    TrendingDown,
    AlertCircle,
    Download,
    RefreshCw,
} from 'lucide-react';
import { fetchClientDashboardAnalytics, fetchCarrierComparison, exportAnalyticsReport, startReporterWorkflow } from '../../services/api';
import GlassCard from '../../components/common/GlassCard';
import ErrorState from '../../components/common/ErrorState';
import ColombiaMap from '../../components/domain/market/ColombiaMap';

const dashboardModes = [
    { value: 'day', label: 'Hoy', description: 'Reportes del día' },
    { value: 'week', label: 'Semana', description: 'Última semana' },
    { value: 'fortnight', label: 'Quincena', description: 'Última quincena' },
    { value: 'month', label: 'Histórico', description: 'Último año' },
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

function formatPercent(value) {
    if (value == null || Number.isNaN(value)) return '—';
    return `${value.toFixed(1)}%`;
}

const AnalyticsDashboard = () => {
    const [analytics, setAnalytics] = useState(null);
    const [carrierComparison, setCarrierComparison] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [timeFilter, setTimeFilter] = useState('month');
    const [exporting, setExporting] = useState(false);
    const [syncingSnapshots, setSyncingSnapshots] = useState(false);
    const [syncMessage, setSyncMessage] = useState(null);

    const loadAnalytics = useCallback(async () => {
        setError(null);
        setLoading(true);
        try {
            const [analyticsData, comparisonData] = await Promise.all([
                fetchClientDashboardAnalytics(timeFilter),
                fetchCarrierComparison(timeFilter),
            ]);
            
            if (analyticsData && typeof analyticsData.error === 'string') {
                throw new Error(analyticsData.error);
            }
            
            setAnalytics(analyticsData);
            setCarrierComparison(comparisonData);
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

    // Auto-refresh cada 30 segundos cuando está en "Hoy"
    useEffect(() => {
        if (timeFilter === 'day' && analytics) {
            const interval = setInterval(() => {
                loadAnalytics();
            }, 30000);
            return () => clearInterval(interval);
        }
    }, [timeFilter, analytics, loadAnalytics]);

    const handleExport = async () => {
        setExporting(true);
        try {
            await exportAnalyticsReport(timeFilter, 'csv');
        } catch (err) {
            console.error('Error exportando:', err);
            alert('Error al exportar el reporte');
        } finally {
            setExporting(false);
        }
    };

    const handleSyncSnapshots = async () => {
        setSyncMessage(null);
        setSyncingSnapshots(true);
        try {
            await startReporterWorkflow();
            setSyncMessage('Sincronización iniciada. El proceso puede tardar unos minutos; luego actualiza este dashboard.');
            setTimeout(() => {
                loadAnalytics();
            }, 3000);
        } catch (err) {
            setSyncMessage(err?.message || 'No se pudo iniciar la sincronización automática.');
        } finally {
            setSyncingSnapshots(false);
        }
    };

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

    const periodLabel = analytics?.period_label || (timeFilter === 'day' ? 'Hoy' : 'Histórico (último año)');

    const {
        kpis = {},
        finances_general = {},
        finances_real = {},
        performance_metrics = {},
        status_breakdown = [],
        by_region = [],
        top_products = [],
        by_carrier = [],
        product_profitability = [],
        carrier_reports = [],
        last_updated,
        data_message,
        snapshot_sync_recommended,
    } = analytics || {};
    const topProduct = top_products?.[0] ?? null;

    return (
        <div style={{ padding: '2rem', maxWidth: '1800px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Dashboard Analítico</h1>
                    <p className="text-muted" style={{ marginTop: '0.5rem' }}>Análisis completo de rendimiento, finanzas y métricas de negocio</p>
                    <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Mostrando: {periodLabel}</span>
                        {last_updated && (
                            <span> · Datos del reporte: {new Date(last_updated).toLocaleDateString('es-CO', { dateStyle: 'medium' })}</span>
                        )}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--glass-bg)', padding: '0.5rem', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                        {dashboardModes.map((mode) => (
                            <button
                                key={mode.value}
                                onClick={() => setTimeFilter(mode.value)}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '8px',
                                    background: timeFilter === mode.value ? 'linear-gradient(135deg, var(--primary), #4f46e5)' : 'transparent',
                                    color: timeFilter === mode.value ? 'white' : 'var(--text-muted)',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontWeight: timeFilter === mode.value ? 600 : 400,
                                    transition: 'all 0.2s',
                                }}
                                title={mode.description}
                            >
                                {mode.label}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={handleExport}
                        disabled={exporting}
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            background: 'rgba(99, 102, 241, 0.2)',
                            color: 'var(--primary)',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            cursor: exporting ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                        }}
                    >
                        <Download size={16} />
                        {exporting ? 'Exportando...' : 'Exportar'}
                    </button>
                    <button
                        onClick={loadAnalytics}
                        style={{
                            padding: '0.5rem',
                            borderRadius: '8px',
                            background: 'rgba(99, 102, 241, 0.2)',
                            color: 'var(--primary)',
                            border: '1px solid rgba(99, 102, 241, 0.3)',
                            cursor: 'pointer',
                        }}
                        title="Actualizar datos"
                    >
                        <RefreshCw size={16} />
                    </button>
                </div>
            </div>
            {data_message && (
                <GlassCard style={{ marginBottom: '1.5rem', border: '1px dashed rgba(245, 158, 11, 0.35)' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                        <p className="text-muted" style={{ margin: 0 }}>
                            {data_message}
                        </p>
                        {snapshot_sync_recommended ? (
                            <button
                                onClick={handleSyncSnapshots}
                                disabled={syncingSnapshots}
                                style={{
                                    padding: '0.5rem 0.9rem',
                                    borderRadius: '8px',
                                    background: 'rgba(99, 102, 241, 0.2)',
                                    color: 'var(--primary)',
                                    border: '1px solid rgba(99, 102, 241, 0.35)',
                                    cursor: syncingSnapshots ? 'not-allowed' : 'pointer',
                                    fontWeight: 600,
                                }}
                            >
                                {syncingSnapshots ? 'Sincronizando...' : 'Sincronizar datos para mapa y finanzas'}
                            </button>
                        ) : null}
                    </div>
                    {syncMessage ? (
                        <p className="text-muted" style={{ margin: '0.65rem 0 0' }}>
                            {syncMessage}
                        </p>
                    ) : null}
                </GlassCard>
            )}

            {/* Sección 1: KPIs Principales */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <BarChart3 size={24} style={{ color: 'var(--primary)' }} />
                    KPIs Principales
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Total Pedidos</p>
                            <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                                <Package size={20} style={{ color: 'var(--primary)' }} />
                            </div>
                        </div>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.total_orders)}</h2>
                    </GlassCard>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Total Guías</p>
                            <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                                <Package size={20} style={{ color: 'var(--primary)' }} />
                            </div>
                        </div>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.total_guides)}</h2>
                    </GlassCard>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Productos</p>
                            <div style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.2)', borderRadius: '12px' }}>
                                <Package size={20} style={{ color: 'var(--primary)' }} />
                            </div>
                        </div>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>{formatNumber(kpis.products_sold)}</h2>
                    </GlassCard>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Confirmación</p>
                            <div style={{ padding: '0.5rem', background: 'rgba(16,185,129,0.2)', borderRadius: '12px' }}>
                                <CheckCircle size={20} style={{ color: 'var(--success)' }} />
                            </div>
                        </div>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                            {formatPercent(kpis.confirmation_pct)}
                        </h2>
                    </GlassCard>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>Cancelación</p>
                            <div style={{ padding: '0.5rem', background: 'rgba(239,68,68,0.2)', borderRadius: '12px' }}>
                                <XCircle size={20} style={{ color: 'var(--danger)' }} />
                            </div>
                        </div>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--danger)' }}>
                            {formatPercent(kpis.cancellation_pct)}
                        </h2>
                    </GlassCard>
                </div>
            </div>

            {/* Sección 2: Finanzas Generales */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <DollarSign size={24} style={{ color: 'var(--primary)' }} />
                    $ Finanzas Generales
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Valor Total</p>
                        <h2 style={{ fontSize: '1.5rem', margin: 0, fontWeight: 'bold' }}>
                            {formatCurrency(finances_general.total_value)}
                        </h2>
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Estado Proyectado</p>
                        <h2 style={{ fontSize: '1.5rem', margin: 0, fontWeight: 'bold' }}>
                            {formatCurrency(finances_general.projected_revenue)}
                        </h2>
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Valoración Recuperada</p>
                        <h2 style={{ fontSize: '1.5rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                            {formatCurrency(finances_general.recovered_valuation)}
                        </h2>
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Utilidad Proyectada (BPS)</p>
                        <h2 style={{ fontSize: '1.5rem', margin: 0, fontWeight: 'bold' }}>
                            {formatCurrency(finances_general.projected_profit_bps)}
                        </h2>
                    </GlassCard>
                </div>
            </div>

            {/* Sección 3: Finanzas Reales (Entregados) */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <TrendingUp size={24} style={{ color: 'var(--success)' }} />
                    $ Finanzas Reales (Entregados)
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Ventas Entregadas</p>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>
                            {formatCurrency(finances_real.delivered_revenue)}
                        </h2>
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Ganancia Neta Real</p>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                            {formatCurrency(finances_real.net_profit_real)}
                        </h2>
                        <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--success)' }}>
                            <TrendingUp size={14} />
                            <span style={{ fontSize: '0.85rem' }}>Ganancia real</span>
                        </div>
                    </GlassCard>
                </div>
            </div>

            {/* Sección 4: Métricas de Rendimiento */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <BarChart3 size={24} style={{ color: 'var(--primary)' }} />
                    Métricas de Rendimiento
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Efectividad Entrega</p>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                            {formatPercent(performance_metrics.delivery_effectiveness_pct)}
                        </h2>
                        <CheckCircle size={16} style={{ color: 'var(--success)', marginTop: '0.5rem' }} />
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Devoluciones Global</p>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold' }}>
                            {formatPercent(performance_metrics.global_returns_pct)}
                        </h2>
                        <Truck size={16} style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }} />
                    </GlassCard>
                    <GlassCard>
                        <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Anulación</p>
                        <h2 style={{ fontSize: '1.75rem', margin: 0, fontWeight: 'bold', color: 'var(--danger)' }}>
                            {formatPercent(performance_metrics.annulation_pct)}
                        </h2>
                        <AlertCircle size={16} style={{ color: 'var(--danger)', marginTop: '0.5rem' }} />
                    </GlassCard>
                </div>

                {/* Desglose por Estado */}
                <GlassCard>
                    <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Desglose por Estado</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                        {status_breakdown.map((status, idx) => (
                            <div key={idx} style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                                <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>{status.status}</p>
                                <p style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0 }}>{formatNumber(status.orders_count)}</p>
                                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '0.25rem', margin: 0 }}>
                                    {formatCurrency(status.total_value)}
                                </p>
                            </div>
                        ))}
                    </div>
                </GlassCard>
            </div>

            {/* Zonas que más compran (por región) */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <MapPin size={24} style={{ color: 'var(--success)' }} />
                    Zonas que más compran
                </h2>
                <GlassCard>
                    <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
                        Colombia por departamento - clic en zona para ver pedidos, transportadora líder y flete promedio
                    </p>
                    <ColombiaMap byRegion={by_region} style={{ minHeight: '320px' }} />
                    {Array.isArray(by_region) && by_region.length > 0 ? (
                        <ul style={{ margin: '1rem 0 0', paddingLeft: '1.25rem', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1rem' }}>
                            {by_region.slice(0, 8).map((r, i) => (
                                <li key={i}>
                                    <strong style={{ color: 'var(--text-main)' }}>{r.department ?? '—'}</strong>: {formatNumber(r.orders)} pedidos - {formatCurrency(r.revenue)} - Top: {r.top_carrier ?? '—'} - Flete prom.: {formatCurrency(r.avg_shipping_price)}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-muted" style={{ margin: '1rem 0 0' }}>
                            Sin datos por región para el período seleccionado. El mapa igual se muestra para validar cobertura geográfica.
                        </p>
                    )}
                </GlassCard>
            </div>

            {/* Producto más vendido y Top productos */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
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
                                {(topProduct.product_name || '').length > 60 ? `${(topProduct.product_name || '').slice(0, 60)}…` : (topProduct.product_name || '—')}
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
                                    {top_products.slice(0, 10).map((p, i) => (
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
            </div>

            {/* Sección 5: Efectividad por Transportadora */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Truck size={24} style={{ color: 'var(--primary)' }} />
                    Efectividad por Transportadora
                </h2>
                <GlassCard style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Empresa</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Aprobados</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Tiempos (%)</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Devoluciones</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Cancelados</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Recaudos</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Ventas (%)</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Efectividad</th>
                            </tr>
                        </thead>
                        <tbody>
                            {by_carrier.map((carrier, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '0.75rem', fontWeight: 500 }}>{carrier.carrier}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(carrier.approved_count)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                                        {formatNumber(carrier.times_count)} ({formatPercent(carrier.times_pct)})
                                    </td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(carrier.returns_count)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(carrier.cancelled_count)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(carrier.recollections_count)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--success)' }}>
                                        {formatCurrency(carrier.sales_amount)} ({formatPercent(carrier.sales_pct)})
                                    </td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 'bold', color: carrier.effectiveness_pct >= 50 ? 'var(--success)' : 'var(--danger)' }}>
                                        {formatPercent(carrier.effectiveness_pct)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </GlassCard>
            </div>

            {/* Sección 6: Rentabilidad por Producto */}
            <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Package size={24} style={{ color: 'var(--primary)' }} />
                    Rentabilidad por Producto
                </h2>
                <GlassCard style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Producto</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Ventas</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Utilidad (%)</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Margen (%)</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>% Desc</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Valor Venta</th>
                                <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Utilidad Bruta</th>
                            </tr>
                        </thead>
                        <tbody>
                            {product_profitability.slice(0, 20).map((product, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '0.75rem', maxWidth: '300px', wordBreak: 'break-word' }}>
                                        {product.product_name?.length > 50 ? `${product.product_name.slice(0, 50)}...` : product.product_name}
                                    </td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatNumber(product.sales_count)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 'bold', color: 'var(--success)' }}>
                                        {formatPercent(product.margin_pct)}
                                    </td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatPercent(product.margin_pct)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatPercent(product.discount_pct)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>{formatCurrency(product.sale_value)}</td>
                                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: 'bold', color: 'var(--success)' }}>
                                        {formatCurrency(product.gross_profit)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </GlassCard>
            </div>

            {/* Sección 7: Comparativa de Transportadoras (Gráfico) */}
            {carrierComparison && carrierComparison.carriers && carrierComparison.carriers.length > 0 && (
                <div style={{ marginBottom: '2rem' }}>
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <BarChart3 size={24} style={{ color: 'var(--primary)' }} />
                        Comparativa de Transportadoras
                    </h2>
                    <GlassCard>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <p className="text-muted" style={{ fontSize: '0.9rem', margin: 0 }}>
                                Análisis de rendimiento gráfico (KPI) - {carrierComparison.period_label}
                            </p>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                    onClick={() => setTimeFilter('month')}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        borderRadius: '8px',
                                        background: timeFilter === 'month' ? 'var(--primary)' : 'transparent',
                                        color: timeFilter === 'month' ? 'white' : 'var(--text-muted)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        cursor: 'pointer',
                                    }}
                                >
                                    Históricos
                                </button>
                                <button
                                    onClick={() => setTimeFilter('day')}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        borderRadius: '8px',
                                        background: timeFilter === 'day' ? 'var(--primary)' : 'transparent',
                                        color: timeFilter === 'day' ? 'white' : 'var(--text-muted)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        cursor: 'pointer',
                                    }}
                                >
                                    Hoy
                                </button>
                            </div>
                        </div>
                        {/* Gráfico de barras simple usando divs */}
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1rem', height: '300px', padding: '1rem 0' }}>
                            {carrierComparison.carriers.slice(0, 10).map((carrier, idx) => {
                                const maxSales = Math.max(...carrierComparison.carriers.map(c => c.sales_amount));
                                const height = maxSales > 0 ? (carrier.sales_amount / maxSales) * 100 : 0;
                                return (
                                    <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                                        <div
                                            style={{
                                                width: '100%',
                                                height: `${height}%`,
                                                background: `linear-gradient(180deg, var(--primary), #4f46e5)`,
                                                borderRadius: '8px 8px 0 0',
                                                minHeight: '20px',
                                                display: 'flex',
                                                alignItems: 'flex-end',
                                                justifyContent: 'center',
                                                padding: '0.5rem',
                                                color: 'white',
                                                fontSize: '0.75rem',
                                                fontWeight: 'bold',
                                            }}
                                            title={`${carrier.carrier}: ${formatCurrency(carrier.sales_amount)}`}
                                        >
                                            {height > 10 && formatCurrency(carrier.sales_amount)}
                                        </div>
                                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0, textAlign: 'center', wordBreak: 'break-word' }}>
                                            {carrier.carrier?.length > 10 ? `${carrier.carrier.slice(0, 10)}...` : carrier.carrier}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </GlassCard>
                </div>
            )}

            {/* Sección 8: Transportadoras Más Reportadas */}
            {carrier_reports && carrier_reports.length > 0 && (
                <div style={{ marginBottom: '2rem' }}>
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertCircle size={24} style={{ color: 'var(--warning)' }} />
                        Transportadoras Más Reportadas
                    </h2>
                    <GlassCard>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                            {carrier_reports.map((report, idx) => (
                                <div key={idx} style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                                    <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>{report.carrier}</p>
                                    <p style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0, color: 'var(--warning)' }}>
                                        {formatNumber(report.reports_count)} reportes
                                    </p>
                                </div>
                            ))}
                        </div>
                    </GlassCard>
                </div>
            )}
        </div>
    );
};

export default AnalyticsDashboard;

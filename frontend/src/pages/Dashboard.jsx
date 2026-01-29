import React, { useEffect, useState } from 'react';
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, ReferenceLine
} from 'recharts';
import { Zap } from 'lucide-react';
import { fetchDashboardStats } from '../services/api';
import './Dashboard.css';

import GlassCard from '../components/common/GlassCard';
import OpportunityCard from '../components/domain/market/OpportunityCard';
import ErrorState from '../components/common/ErrorState';
import EmptyState from '../components/common/EmptyState';

const CustomTooltip = React.memo(({ active, payload }) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="custom-tooltip glass-panel" style={{ padding: '0.8rem', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.9)', borderRadius: 8 }}>
                <p style={{ fontWeight: 'bold', color: '#fff', marginBottom: 4 }}>{data.category}</p>
                <div style={{ fontSize: '0.8rem', color: '#ccc' }}>
                    <p>Volumen: {data.volume} productos</p>
                    <p>Margen Avg: {data.avg_margin}%</p>
                    <p>Competencia: {data.competitiveness}</p>
                </div>
            </div>
        );
    }
    return null;
});

const Dashboard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let mounted = true;
        
        const loadStats = async () => {
            try {
                setError(null);
                const res = await fetchDashboardStats();
                if (mounted) {
                    setData(res);
                }
            } catch (err) {
                console.error("Failed to load intelligence:", err);
                if (mounted) {
                    setError(err.message || "Error al cargar los datos del dashboard");
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };
        
        loadStats();
        
        return () => {
            mounted = false;
        };
    }, []);

    // Error state - always show errors first
    if (error) {
        return (
            <ErrorState
                error={error}
                onRetry={() => {
                    setError(null);
                    setLoading(true);
                    window.location.reload();
                }}
                title="Error al cargar datos"
            />
        );
    }

    // Loading state - ONLY when loading AND no data exists (prevents flash on refetch)
    if (loading && !data) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh', color: '#6366f1' }}>
                <Zap className="spin" size={48} />
                <p style={{ marginTop: '1rem' }}>Sincronizando Inteligencia de Mercado...</p>
                <style jsx>{` .spin { animation: spin 1s infinite linear; } @keyframes spin { 100% { transform: rotate(360deg); } } `}</style>
            </div>
        );
    }

    // Empty state - when no data available
    if (!data) {
        return (
            <EmptyState
                icon={Zap}
                title="No hay datos disponibles"
                description="Los datos del dashboard aparecerán aquí una vez que estén disponibles."
            />
        );
    }

    const { tactical_feed = [], market_radar = [] } = data;

    return (
        <div className="dashboard-container" style={{ maxWidth: '1600px', margin: '0 auto', padding: '2rem' }}>
            {/* Header */}
            <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', marginBottom: '2rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Centro de Comando</h1>
                    <p className="subtitle" style={{ color: '#94a3b8', margin: '0.5rem 0 0 0' }}>Resumen Estratégico & Oportunidades Diarias</p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.1)', padding: '0.5rem 1rem', borderRadius: '20px', fontSize: '0.9rem', color: '#e2e8f0' }}>
                    <span>{new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
                </div>
            </div>

            {/* SECTION 1: TACTICAL FEED */}
            <section style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', color: '#fff' }}>
                    <Zap size={20} color="#f59e0b" fill="#f59e0b" />
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>Hallazgos Flash (24h)</h3>
                    <span style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', padding: '2px 8px', borderRadius: '99px', fontSize: '0.7rem', fontWeight: 'bold', border: '1px solid rgba(245, 158, 11, 0.3)' }}>Top Oportunidades</span>
                </div>

                {tactical_feed.length === 0 ? (
                    <EmptyState
                        icon={Zap}
                        title="No hay hallazgos flash"
                        description="El escaneo de hoy no ha encontrado 'Unicornios' todavía. Revisa Gold Mine."
                    />
                ) : (
                    <div className="cards-grid">
                        {tactical_feed.map(item => (
                            <OpportunityCard key={item.id} product={item} />
                        ))}
                    </div>
                )}
            </section>

            {/* SECTION 2: STRATEGIC RADAR & ANALYTICS */}
            <div className="strategy-grid">

                {/* RADAR CHART */}
                <GlassCard className="chart-panel">
                    <div style={{ marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.1rem', color: '#fff', margin: '0 0 0.25rem 0' }}>Radar de Categorías</h3>
                        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>Eje X: Saturación (Competencia) vs Eje Y: Rentabilidad (Margen)</p>
                    </div>
                    <div style={{ width: '100%', height: 350 }}>
                        <ResponsiveContainer>
                            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                <XAxis
                                    type="number"
                                    dataKey="competitiveness"
                                    name="Saturación"
                                    stroke="#94a3b8"
                                    label={{ value: 'Saturación (Más a la derecha es Peor)', position: 'bottom', offset: 0, fill: '#64748b', fontSize: 12 }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="avg_margin"
                                    name="Margen"
                                    stroke="#94a3b8"
                                    label={{ value: '% Margen Promedio', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 12 }}
                                />
                                <ZAxis type="number" dataKey="volume" range={[60, 400]} name="Volumen" />
                                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                                <ReferenceLine x={5} stroke="red" strokeDasharray="3 3" label={{ position: 'top', value: 'Zona Roja', fill: 'red', fontSize: 10 }} />
                                <ReferenceLine y={40} stroke="#10b981" strokeDasharray="3 3" label={{ position: 'right', value: 'High Profit', fill: '#10b981', fontSize: 10 }} />
                                <Scatter name="Categorías" data={market_radar} fill="#8884d8">
                                    {market_radar.map((entry, index) => (
                                        <cell key={`cell-${index}`} fill={entry.avg_margin > 40 ? '#10b981' : (entry.competitiveness > 6 ? '#ef4444' : '#6366f1')} />
                                    ))}
                                </Scatter>
                            </ScatterChart>
                        </ResponsiveContainer>
                    </div>
                </GlassCard>

                {/* TOP MOVERS LIST */}
                <GlassCard className="list-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1.1rem', color: '#fff', margin: '0 0 0.25rem 0' }}>Top Categorías</h3>
                        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>Ranking por Margen Promedio</p>
                    </div>
                    <div className="category-list custom-scrollbar" style={{ flex: 1, overflowY: 'auto' }}>
                        {market_radar.map((cat, idx) => (
                            <div key={idx} className="cat-row">
                                <div className="rank">#{idx + 1}</div>
                                <div className="cat-info">
                                    <span className="cat-name">{cat.category}</span>
                                    <span className="cat-meta">{cat.volume} productos</span>
                                </div>
                                <div className="cat-stat">
                                    <span className={`stat-val ${cat.avg_margin > 40 ? 'positive' : ''}`}>
                                        {cat.avg_margin}%
                                    </span>
                                    <span className="stat-label">Margen</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </GlassCard>
            </div>

            <style jsx>{`
                .cards-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
                    gap: 1.5rem;
                }
                .strategy-grid {
                    display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;
                }
                .cat-row {
                    display: flex; alignItems: center; gap: 1rem; padding: 0.75rem 0;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }
                .rank { font-size: 0.9rem; font-weight: bold; color: #64748b; width: 25px; }
                .cat-info { flex: 1; display: flex; flexDirection: column; }
                .cat-name { color: #e2e8f0; font-size: 0.9rem; font-weight: 500; }
                .cat-meta { color: #64748b; font-size: 0.75rem; }
                
                .cat-stat { display: flex; flexDirection: column; alignItems: flex-end; }
                .stat-val { font-weight: bold; color: #fff; font-size: 0.95rem; }
                .stat-val.positive { color: #10b981; }
                .stat-label { font-size: 0.7rem; color: #64748b; }

                @media (max-width: 1024px) {
                    .strategy-grid { grid-template-columns: 1fr; }
                }
                .text-gradient {
                    background: linear-gradient(to right, #fff, #94a3b8);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
            `}</style>
        </div>
    );
};

export default Dashboard;

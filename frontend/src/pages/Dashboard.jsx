import React, { useEffect, useState } from 'react';
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, ReferenceLine
} from 'recharts';
import { TrendingUp, Activity, ArrowRight, DollarSign, Target, Award, Zap } from 'lucide-react';
import { fetchDashboardStats } from '../services/api';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

import LazyImage from '../components/common/LazyImage';

const OpportunityCard = ({ product }) => {
    const navigate = useNavigate();

    return (
        <div className="glass-card tactical-card" onClick={() => window.open(`https://app.dropi.co/products/${product.id}`, '_blank')}>
            <div className="card-badge">{product.badge}</div>
            <div className="img-container">
                <LazyImage
                    src={product.image}
                    alt={product.title}
                    style={{ width: '100%', height: '100%' }}
                />
                <div className="overlay">
                    <button className="btn-primary">Ver en Dropi <ArrowRight size={14} /></button>
                </div>
            </div>
            <div className="card-content">
                <h4 title={product.title}>{product.title}</h4>
                <div className="metrics">
                    <div className="metric">
                        <span className="label">Precio</span>
                        <span className="value">${parseInt(product.price).toLocaleString()}</span>
                    </div>
                    <div className="metric highlight">
                        <span className="label">Margen</span>
                        <span className="value">+{parseInt(product.margin)}%</span>
                    </div>
                </div>
                <div className="competitors-tag">
                    <Target size={12} />
                    <span>{product.competitors} {product.competitors === 1 ? 'Rival' : 'Rivales'}</span>
                </div>
            </div>
        </div>
    );
};
const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="custom-tooltip glass-panel" style={{ padding: '0.8rem', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.9)' }}>
                <p style={{ fontWeight: 'bold', color: '#fff', marginBottom: 4 }}>{data.category}</p>
                <div style={{ fontSize: '0.8rem', color: '#ccc' }}>
                    <p>Volumen: {data.volume} productos</p>
                    <p>Margen Avg: {data.avg_margin}%</p>
                    <p>Competencia: {data.competitiveness} (Saturación)</p>
                </div>
            </div>
        );
    }
    return null;
};

const Dashboard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadStats = async () => {
            try {
                const res = await fetchDashboardStats();
                setData(res);
            } catch (error) {
                console.error("Failed to load intelligence");
            } finally {
                setLoading(false);
            }
        };
        loadStats();
    }, []);

    if (loading) return (
        <div className="dashboard-loading">
            <Activity className="spin-icon" size={48} color="#6366f1" />
            <p>Sincronizando Inteligencia de Mercado...</p>
        </div>
    );

    if (!data) return <div style={{ padding: '2rem' }}>Error de conexión con Neural Core.</div>;

    const { tactical_feed = [], market_radar = [] } = data;

    return (
        <div className="dashboard-container">
            {/* Header */}
            <div className="dashboard-header">
                <div>
                    <h1 className="text-gradient">Centro de Comando</h1>
                    <p className="subtitle">Resumen Estratégico & Oportunidades Diarias</p>
                </div>
                <div className="date-badge">
                    <span>{new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
                </div>
            </div>

            {/* SECTION 1: TACTICAL FEED */}
            <section className="section-feed">
                <div className="section-title">
                    <Zap size={20} color="#f59e0b" fill="#f59e0b" />
                    <h3>Hallazgos Flash (24h)</h3>
                    <span className="chip">Top Oportunidades</span>
                </div>

                {tactical_feed.length === 0 ? (
                    <div className="empty-state glass-panel">
                        <p>El escaneo de hoy no ha encontrado "Unicornios" todavía. Revisa Gold Mine.</p>
                    </div>
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
                <div className="glass-card chart-panel">
                    <div className="panel-header">
                        <h3>Radar de Categorías</h3>
                        <p>Eje X: Saturación (Competencia) vs Eje Y: Rentabilidad (Margen)</p>
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
                </div>

                {/* TOP MOVERS LIST */}
                <div className="glass-card list-panel">
                    <div className="panel-header">
                        <h3>Top Categorías</h3>
                        <p>Ranking por Margen Promedio</p>
                    </div>
                    <div className="category-list custom-scrollbar">
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
                </div>
            </div>

            <style>{`
                .section-feed { margin-bottom: 2rem; }
                .section-title { display: flex; align-items: center; gap: 0.75rem; marginBottom: 1rem; color: #fff; }
                .section-title h3 { font-size: 1.25rem; font-weight: 600; }
                .chip { background: rgba(245, 158, 11, 0.15); color: #f59e0b; padding: 2px 8px; border-radius: 99px; font-size: 0.7rem; font-weight: bold; border: 1px solid rgba(245, 158, 11, 0.3); }

                .cards-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
                    gap: 1.5rem;
                }

                .tactical-card {
                    padding: 0;
                    overflow: hidden;
                    transition: transform 0.2s, box-shadow 0.2s;
                    cursor: pointer;
                    position: relative;
                }
                .tactical-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.3); border-color: rgba(99, 102, 241, 0.5); }
                
                .card-badge {
                    position: absolute; top: 10px; left: 10px; z-index: 2;
                    background: #10b981; color: white; padding: 2px 8px; border-radius: 4px;
                    font-size: 0.7rem; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }

                .img-container {
                    height: 180px; width: 100%; position: relative; background: #000;
                }
                .img-container img { width: 100%; height: 100%; object-fit: contain; }
                .overlay {
                    position: absolute; inset: 0; background: rgba(0,0,0,0.4);
                    display: flex; align-items: center; justify-content: center;
                    opacity: 0; transition: opacity 0.2s;
                }
                .tactical-card:hover .overlay { opacity: 1; }

                .card-content { padding: 1rem; }
                .card-content h4 { font-size: 0.95rem; margin-bottom: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff; }
                
                .metrics { display: flex; justify-content: space-between; margin-bottom: 0.75rem; }
                .metric { display: flex; flexDirection: column; }
                .metric.highlight .value { color: #10b981; }
                .metric .label { font-size: 0.7rem; color: #64748b; }
                .metric .value { font-weight: bold; font-size: 0.9rem; }

                .competitors-tag { 
                    display: flex; alignItems: center; gap: 4px; font-size: 0.75rem; color: #94a3b8; 
                    background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; width: fit-content;
                }

                .strategy-grid {
                    display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;
                }
                .panel-header { margin-bottom: 1.5rem; }
                .panel-header h3 { font-size: 1.1rem; color: #fff; margin-bottom: 0.25rem; }
                .panel-header p { font-size: 0.8rem; color: #64748b; }

                .chart-panel { padding: 1.5rem; }
                .list-panel { padding: 1.5rem; height: 100%; max-height: 450px; display: flex; flexDirection: column; }

                .category-list { flex: 1; overflow-y: auto; padding-right: 0.5rem; }
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
            `}</style>
        </div>
    );
};

export default Dashboard;

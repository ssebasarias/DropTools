import React, { useState } from 'react';
import { 
    DollarSign, 
    TrendingUp, 
    Package, 
    XCircle, 
    CheckCircle, 
    Truck, 
    MapPin,
    BarChart3
} from 'lucide-react';
import GlassCard from '../../components/common/GlassCard';

const ClientDashboard = () => {
    const [timeFilter, setTimeFilter] = useState('day');

    const kpiData = {
        income: 45230,
        expenses: 12340,
        delivered: 156,
        cancelled: 12,
        carrierEfficiency: 94.5,
        topProduct: {
            name: 'Producto Estrella XYZ',
            sales: 234,
            revenue: 12500
        }
    };

    const regionsData = {
        topBuying: [
            { name: 'BogotÃ¡', purchases: 450, size: 80 },
            { name: 'MedellÃ­n', purchases: 320, size: 65 },
            { name: 'Cali', purchases: 280, size: 58 },
            { name: 'Barranquilla', purchases: 195, size: 45 },
            { name: 'Cartagena', purchases: 150, size: 38 }
        ],
        topReturns: [
            { name: 'BogotÃ¡', returns: 45, size: 50 },
            { name: 'MedellÃ­n', returns: 32, size: 38 },
            { name: 'Cali', returns: 28, size: 35 }
        ]
    };

    const timeFilters = [
        { value: 'day', label: 'DÃ­a' },
        { value: 'week', label: 'Semana' },
        { value: 'fortnight', label: 'Quincena' },
        { value: 'month', label: 'Mes' }
    ];

    return (
        <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Dashboard</h1>
                    <p className="text-muted" style={{ marginTop: '0.5rem' }}>AnÃ¡lisis de rendimiento y estadÃ­sticas de tu negocio</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--glass-bg)', padding: '0.5rem', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                    {timeFilters.map(filter => (
                        <button
                            key={filter.value}
                            onClick={() => setTimeFilter(filter.value)}
                            style={{
                                padding: '0.5rem 1rem',
                                borderRadius: '8px',
                                background: timeFilter === filter.value 
                                    ? 'linear-gradient(135deg, var(--primary), #4f46e5)' 
                                    : 'transparent',
                                color: timeFilter === filter.value ? 'white' : 'var(--text-muted)',
                                border: 'none',
                                cursor: 'pointer',
                                fontWeight: timeFilter === filter.value ? 600 : 400,
                                transition: 'all 0.2s'
                            }}
                        >
                            {filter.label}
                        </button>
                    ))}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Ingresos</p>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                                
                            </h2>
                        </div>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(99,102,241,0.2)', 
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <DollarSign size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <TrendingUp size={16} style={{ color: 'var(--success)' }} />
                        <span style={{ color: 'var(--success)' }}>+12.5% vs perÃ­odo anterior</span>
                    </div>
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Egresos</p>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                                
                            </h2>
                        </div>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(239,68,68,0.2)', 
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <TrendingUp size={24} style={{ color: 'var(--danger)', transform: 'rotate(180deg)' }} />
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <span className="text-muted">Gastos operativos</span>
                    </div>
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Entregados</p>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                                {kpiData.delivered}
                            </h2>
                        </div>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(16,185,129,0.2)', 
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <CheckCircle size={24} style={{ color: 'var(--success)' }} />
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--success)' }}>92.8% tasa de Ã©xito</span>
                    </div>
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
                        <div>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Cancelados</p>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                                {kpiData.cancelled}
                            </h2>
                        </div>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(239,68,68,0.2)', 
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <XCircle size={24} style={{ color: 'var(--danger)' }} />
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <span className="text-muted">7.2% tasa de cancelaciÃ³n</span>
                    </div>
                </GlassCard>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(99,102,241,0.2)', 
                            borderRadius: '12px'
                        }}>
                            <Truck size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Eficiencia de Transportadora</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>Rendimiento de entregas</p>
                        </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ 
                            fontSize: '4rem', 
                            fontWeight: 'bold', 
                            background: 'linear-gradient(135deg, var(--primary), #4f46e5)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            marginBottom: '0.5rem'
                        }}>
                            {kpiData.carrierEfficiency}%
                        </div>
                        <p className="text-muted">Tasa de entregas exitosas</p>
                    </div>
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(245,158,11,0.2)', 
                            borderRadius: '12px'
                        }}>
                            <Package size={24} style={{ color: 'var(--warning)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Producto Top</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>MÃ¡s vendido del perÃ­odo</p>
                        </div>
                    </div>
                    <div>
                        <h4 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>{kpiData.topProduct.name}</h4>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
                            <div>
                                <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>Ventas</p>
                                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{kpiData.topProduct.sales}</p>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>Ingresos</p>
                                <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}></p>
                            </div>
                        </div>
                    </div>
                </GlassCard>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(16,185,129,0.2)', 
                            borderRadius: '12px'
                        }}>
                            <MapPin size={24} style={{ color: 'var(--success)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Regiones que MÃ¡s Compran</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>DistribuciÃ³n geogrÃ¡fica de compras</p>
                        </div>
                    </div>
                    <div style={{ 
                        height: '400px', 
                        background: 'rgba(255,255,255,0.02)', 
                        borderRadius: '12px',
                        position: 'relative',
                        border: '1px solid var(--glass-border)',
                        overflow: 'hidden'
                    }}>
                        <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
                            <rect width="100%" height="100%" fill="rgba(99,102,241,0.05)" />
                            {regionsData.topBuying.map((region, idx) => (
                                <g key={idx}>
                                    <circle
                                        cx={`${20 + idx * 15}%`}
                                        cy={`${30 + idx * 10}%`}
                                        r={region.size / 2}
                                        fill="rgba(16,185,129,0.3)"
                                        stroke="var(--success)"
                                        strokeWidth="2"
                                    />
                                    <text
                                        x={`${20 + idx * 15}%`}
                                        y={`${30 + idx * 10}%`}
                                        textAnchor="middle"
                                        fill="var(--text-main)"
                                        fontSize="12"
                                        fontWeight="bold"
                                        dy="4"
                                    >
                                        {region.purchases}
                                    </text>
                                    <text
                                        x={`${20 + idx * 15}%`}
                                        y={`${30 + idx * 10 + region.size / 2 + 20}%`}
                                        textAnchor="middle"
                                        fill="var(--text-muted)"
                                        fontSize="10"
                                    >
                                        {region.name}
                                    </text>
                                </g>
                            ))}
                        </svg>
                        <div style={{ 
                            position: 'absolute', 
                            bottom: '1rem', 
                            left: '1rem', 
                            background: 'var(--glass-bg)', 
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-border)'
                        }}>
                            <p style={{ fontSize: '0.85rem', margin: 0, color: 'var(--text-muted)' }}>
                                TamaÃ±o del cÃ­rculo = Volumen de compras
                            </p>
                        </div>
                    </div>
                </GlassCard>

                <GlassCard>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(239,68,68,0.2)', 
                            borderRadius: '12px'
                        }}>
                            <MapPin size={24} style={{ color: 'var(--danger)' }} />
                        </div>
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Regiones que MÃ¡s Devuelven</h3>
                            <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0 }}>DistribuciÃ³n geogrÃ¡fica de devoluciones</p>
                        </div>
                    </div>
                    <div style={{ 
                        height: '400px', 
                        background: 'rgba(255,255,255,0.02)', 
                        borderRadius: '12px',
                        position: 'relative',
                        border: '1px solid var(--glass-border)',
                        overflow: 'hidden'
                    }}>
                        <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
                            <rect width="100%" height="100%" fill="rgba(239,68,68,0.05)" />
                            {regionsData.topReturns.map((region, idx) => (
                                <g key={idx}>
                                    <circle
                                        cx={`${25 + idx * 20}%`}
                                        cy={`${35 + idx * 12}%`}
                                        r={region.size / 2}
                                        fill="rgba(239,68,68,0.3)"
                                        stroke="var(--danger)"
                                        strokeWidth="2"
                                    />
                                    <text
                                        x={`${25 + idx * 20}%`}
                                        y={`${35 + idx * 12}%`}
                                        textAnchor="middle"
                                        fill="var(--text-main)"
                                        fontSize="12"
                                        fontWeight="bold"
                                        dy="4"
                                    >
                                        {region.returns}
                                    </text>
                                    <text
                                        x={`${25 + idx * 20}%`}
                                        y={`${35 + idx * 12 + region.size / 2 + 20}%`}
                                        textAnchor="middle"
                                        fill="var(--text-muted)"
                                        fontSize="10"
                                    >
                                        {region.name}
                                    </text>
                                </g>
                            ))}
                        </svg>
                        <div style={{ 
                            position: 'absolute', 
                            bottom: '1rem', 
                            left: '1rem', 
                            background: 'var(--glass-bg)', 
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-border)'
                        }}>
                            <p style={{ fontSize: '0.85rem', margin: 0, color: 'var(--text-muted)' }}>
                                TamaÃ±o del cÃ­rculo = Volumen de devoluciones
                            </p>
                        </div>
                    </div>
                </GlassCard>
            </div>

            <GlassCard style={{ 
                background: 'rgba(245,158,11,0.1)', 
                borderColor: 'rgba(245,158,11,0.3)',
                textAlign: 'center'
            }}>
                <p className="text-muted" style={{ margin: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <BarChart3 size={16} />
                    Los datos mostrados son de ejemplo. Esta secciÃ³n se actualizarÃ¡ automÃ¡ticamente cuando el mÃ³dulo de anÃ¡lisis de reportes estÃ© completamente desarrollado.
                </p>
            </GlassCard>
        </div>
    );
};

export default ClientDashboard;

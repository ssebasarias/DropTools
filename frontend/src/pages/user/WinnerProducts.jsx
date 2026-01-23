import React, { useState } from 'react';
import { 
    Star, 
    ShoppingCart, 
    TrendingUp, 
    ExternalLink, 
    Search, 
    Filter,
    DollarSign,
    Users,
    Zap,
    Trophy,
    Target,
    ArrowRight,
    BarChart3
} from 'lucide-react';
import SubscriptionGate from '../../components/common/SubscriptionGate';
import GlassCard from '../../components/common/GlassCard';
import LazyImage from '../../components/common/LazyImage';
import CompetitorBadge from '../../components/common/CompetitorBadge';

const ProductCard = ({ product }) => (
    <GlassCard
        padding="0"
        hoverEffect={true}
        onClick={() => product.url && window.open(product.url, '_blank')}
        style={{ cursor: 'pointer', overflow: 'hidden', position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}
    >
        {product.isHot && (
            <div style={{
                position: 'absolute',
                top: '10px',
                left: '10px',
                zIndex: 2,
                background: 'rgba(239,68,68,0.9)',
                color: 'white',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.7rem',
                fontWeight: 'bold',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
            }}>
                <Zap size={12} fill="white" />
                Hot
            </div>
        )}
        
        {product.badge && (
            <div style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                zIndex: 2,
                background: product.badge === 'High Demand' ? 'rgba(16,185,129,0.9)' : product.badge === 'Low Competition' ? 'rgba(245,158,11,0.9)' : 'rgba(99,102,241,0.9)',
                color: 'white',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.7rem',
                fontWeight: 'bold',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
            }}>
                {product.badge}
            </div>
        )}

        <div style={{ 
            height: '200px', 
            width: '100%', 
            position: 'relative', 
            background: '#000',
            overflow: 'hidden'
        }}>
            {product.image ? (
                <LazyImage
                    src={product.image}
                    alt={product.name}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
            ) : (
                <div style={{ 
                    width: '100%', 
                    height: '100%', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    background: 'rgba(255,255,255,0.05)'
                }}>
                    <ShoppingCart size={64} className="text-muted" style={{ opacity: 0.3 }} />
                </div>
            )}
            <div style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(0,0,0,0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: 0,
                transition: 'opacity 0.2s'
            }} className="product-overlay">
                <button 
                    className="btn-primary" 
                    style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.5rem',
                        pointerEvents: 'none'
                    }}
                >
                    Ver en Dropi <ArrowRight size={14} />
                </button>
            </div>
        </div>

        <div style={{ padding: '1.25rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ 
                fontSize: '1rem', 
                fontWeight: '600', 
                margin: '0 0 0.75rem 0', 
                color: 'var(--text-main)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
            }} title={product.name}>
                {product.name}
            </h4>

            <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                marginBottom: '0.75rem',
                gap: '0.5rem'
            }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Precio</span>
                    <span style={{ fontWeight: 'bold', fontSize: '1rem', color: 'var(--text-main)' }}>
                        ${product.price?.toLocaleString() || 'N/A'}
                    </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Margen</span>
                    <span style={{ fontWeight: 'bold', fontSize: '1rem', color: 'var(--success)' }}>
                        +{product.margin || 'N/A'}%
                    </span>
                </div>
            </div>

            <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.5rem',
                marginTop: 'auto',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--glass-border)'
            }}>
                <Target size={14} style={{ color: 'var(--text-muted)' }} />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {product.competitors || 0} {product.competitors === 1 ? 'Competidor' : 'Competidores'}
                </span>
                {product.growth && (
                    <>
                        <span style={{ margin: '0 0.25rem', color: 'var(--text-muted)' }}>â€¢</span>
                        <TrendingUp size={14} style={{ color: 'var(--success)' }} />
                        <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
                            +{product.growth}%
                        </span>
                    </>
                )}
            </div>
        </div>

        <style>{`
            .product-overlay {
                opacity: 0;
                transition: opacity 0.2s;
            }
            .glass-card-component:hover .product-overlay {
                opacity: 1;
            }
        `}</style>
    </GlassCard>
);

const WinnerProducts = () => {
    const [search, setSearch] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [viewMode, setViewMode] = useState('grid');
    const [minPrice, setMinPrice] = useState('');
    const [maxPrice, setMaxPrice] = useState('');

        // Mock data - Productos realistas con datos completos
    const products = [
        {
            id: 1,
            name: 'Auriculares InalÃ¡mbricos Bluetooth 5.0',
            description: 'Auriculares con cancelaciÃ³n de ruido activa, baterÃ­a de 30h y calidad de sonido premium.',
            growth: 28,
            rating: 4.8,
            price: 89000,
            margin: 42,
            competitors: 1,
            badge: 'High Demand',
            isHot: true,
            image: null,
            url: 'https://app.dropi.co/products/1',
            saturation: 'BAJA',
            category: 'electronics'
        },
        {
            id: 2,
            name: 'Smartwatch Fitness Tracker',
            description: 'Reloj inteligente con monitor de frecuencia cardÃ­aca, GPS y resistencia al agua.',
            growth: 35,
            rating: 4.6,
            price: 125000,
            margin: 38,
            competitors: 2,
            badge: 'Low Competition',
            isHot: true,
            image: null,
            url: 'https://app.dropi.co/products/2',
            saturation: 'BAJA',
            category: 'electronics'
        },
        {
            id: 3,
            name: 'Zapatillas Deportivas Running',
            description: 'Zapatillas ligeras con tecnologÃ­a de amortiguaciÃ³n avanzada para corredores.',
            growth: 22,
            rating: 4.7,
            price: 145000,
            margin: 45,
            competitors: 0,
            badge: 'Trending',
            isHot: true,
            image: null,
            url: 'https://app.dropi.co/products/3',
            saturation: 'BAJA',
            category: 'sports'
        },
        {
            id: 4,
            name: 'Cargador InalÃ¡mbrico Magsafe',
            description: 'Cargador rÃ¡pido inalÃ¡mbrico compatible con iPhone y Android, 15W de potencia.',
            growth: 18,
            rating: 4.5,
            price: 45000,
            margin: 40,
            competitors: 3,
            badge: 'High Demand',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/4',
            saturation: 'MEDIA',
            category: 'electronics'
        },
        {
            id: 5,
            name: 'Mochila Antirrobo con USB',
            description: 'Mochila resistente al agua con puerto USB integrado y compartimentos antirrobo.',
            growth: 25,
            rating: 4.6,
            price: 78000,
            margin: 36,
            competitors: 2,
            badge: 'Low Competition',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/5',
            saturation: 'BAJA',
            category: 'fashion'
        },
        {
            id: 6,
            name: 'LÃ¡mpara LED Inteligente RGB',
            description: 'Bombilla LED con control por app, 16 millones de colores y compatibilidad con Alexa.',
            growth: 30,
            rating: 4.4,
            price: 55000,
            margin: 48,
            competitors: 1,
            badge: 'Trending',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/6',
            saturation: 'BAJA',
            category: 'home'
        },
        {
            id: 7,
            name: 'Kit de Herramientas Profesional',
            description: 'Set completo de 85 piezas con estuche resistente, ideal para bricolaje y reparaciones.',
            growth: 15,
            rating: 4.7,
            price: 165000,
            margin: 33,
            competitors: 4,
            badge: 'High Demand',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/7',
            saturation: 'MEDIA',
            category: 'home'
        },
        {
            id: 8,
            name: 'Gafas de Sol Polarizadas UV400',
            description: 'Gafas de sol con protecciÃ³n total UV, diseÃ±o moderno y lentes polarizadas.',
            growth: 20,
            rating: 4.5,
            price: 68000,
            margin: 41,
            competitors: 2,
            badge: 'Low Competition',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/8',
            saturation: 'BAJA',
            category: 'fashion'
        },
        {
            id: 9,
            name: 'BÃ¡scula Inteligente Bluetooth',
            description: 'BÃ¡scula digital con app para seguimiento de peso, IMC, grasa corporal y mÃ¡s mÃ©tricas.',
            growth: 27,
            rating: 4.6,
            price: 95000,
            margin: 39,
            competitors: 1,
            badge: 'Trending',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/9',
            saturation: 'BAJA',
            category: 'electronics'
        },
        {
            id: 10,
            name: 'Alfombra de Yoga Antideslizante',
            description: 'Alfombra ecolÃ³gica de 6mm de grosor, antideslizante y fÃ¡cil de limpiar.',
            growth: 19,
            rating: 4.8,
            price: 52000,
            margin: 44,
            competitors: 3,
            badge: 'High Demand',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/10',
            saturation: 'MEDIA',
            category: 'sports'
        },
        {
            id: 11,
            name: 'Ventilador de Torre Silencioso',
            description: 'Ventilador de 40 pulgadas con control remoto, modo nocturno silencioso y oscilaciÃ³n.',
            growth: 24,
            rating: 4.5,
            price: 112000,
            margin: 37,
            competitors: 2,
            badge: 'Low Competition',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/11',
            saturation: 'BAJA',
            category: 'home'
        },
        {
            id: 12,
            name: 'Reloj Inteligente para NiÃ±os GPS',
            description: 'Smartwatch infantil con GPS, llamadas, cÃ¡mara y geolocalizaciÃ³n para padres.',
            growth: 32,
            rating: 4.7,
            price: 138000,
            margin: 43,
            competitors: 0,
            badge: 'Trending',
            isHot: false,
            image: null,
            url: 'https://app.dropi.co/products/12',
            saturation: 'BAJA',
            category: 'electronics'
        }
    ];

    const categories = [
        { id: 'all', name: 'Todas las CategorÃ­as' },
        { id: 'electronics', name: 'ElectrÃ³nica' },
        { id: 'fashion', name: 'Moda' },
        { id: 'home', name: 'Hogar' },
        { id: 'sports', name: 'Deportes' }
    ];

    const filteredProducts = products.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = selectedCategory === 'all' || p.category === selectedCategory;
        const matchesMinPrice = !minPrice || (p.price && p.price >= Number(minPrice));
        const matchesMaxPrice = !maxPrice || (p.price && p.price <= Number(maxPrice));
        return matchesSearch && matchesCategory && matchesMinPrice && matchesMaxPrice;
    });

    const avgMargin = filteredProducts.length > 0 
        ? Math.round(filteredProducts.reduce((acc, p) => acc + (p.margin || 0), 0) / filteredProducts.length)
        : 0;
    const avgCompetitors = filteredProducts.length > 0
        ? Math.round(filteredProducts.reduce((acc, p) => acc + (p.competitors || 0), 0) / filteredProducts.length)
        : 0;

    return (
        <SubscriptionGate minTier="GOLD" title="Winner Products (requiere GOLD)">
            <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(245,158,11,0.2)', 
                            borderRadius: '12px'
                        }}>
                            <Trophy size={32} style={{ color: 'var(--warning)' }} />
                        </div>
                        <div>
                            <h1 className="text-gradient" style={{ fontSize: '2.5rem', margin: 0 }}>Productos Ganadores</h1>
                            <p className="text-muted" style={{ marginTop: '0.25rem' }}>
                                Lista curada de productos de alto potencial para tu tienda
                            </p>
                        </div>
                    </div>
                </div>

                {/* EstadÃ­sticas RÃ¡pidas - Estilo Dashboard */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
                    <GlassCard style={{ textAlign: 'center', padding: '1.25rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(99,102,241,0.2)', 
                            borderRadius: '12px',
                            display: 'inline-flex',
                            marginBottom: '0.75rem'
                        }}>
                            <DollarSign size={24} style={{ color: 'var(--primary)' }} />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.5rem' }}>Productos Disponibles</p>
                        <h3 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>{filteredProducts.length}</h3>
                    </GlassCard>
                    <GlassCard style={{ textAlign: 'center', padding: '1.25rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(16,185,129,0.2)', 
                            borderRadius: '12px',
                            display: 'inline-flex',
                            marginBottom: '0.75rem'
                        }}>
                            <TrendingUp size={24} style={{ color: 'var(--success)' }} />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.5rem' }}>Margen Promedio</p>
                        <h3 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold', color: 'var(--success)' }}>
                            {avgMargin}%
                        </h3>
                    </GlassCard>
                    <GlassCard style={{ textAlign: 'center', padding: '1.25rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(245,158,11,0.2)', 
                            borderRadius: '12px',
                            display: 'inline-flex',
                            marginBottom: '0.75rem'
                        }}>
                            <Users size={24} style={{ color: 'var(--warning)' }} />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.5rem' }}>Competencia Promedio</p>
                        <h3 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                            {avgCompetitors}
                        </h3>
                    </GlassCard>
                    <GlassCard style={{ textAlign: 'center', padding: '1.25rem' }}>
                        <div style={{ 
                            padding: '0.75rem', 
                            background: 'rgba(236,72,153,0.2)', 
                            borderRadius: '12px',
                            display: 'inline-flex',
                            marginBottom: '0.75rem'
                        }}>
                            <BarChart3 size={24} style={{ color: 'var(--secondary)' }} />
                        </div>
                        <p className="text-muted" style={{ fontSize: '0.85rem', margin: 0, marginBottom: '0.5rem' }}>Oportunidades</p>
                        <h3 style={{ fontSize: '2rem', margin: 0, fontWeight: 'bold' }}>
                            {filteredProducts.filter(p => p.competitors <= 2).length}
                        </h3>
                    </GlassCard>
                </div>

                {/* Filtros y BÃºsqueda - Estilo GoldMine simplificado */}
                <GlassCard style={{ marginBottom: '2rem', padding: '1rem' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <div style={{ position: 'relative', flex: 1, minWidth: '250px' }}>
                            <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', zIndex: 1 }} />
                            <input 
                                type="text" 
                                placeholder="Buscar producto por nombre..." 
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="glass-input"
                                style={{ width: '100%', paddingLeft: '40px' }}
                            />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Filter size={18} style={{ color: 'var(--text-muted)' }} />
                            <select 
                                value={selectedCategory} 
                                onChange={(e) => setSelectedCategory(e.target.value)}
                                className="glass-select"
                                style={{ minWidth: '180px' }}
                            >
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                                ))}
                            </select>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>Precio:</span>
                            <input 
                                type="number" 
                                placeholder="Min" 
                                value={minPrice} 
                                onChange={(e) => setMinPrice(e.target.value)} 
                                className="glass-input" 
                                style={{ width: '90px', padding: '0.4rem 0.5rem', fontSize: '0.85rem' }} 
                            />
                            <span style={{ color: 'var(--text-muted)' }}>-</span>
                            <input 
                                type="number" 
                                placeholder="Max" 
                                value={maxPrice} 
                                onChange={(e) => setMaxPrice(e.target.value)} 
                                className="glass-input" 
                                style={{ width: '90px', padding: '0.4rem 0.5rem', fontSize: '0.85rem' }} 
                            />
                        </div>
                        <div style={{ 
                            display: 'flex', 
                            gap: '0.5rem', 
                            background: 'var(--glass-bg)', 
                            padding: '0.25rem',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-border)',
                            marginLeft: 'auto'
                        }}>
                            <button
                                onClick={() => setViewMode('grid')}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '6px',
                                    background: viewMode === 'grid' ? 'var(--primary)' : 'transparent',
                                    color: viewMode === 'grid' ? 'white' : 'var(--text-muted)',
                                    border: 'none',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    fontSize: '0.85rem'
                                }}
                            >
                                Grid
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: '6px',
                                    background: viewMode === 'list' ? 'var(--primary)' : 'transparent',
                                    color: viewMode === 'list' ? 'white' : 'var(--text-muted)',
                                    border: 'none',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    fontSize: '0.85rem'
                                }}
                            >
                                Lista
                            </button>
                        </div>
                    </div>
                </GlassCard>

                {/* Grid de Productos - Estilo Dashboard con cards mejoradas */}
                {viewMode === 'grid' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
                        {filteredProducts.map(p => (
                            <ProductCard key={p.id} product={p} />
                        ))}
                    </div>
                ) : (
                    <GlassCard padding="0">
                        <div style={{ overflowX: 'auto' }}>
                            <table className="glass-table" style={{ width: '100%' }}>
                                <thead>
                                    <tr>
                                        <th>Imagen</th>
                                        <th>Producto</th>
                                        <th>Precio</th>
                                        <th>Margen</th>
                                        <th>Competencia</th>
                                        <th>Crecimiento</th>
                                        <th>SaturaciÃ³n</th>
                                        <th>AcciÃ³n</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredProducts.map(p => (
                                        <tr key={p.id}>
                                            <td>
                                                <div style={{ width: 50, height: 50, borderRadius: 8, overflow: 'hidden', background: 'rgba(255,255,255,0.05)' }}>
                                                    {p.image ? (
                                                        <LazyImage src={p.image} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                                    ) : (
                                                        <ShoppingCart size={24} style={{ margin: 13, color: 'var(--text-muted)', opacity: 0.5 }} />
                                                    )}
                                                </div>
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{p.name}</div>
                                                <div className="text-muted" style={{ fontSize: '0.75rem' }}>ID: {p.id}</div>
                                            </td>
                                            <td style={{ fontWeight: 'bold' }}>${p.price?.toLocaleString()}</td>
                                            <td>
                                                <span className="badge badge-success">{p.margin}%</span>
                                            </td>
                                            <td>
                                                <CompetitorBadge count={p.competitors} />
                                            </td>
                                            <td style={{ color: 'var(--success)' }}>+{p.growth}%</td>
                                            <td>
                                                <span style={{ 
                                                    color: p.saturation === 'ALTA' ? 'var(--danger)' : (p.saturation === 'MEDIA' ? 'var(--warning)' : 'var(--success)'), 
                                                    fontWeight: 500,
                                                    fontSize: '0.85rem'
                                                }}>
                                                    {p.saturation || 'BAJA'}
                                                </span>
                                            </td>
                                            <td>
                                                <button 
                                                    className="btn-primary" 
                                                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                                                    onClick={() => p.url && window.open(p.url, '_blank')}
                                                >
                                                    <ExternalLink size={14} style={{ marginRight: '0.25rem' }} />
                                                    Ver
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </GlassCard>
                )}

                {filteredProducts.length === 0 && (
                    <GlassCard style={{ textAlign: 'center', padding: '3rem' }}>
                        <ShoppingCart size={48} className="text-muted" style={{ opacity: 0.5, marginBottom: '1rem' }} />
                        <p className="text-muted">No se encontraron productos con estos filtros.</p>
                    </GlassCard>
                )}
            </div>
        </SubscriptionGate>
    );
};

export default WinnerProducts;

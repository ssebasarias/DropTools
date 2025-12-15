import React, { useEffect, useState, useCallback } from 'react';
import { fetchGoldMine, searchVisualGoldMine, fetchCategories } from '../services/api';
import { ShoppingBag, Users, Search, Filter, Camera, X, UploadCloud } from 'lucide-react';
import './Dashboard.css';

const GoldMine = () => {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(false);
    const [categories, setCategories] = useState([]);

    // Filtros
    const [search, setSearch] = useState('');
    const [competitorRange, setCompetitorRange] = useState('0-20');
    const [selectedCategory, setSelectedCategory] = useState('all');

    // Visual Search State
    const [visualImage, setVisualImage] = useState(null);
    const [isVisualMode, setIsVisualMode] = useState(false);

    // Paginación
    const [offset, setOffset] = useState(0);
    const LIMIT = 50;
    const [hasMore, setHasMore] = useState(true);

    // Cargar Categorías al inicio
    useEffect(() => {
        fetchCategories().then(setCategories);
    }, []);

    const loadData = useCallback(async (isNewSearch = false) => {
        if (isVisualMode) return; // Visual search tiene su propio flow

        setLoading(true);
        try {
            const [min, max] = competitorRange.split('-').map(Number);
            const currentOffset = isNewSearch ? 0 : offset;

            const params = {
                q: search,
                category: selectedCategory,
                min_comp: min,
                max_comp: max,
                limit: LIMIT,
                offset: currentOffset
            };

            const newData = await fetchGoldMine(params);

            if (isNewSearch) {
                setOpportunities(newData);
                setOffset(LIMIT);
            } else {
                setOpportunities(prev => [...prev, ...newData]);
                setOffset(prev => prev + LIMIT);
            }

            if (newData.length < LIMIT) setHasMore(false);
            else setHasMore(true);

        } catch (error) {
            console.error("Failed to load gold mine");
        } finally {
            setLoading(false);
        }
    }, [search, competitorRange, selectedCategory, offset, isVisualMode]);

    // Disparar búsqueda al cambiar filtros (Debounce manual simple)
    useEffect(() => {
        if (!isVisualMode) {
            const timer = setTimeout(() => {
                loadData(true);
            }, 500);
            return () => clearTimeout(timer);
        }
    }, [search, competitorRange, selectedCategory, isVisualMode]);

    // Handle Visual Search
    const handleImageUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoading(true);
        setIsVisualMode(true);
        setVisualImage(URL.createObjectURL(file));
        setOpportunities([]); // Clear previous text results

        try {
            const results = await searchVisualGoldMine(file);
            setOpportunities(results);
            setHasMore(false); // Visual search is usually one-shot top 50
        } catch (err) {
            console.error(err);
            alert("Error in visual search");
            setIsVisualMode(false);
            setVisualImage(null);
            loadData(true);
        } finally {
            setLoading(false);
        }
    };

    const clearVisualSearch = () => {
        setVisualImage(null);
        setIsVisualMode(false);
        loadData(true); // Restore text search
    };

    return (
        <div className="dashboard-container">
            <div className="header-greeting">
                <h1 className="text-gradient">Gold Mine Hunter</h1>
                <p>Encuentra productos rentables. {isVisualMode ? "Modo: Búsqueda Visual por IA" : "Filtra, analiza y ataca."}</p>
            </div>

            {/* Filter Bar */}
            <div className="glass-card" style={{ display: 'flex', gap: '1rem', padding: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>

                {/* Visual Search Toggle */}
                <div style={{ marginRight: '1rem' }}>
                    <input
                        type="file"
                        id="visual-upload"
                        style={{ display: 'none' }}
                        accept="image/*"
                        onChange={handleImageUpload}
                    />
                    {!isVisualMode ? (
                        <label htmlFor="visual-upload" className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                            <Camera size={18} />
                            <span>Visual Search</span>
                        </label>
                    ) : (
                        <button onClick={clearVisualSearch} className="btn-secondary" style={{ background: '#ef4444', borderColor: '#ef4444', color: 'white', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <X size={18} />
                            <span>Clear Image</span>
                        </button>
                    )}
                </div>

                {/* Text Search (Disabled in Visual Mode) */}
                <div style={{ position: 'relative', flex: 1, opacity: isVisualMode ? 0.5 : 1 }}>
                    <Search size={18} style={{ position: 'absolute', left: 12, top: 10, color: '#94a3b8' }} />
                    <input
                        type="text"
                        placeholder="Buscar producto por nombre..."
                        value={search}
                        disabled={isVisualMode}
                        onChange={(e) => setSearch(e.target.value)}
                        className="glass-select"
                        style={{ width: '100%', paddingLeft: 40 }}
                    />
                </div>

                {/* Filters (Disabled in Visual Mode) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto', opacity: isVisualMode ? 0.5 : 1 }}>
                    <Filter size={18} color="#94a3b8" />

                    {/* Category Filter */}
                    <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        disabled={isVisualMode}
                        className="glass-select"
                        style={{ maxWidth: 150 }}
                    >
                        <option value="all">Todas las Categorías</option>
                        {categories.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>

                    <span style={{ fontSize: '0.9rem', color: '#94a3b8', marginLeft: '0.5rem' }}>Comp:</span>
                    <select
                        value={competitorRange}
                        onChange={(e) => setCompetitorRange(e.target.value)}
                        disabled={isVisualMode}
                        className="glass-select"
                    >
                        <option value="0-1">Solo yo (0-1)</option>
                        <option value="0-3">Baja (0-3)</option>
                        <option value="0-5">Media (0-5)</option>
                        <option value="0-20">Todas (0-20)</option>
                    </select>
                </div>
            </div>

            {/* Visual Preview Area */}
            {isVisualMode && visualImage && (
                <div className="glass-card" style={{ marginBottom: '1rem', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(16, 185, 129, 0.1)' }}>
                    <div style={{ width: 60, height: 60, borderRadius: 8, overflow: 'hidden' }}>
                        <img src={visualImage} alt="Search Query" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>
                    <div>
                        <h4 style={{ color: '#10b981', marginBottom: 2 }}>Buscando visualmente...</h4>
                        <span style={{ fontSize: '0.8rem', color: '#ccc' }}>Analizando patrones visuales con IA para encontrar similitudes.</span>
                    </div>
                </div>
            )}

            <div className="glass-card">
                <div style={{ overflowX: 'auto' }}>
                    <table className="glass-table">
                        <thead>
                            <tr>
                                <th>Image</th>
                                <th>Product Name</th>
                                <th>Price</th>
                                <th>{isVisualMode ? "Similarity" : "Margin"}</th>
                                <th>Supplier</th>
                                <th>Competitors</th>
                                <th>Saturation</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {opportunities.map((op, idx) => (
                                <tr key={`${op.id}-${idx}`}>
                                    <td>
                                        <div style={{ width: 50, height: 50, borderRadius: 8, overflow: 'hidden', background: '#222' }}>
                                            {op.image ? (
                                                <img src={op.image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                            ) : (
                                                <ShoppingBag size={24} style={{ margin: 12, color: '#666' }} />
                                            )}
                                        </div>
                                    </td>
                                    <td style={{ maxWidth: 300 }}>
                                        <div style={{ fontWeight: 600, color: '#fff' }}>{op.title}</div>
                                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>ID: {op.id}</div>
                                    </td>
                                    <td style={{ fontWeight: 'bold' }}>${parseInt(op.price || 0).toLocaleString()}</td>
                                    <td>
                                        {isVisualMode ? (
                                            <span className="badge" style={{ background: '#3b82f6', color: 'white' }}>{op.similarity}</span>
                                        ) : (
                                            <span className="badge badge-success">{op.profit_margin}</span>
                                        )}
                                    </td>
                                    <td style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
                                        {op.supplier}
                                    </td>
                                    <td>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            <UsersIcon count={op.competitors} />
                                            <span>{op.competitors}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <span style={{
                                            color: op.saturation === 'ALTA' ? '#ef4444' : (op.saturation === 'MEDIA' ? '#f59e0b' : '#10b981'),
                                            fontWeight: 500
                                        }}>
                                            {op.saturation || 'BAJA'}
                                        </span>
                                    </td>
                                    <td>
                                        <button className="btn-primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
                                            Ver
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {loading && <div style={{ textAlign: 'center', padding: '2rem' }}>Cargando datos...</div>}

                {!loading && opportunities.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                        {isVisualMode ? "No se encontraron productos similares visualmente." : "No se encontraron productos con estos filtros."}
                    </div>
                )}

                {hasMore && !loading && !isVisualMode && opportunities.length > 0 && (
                    <div style={{ textAlign: 'center', padding: '1rem' }}>
                        <button
                            className="btn-primary"
                            onClick={() => loadData(false)}
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)' }}
                        >
                            Cargar más productos...
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

const UsersIcon = ({ count }) => {
    let color = '#10b981';
    if (count > 2) color = '#f59e0b';
    if (count > 5) color = '#ef4444';

    return (
        <Users size={16} color={color} />
    );
};

export default GoldMine;

import React, { useEffect, useState, useCallback } from 'react';
import { fetchGoldMine, fetchGoldMineStats, searchVisualGoldMine, fetchCategories } from '../services/api';
import { ShoppingBag, Users, Search, Filter, Camera, X } from 'lucide-react';
import LazyImage from '../components/common/LazyImage';
import './Dashboard.css';

const GoldMine = () => {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(false);
    const [categories, setCategories] = useState([]);

    // Filtros
    const [search, setSearch] = useState('');
    const [competitorRange, setCompetitorRange] = useState('0-1000');
    const [selectedCompetitor, setSelectedCompetitor] = useState(null); // null = All
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [minPrice, setMinPrice] = useState('');
    const [maxPrice, setMaxPrice] = useState('');

    // Visual Search State
    const [visualImage, setVisualImage] = useState(null);
    const [isVisualMode, setIsVisualMode] = useState(false);

    // Paginación
    const [currentPage, setCurrentPage] = useState(1);
    const [totalResults, setTotalResults] = useState(0);
    const [competitorStats, setCompetitorStats] = useState({});
    const ITEMS_PER_PAGE = 20;

    // Cargar Categorías al inicio
    useEffect(() => {
        fetchCategories().then(setCategories);
    }, []);

    const loadData = useCallback(async (page = 1) => {
        if (isVisualMode) return;

        setLoading(true);
        try {
            const [min, max] = competitorRange.split('-').map(Number);
            const offset = (page - 1) * ITEMS_PER_PAGE;

            const params = {
                q: search,
                category: selectedCategory,
                min_comp: min,
                max_comp: max,
                limit: ITEMS_PER_PAGE,
                offset: offset
            };

            if (minPrice && Number(minPrice) > 0) params.min_price = minPrice;
            if (maxPrice && Number(maxPrice) > 0) params.max_price = maxPrice;

            const newData = await fetchGoldMine(params);

            setOpportunities(newData);
            setCurrentPage(page);

            // Stats are now fetched globally in a separate effect


            if (newData.length < ITEMS_PER_PAGE) {
                setTotalResults(offset + newData.length);
            } else {
                setTotalResults((page + 10) * ITEMS_PER_PAGE);
            }

        } catch (error) {
            console.error("Failed to load gold mine");
        } finally {
            setLoading(false);
        }
    }, [search, competitorRange, selectedCategory, minPrice, maxPrice, isVisualMode]);

    useEffect(() => {
        if (!isVisualMode) {
            const timer = setTimeout(() => {
                loadData(1);
            }, 500);
            return () => clearTimeout(timer);
        }
    }, [search, competitorRange, selectedCategory, minPrice, maxPrice, isVisualMode]);

    // Cargar Estadísticas Globales (Independiente de la paginación y filtro de competidores actual)
    useEffect(() => {
        if (isVisualMode) return;

        const loadStats = async () => {
            try {
                const params = {
                    q: search,
                    category: selectedCategory,
                };
                if (minPrice && Number(minPrice) > 0) params.min_price = minPrice;
                if (maxPrice && Number(maxPrice) > 0) params.max_price = maxPrice;

                const globalStats = await fetchGoldMineStats(params);
                setCompetitorStats(globalStats);
            } catch (error) {
                console.error("Error loading stats", error);
            }
        };

        const timer = setTimeout(loadStats, 500);
        return () => clearTimeout(timer);
    }, [search, selectedCategory, minPrice, maxPrice, isVisualMode]);

    const handleImageUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoading(true);
        setIsVisualMode(true);
        setVisualImage(URL.createObjectURL(file));
        setOpportunities([]);

        try {
            const results = await searchVisualGoldMine(file);
            setOpportunities(results);
            setTotalResults(results.length);
        } catch (err) {
            console.error(err);
            alert("Error in visual search");
            setIsVisualMode(false);
            setVisualImage(null);
            loadData(1);
        } finally {
            setLoading(false);
        }
    };

    const clearVisualSearch = () => {
        setVisualImage(null);
        setIsVisualMode(false);
        loadData(1);
    };

    const totalPages = Math.ceil(totalResults / ITEMS_PER_PAGE);

    const getPageNumbers = () => {
        const pages = [];
        const maxVisible = 7;

        if (totalPages <= maxVisible) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            if (currentPage <= 4) {
                for (let i = 1; i <= 5; i++) pages.push(i);
                pages.push('...');
                pages.push(totalPages);
            } else if (currentPage >= totalPages - 3) {
                pages.push(1);
                pages.push('...');
                for (let i = totalPages - 4; i <= totalPages; i++) pages.push(i);
            } else {
                pages.push(1);
                pages.push('...');
                for (let i = currentPage - 1; i <= currentPage + 1; i++) pages.push(i);
                pages.push('...');
                pages.push(totalPages);
            }
        }
        return pages;
    };

    return (
        <div className="dashboard-container">
            <div className="header-greeting">
                <h1 className="text-gradient">Gold Mine Hunter</h1>
                <p>Encuentra productos rentables. {isVisualMode ? "Modo: Búsqueda Visual por IA" : "Filtra, analiza y ataca."}</p>
            </div>

            <div className="glass-card" style={{ display: 'flex', gap: '1rem', padding: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ marginRight: '1rem' }}>
                    <input type="file" id="visual-upload" style={{ display: 'none' }} accept="image/*" onChange={handleImageUpload} />
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

                <div style={{ position: 'relative', flex: 1, opacity: isVisualMode ? 0.5 : 1 }}>
                    <Search size={18} style={{ position: 'absolute', left: 12, top: 10, color: '#94a3b8' }} />
                    <input type="text" placeholder="Buscar producto por nombre..." value={search} disabled={isVisualMode} onChange={(e) => setSearch(e.target.value)} className="glass-select" style={{ width: '100%', paddingLeft: 40 }} />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto', opacity: isVisualMode ? 0.5 : 1, flexWrap: 'wrap' }}>
                    <Filter size={18} color="#94a3b8" />

                    <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} disabled={isVisualMode} className="glass-select" style={{ maxWidth: 150 }}>
                        <option value="all">Todas las Categorías</option>
                        {categories.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <span style={{ fontSize: '0.85rem', color: '#94a3b8', marginLeft: '0.5rem' }}>Precio:</span>
                        <input type="number" placeholder="Min" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} disabled={isVisualMode} className="glass-select" style={{ width: '90px', padding: '0.4rem 0.5rem', fontSize: '0.85rem' }} />
                        <span style={{ color: '#64748b' }}>-</span>
                        <input type="number" placeholder="Max" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} disabled={isVisualMode} className="glass-select" style={{ width: '90px', padding: '0.4rem 0.5rem', fontSize: '0.85rem' }} />
                    </div>

                </div>
            </div>

            {/* Interactive Competitor Distribution Bar (Replacing the old Select) */}
            {!loading && !isVisualMode && Object.keys(competitorStats).length > 0 && (
                <div className="glass-panel" style={{ marginBottom: '1rem', padding: '0.75rem 1rem' }}>
                    <div className="custom-scrollbar" style={{
                        display: 'flex',
                        overflowX: 'auto',
                        gap: '1.5rem',
                        alignItems: 'center',
                        paddingBottom: '0.75rem' // Espacio para la scrollbar
                    }}>
                        <style>
                            {`
                                .custom-scrollbar::-webkit-scrollbar {
                                    height: 6px;
                                }
                                .custom-scrollbar::-webkit-scrollbar-track {
                                    background: rgba(255, 255, 255, 0.02);
                                    border-radius: 10px;
                                }
                                .custom-scrollbar::-webkit-scrollbar-thumb {
                                    background: rgba(255, 255, 255, 0.15);
                                    border-radius: 10px;
                                }
                                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                                    background: rgba(255, 255, 255, 0.25);
                                }
                            `}
                        </style>

                        {/* Option: ALL */}
                        <div
                            onClick={() => {
                                setSelectedCompetitor(null);
                                setCompetitorRange('0-1000');
                            }}
                            style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '0.25rem',
                                cursor: 'pointer',
                                opacity: selectedCompetitor === null ? 1 : 0.6,
                                borderBottom: selectedCompetitor === null ? '2px solid #6366f1' : '2px solid transparent',
                                paddingBottom: '0.5rem',
                                transition: 'all 0.2s',
                                minWidth: '70px'
                            }}
                        >
                            <div style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '50%',
                                background: selectedCompetitor === null ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255,255,255,0.03)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <Users size={18} color={selectedCompetitor === null ? '#6366f1' : '#94a3b8'} />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1.1 }}>
                                <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>Todos</span>
                                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{totalResults}</span>
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ width: 1, height: '30px', background: 'rgba(255,255,255,0.08)' }}></div>

                        {/* Competitor Groups */}
                        {Object.entries(competitorStats)
                            .sort((a, b) => Number(a[0]) - Number(b[0]))
                            .map(([competitors, count]) => {
                                const compNum = Number(competitors);
                                const isSelected = selectedCompetitor === compNum;

                                let iconColor = '#10b981'; // Green (Low)
                                if (compNum > 2) iconColor = '#f59e0b'; // Medium
                                if (compNum > 5) iconColor = '#ef4444'; // High

                                let glowColor = `rgba(${compNum > 5 ? '239, 68, 68' : (compNum > 2 ? '245, 158, 11' : '16, 185, 129')}, 0.15)`;

                                return (
                                    <div
                                        key={competitors}
                                        onClick={() => {
                                            setSelectedCompetitor(compNum);
                                            setCompetitorRange(`${compNum}-${compNum}`);
                                        }}
                                        style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            cursor: 'pointer',
                                            minWidth: '70px',
                                            paddingBottom: '0.5rem',
                                            borderBottom: isSelected ? `2px solid ${iconColor}` : '2px solid transparent',
                                            opacity: (selectedCompetitor !== null && !isSelected) ? 0.4 : 1,
                                            transform: isSelected ? 'scale(1.05)' : 'scale(1)',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <div style={{
                                            width: '36px',
                                            height: '36px',
                                            borderRadius: '50%',
                                            background: isSelected ? glowColor : 'rgba(255,255,255,0.03)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            boxShadow: isSelected ? `0 0 10px ${glowColor}` : 'none'
                                        }}>
                                            <Users size={18} color={iconColor} />
                                        </div>

                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1.1 }}>
                                            <span style={{
                                                color: iconColor,
                                                fontSize: '0.85rem',
                                                fontWeight: '600',
                                                textShadow: isSelected ? `0 0 8px ${iconColor}` : 'none'
                                            }}>
                                                {compNum} Comp.
                                            </span>
                                            <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                                                {count}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                    </div>
                </div>
            )}


            <div className="glass-card">
                {!loading && opportunities.length > 0 && (
                    <div style={{ padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', fontSize: '0.9rem' }}>
                        Mostrando {((currentPage - 1) * ITEMS_PER_PAGE) + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, totalResults)} de {totalResults}+ resultados
                    </div>
                )}

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
                                                <LazyImage
                                                    src={op.image}
                                                    alt=""
                                                    style={{ width: '100%', height: '100%' }}
                                                />
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
                                    <td style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{op.supplier}</td>
                                    <td>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            <UsersIcon count={op.competitors} />
                                            <span>{op.competitors}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <span style={{ color: op.saturation === 'ALTA' ? '#ef4444' : (op.saturation === 'MEDIA' ? '#f59e0b' : '#10b981'), fontWeight: 500 }}>
                                            {op.saturation || 'BAJA'}
                                        </span>
                                    </td>
                                    <td>
                                        <button className="btn-primary" onClick={() => window.open(`https://app.dropi.co/products/${op.id}`, '_blank')} style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
                                            Ver en Dropi
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {loading && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#ccc' }}>
                        {isVisualMode ? "Analizando imagen..." : "Cargando datos..."}
                    </div>
                )}

                {!loading && opportunities.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                        {isVisualMode ? "No se encontraron productos similares visualmente." : "No se encontraron productos con estos filtros."}
                    </div>
                )}

                {!loading && !isVisualMode && opportunities.length > 0 && totalPages > 1 && (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', padding: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                        <button onClick={() => loadData(currentPage - 1)} disabled={currentPage === 1} className="btn-secondary" style={{ padding: '0.5rem 1rem', opacity: currentPage === 1 ? 0.5 : 1, cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}>
                            ← Anterior
                        </button>

                        {getPageNumbers().map((page, idx) => (
                            page === '...' ? (
                                <span key={`ellipsis-${idx}`} style={{ color: '#64748b', padding: '0 0.5rem' }}>...</span>
                            ) : (
                                <button key={page} onClick={() => loadData(page)} className="btn-secondary" style={{ padding: '0.5rem 0.75rem', minWidth: '40px', background: currentPage === page ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255,255,255,0.05)', border: currentPage === page ? '1px solid #667eea' : '1px solid var(--glass-border)', fontWeight: currentPage === page ? 'bold' : 'normal' }}>
                                    {page}
                                </button>
                            )
                        ))}

                        <button onClick={() => loadData(currentPage + 1)} disabled={currentPage === totalPages} className="btn-secondary" style={{ padding: '0.5rem 1rem', opacity: currentPage === totalPages ? 0.5 : 1, cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}>
                            Siguiente →
                        </button>
                    </div>
                )}
            </div>
        </div >
    );
};

const UsersIcon = ({ count }) => {
    let color = '#10b981';
    if (count > 2) color = '#f59e0b';
    if (count > 5) color = '#ef4444';
    return <Users size={16} color={color} />;
};

export default GoldMine;

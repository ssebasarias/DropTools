import React from 'react';
import { Star, ShoppingCart, TrendingUp, ExternalLink } from 'lucide-react';

const ProductCard = ({ product }) => (
    <div className="glass-card product-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
        <div style={{ height: '160px', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* Placeholder Image */}
            <ShoppingCart size={48} className="text-muted" opacity={0.5} />
        </div>
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '600' }}>{product.name}</h3>
                <span className="badge badge-success">High Demand</span>
            </div>
            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>{product.description}</p>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto' }}>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.9rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--success)' }}>
                        <TrendingUp size={16} /> +{product.growth}%
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--warning)' }}>
                        <Star size={16} /> {product.rating}
                    </span>
                </div>
                <button className="btn-primary" style={{ padding: '0.5rem', borderRadius: '8px' }}>
                    <ExternalLink size={18} />
                </button>
            </div>
        </div>
    </div>
);

const WinnerProducts = () => {
    // Mock Data
    const products = Array(6).fill(null).map((_, i) => ({
        id: i,
        name: `Winner Product #${i + 1}`,
        description: 'Trending product with high conversion rate and low competition.',
        growth: 15 + i * 2,
        rating: 4.8
    }));

    return (
        <div style={{ padding: '2rem' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Winner Products</h1>
                <p className="text-muted">Curated list of high-potential products for your store.</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {products.map(p => (
                    <ProductCard key={p.id} product={p} />
                ))}
            </div>
        </div>
    );
};

export default WinnerProducts;

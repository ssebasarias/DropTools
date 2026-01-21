import React from 'react';
import { ArrowRight, Target } from 'lucide-react';
import LazyImage from '../../common/LazyImage';
import GlassCard from '../../common/GlassCard';

const OpportunityCard = ({ product }) => {
    // const navigate = useNavigate(); // If needed for internal navigation

    return (
        <GlassCard
            padding="0"
            hoverEffect={true}
            onClick={() => window.open(`https://app.dropi.co/products/${product.id}`, '_blank')}
            style={{ cursor: 'pointer', overflow: 'hidden', position: 'relative' }}
        >
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

            <style jsx>{`
                .card-badge {
                    position: absolute; top: 10px; left: 10px; z-index: 2;
                    background: #10b981; color: white; padding: 2px 8px; border-radius: 4px;
                    font-size: 0.7rem; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .img-container {
                    height: 180px; width: 100%; position: relative; background: #000;
                }
                .overlay {
                    position: absolute; inset: 0; background: rgba(0,0,0,0.4);
                    display: flex; align-items: center; justify-content: center;
                    opacity: 0; transition: opacity 0.2s;
                }
                .img-container:hover .overlay { opacity: 1; }
                
                .btn-primary {
                    background: #6366f1; color: white; border: none; padding: 0.5rem 1rem;
                    border-radius: 6px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;
                }

                .card-content { padding: 1rem; }
                .card-content h4 { font-size: 0.95rem; margin: 0 0 0.75rem 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff; }
                
                .metrics { display: flex; justify-content: space-between; margin-bottom: 0.75rem; }
                .metric { display: flex; flex-direction: column; }
                .metric.highlight .value { color: #10b981; }
                .metric .label { font-size: 0.7rem; color: #64748b; }
                .metric .value { font-weight: bold; font-size: 0.9rem; color: #e2e8f0; }

                .competitors-tag { 
                    display: flex; align-items: center; gap: 4px; font-size: 0.75rem; color: #94a3b8; 
                    background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; width: fit-content;
                }
            `}</style>
        </GlassCard>
    );
};

export default OpportunityCard;

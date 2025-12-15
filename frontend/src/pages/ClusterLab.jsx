import React, { useState } from 'react';
import { Check, X, Split, Layers, AlertCircle } from 'lucide-react';
import './ClusterLab.css';

// Datos Dummy para diseño (hasta conectar API)
const DUMMY_CLUSTERS = [
    {
        cluster_id: 101,
        confidence: '98%',
        method: 'AI_VISUAL_STRONG',
        items: [
            { id: 4321, title: "Audífonos Bluetooth F9-5 TWS", sku: "F9-5-BLK", price: 12.50, image: "https://via.placeholder.com/150", supplier: "TechStore" },
            { id: 8765, title: "F9 TWS Auriculares Inalámbricos", sku: "AU-F9", price: 14.00, image: "https://via.placeholder.com/150", supplier: "Importadora XYZ" },
            { id: 9988, title: "Audífonos Gamer F9", sku: "GAMER-F9", price: 11.00, image: "https://via.placeholder.com/150", supplier: "Bodega Central" }
        ]
    },
    {
        cluster_id: 205,
        confidence: '85%',
        method: 'AI_HYBRID',
        items: [
            { id: 1122, title: "Smart Watch T500", sku: "T500-PINK", price: 18.00, image: "https://via.placeholder.com/150", supplier: "RelojesYA" },
            { id: 3344, title: "Reloj Inteligente T500 Series 7", sku: "SW-T500", price: 21.00, image: "https://via.placeholder.com/150", supplier: "GadgetWorld" }
        ]
    }
];

const ClusterCard = ({ cluster }) => {
    return (
        <div className="glass-card cluster-card">
            <div className="cluster-header">
                <div className="cluster-info">
                    <h3>Cluster #{cluster.cluster_id}</h3>
                    <div className="cluster-meta">
                        <span className="badge badge-success">{cluster.confidence} Match</span>
                        <span className="method-tag">{cluster.method}</span>
                    </div>
                </div>
                <div className="cluster-actions">
                    <button className="btn-icon check" title="Confirmar Cluster"><Check size={18} /></button>
                    <button className="btn-icon split" title="Separar (Falso Positivo)"><Split size={18} /></button>
                </div>
            </div>

            <div className="cluster-items-grid">
                {cluster.items.map((item, idx) => (
                    <div key={item.id} className="cluster-item">
                        <div className="item-image">
                            <img src={item.image} alt="Product" />
                            {idx === 0 && <span className="leader-badge">Líder</span>}
                        </div>
                        <div className="item-details">
                            <h4>{item.title}</h4>
                            <div className="item-pricing">
                                <span className="sku">{item.sku}</span>
                                <span className="price">${item.price.toFixed(2)}</span>
                            </div>
                            <span className="supplier">{item.supplier}</span>
                        </div>
                        <button className="remove-item-btn"><X size={14} /></button>
                    </div>
                ))}
            </div>
        </div>
    );
};

const ClusterLab = () => {
    return (
        <div className="cluster-lab-container">
            <div className="header-greeting">
                <h1 className="text-gradient">Cluster Laboratory</h1>
                <p>Auditoría visual de agrupaciones realizadas por la IA.</p>
            </div>

            <div className="lab-toolbar glass-panel">
                <div className="stats">
                    <span><strong>124</strong> Pendientes de Revisión</span>
                    <span><strong>98%</strong> Precisión Promedio</span>
                </div>
                <div className="filters">
                    <button className="btn-filter active">Low Confidence</button>
                    <button className="btn-filter">High Value</button>
                </div>
            </div>

            <div className="clusters-feed">
                {DUMMY_CLUSTERS.map(c => <ClusterCard key={c.cluster_id} cluster={c} />)}
            </div>

            <div className="empty-state-lab" style={{ display: 'none' }}>
                <AlertCircle size={48} color="var(--text-muted)" />
                <p>Todos los clusters han sido verificados.</p>
            </div>
        </div>
    );
};

export default ClusterLab;

import React from 'react';
import { Server, Database, Activity, Cpu, CircuitBoard, Layers, ShoppingBag, Brain } from 'lucide-react';
import { useSystemStatus } from '../hooks/useSystemStatus';
import UnifiedWorkerCard from '../components/domain/system/UnifiedWorkerCard';
import './Dashboard.css';

const Section = ({ title, services, logs, stats }) => (
    <div style={{ marginBottom: '3rem' }}>
        <h2 style={{
            marginBottom: '1.5rem',
            color: '#fff',
            fontSize: '1.5rem',
            borderLeft: '4px solid #3b82f6',
            paddingLeft: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
        }}>
            {title}
            <div style={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, rgba(59,130,246,0.3) 0%, transparent 100%)', marginLeft: '1rem' }}></div>
        </h2>
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            gap: '1.5rem'
        }}>
            {services.map(svc => (
                <UnifiedWorkerCard
                    key={svc.id}
                    {...svc}
                    logs={logs}
                    displayParams={stats[svc.id]}
                />
            ))}
        </div>
    </div>
);

const SystemStatus = () => {
    const { logs, stats, loading } = useSystemStatus();

    // Configuration of services divided by logic
    const collectionServices = [
        { id: 'scraper', name: 'Web Scraper', icon: Activity, actions: ['restart'], color: '#10b981' }, // Green
        { id: 'shopify', name: 'Shopify Finder', icon: ShoppingBag, actions: ['restart'], color: '#84cc16' }, // Lime
        { id: 'loader', name: 'Data Loader', icon: Database, actions: ['restart'], color: '#3b82f6' }, // Blue
        { id: 'vectorizer', name: 'AI Vectorizer', icon: Cpu, actions: ['restart'], color: '#a855f7' }, // Purple
    ];

    const analysisServices = [
        { id: 'classifier', name: 'Agent 1: Classifier', icon: Layers, actions: ['restart'], color: '#ec4899' }, // Pink
        { id: 'clusterizer', name: 'Agent 2: Clusterizer', icon: Server, actions: ['restart'], color: '#14b8a6' }, // Teal
        { id: 'ai_trainer', name: 'AI Trainer (Cerebro)', icon: Brain, actions: ['restart'], color: '#f59e0b' }, // Amber
    ];

    if (loading && Object.keys(stats).length === 0) {
        return (
            <div style={{ padding: '2rem', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                <CircuitBoard className="spin" size={32} />
                <span style={{ marginLeft: '1rem', fontSize: '1.2rem' }}>Initializing Control Center...</span>
            </div>
        );
    }

    return (
        <div className="dashboard-container" style={{ maxWidth: '1800px', margin: '0 auto', padding: '2rem' }}>
            {/* Header */}
            <div className="header-greeting" style={{ textAlign: 'center', marginBottom: '4rem', position: 'relative' }}>
                <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    width: '600px', height: '100px', background: '#3b82f6', filter: 'blur(100px)', opacity: 0.1, zIndex: -1
                }}></div>
                <h1 style={{
                    fontSize: '3rem',
                    background: 'linear-gradient(to right, #fff, #94a3b8)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    marginBottom: '0.5rem',
                    letterSpacing: '-1px'
                }}>
                    System Control
                </h1>
                <p style={{ color: '#64748b', fontSize: '1.1rem' }}>Real-time Infrastructure Operations & Telemetry</p>
            </div>

            {/* SECTIONS */}
            <Section title="Recolección" services={collectionServices} logs={logs} stats={stats} />
            <Section title="Análisis" services={analysisServices} logs={logs} stats={stats} />

        </div>
    );
};

export default SystemStatus;

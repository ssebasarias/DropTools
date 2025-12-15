import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import GoldMine from './pages/GoldMine';
import ClusterLab from './pages/ClusterLab';
import SystemStatus from './pages/SystemStatus';

const Placeholder = ({ title }) => (
  <div style={{ padding: '2rem' }}>
    <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>{title}</h1>
    <p style={{ color: '#94a3b8' }}>Work in progress...</p>
  </div>
);

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="gold-mine" element={<GoldMine />} />
        <Route path="cluster-lab" element={<ClusterLab />} />
        <Route path="system-status" element={<SystemStatus />} />
      </Route>
    </Routes>
  );
}

export default App;

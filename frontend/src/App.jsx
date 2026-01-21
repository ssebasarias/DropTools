import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import GoldMine from './pages/GoldMine';
import ClusterLab from './pages/ClusterLab';
import SystemStatus from './pages/SystemStatus';

// Auth Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';

// User Pages
import UserLayout from './components/layout/UserLayout';
import WinnerProducts from './pages/user/WinnerProducts';
import ReporterConfig from './pages/user/ReporterConfig';
import ReportAnalysis from './pages/user/ReportAnalysis';
import Settings from './pages/Settings';

import Subscriptions from './pages/Subscriptions';

import LandingPage from './pages/LandingPage';

import RequireAuth from './components/auth/RequireAuth';
import RequireAdmin from './components/auth/RequireAdmin';
import RequireUser from './components/auth/RequireUser';
import RequireTier from './components/auth/RequireTier';

function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Admin Routes */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireAdmin>
              <MainLayout />
            </RequireAdmin>
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="gold-mine" element={<GoldMine />} />
        <Route path="cluster-lab" element={<ClusterLab />} />
        <Route path="system-status" element={<SystemStatus />} />
        <Route path="settings" element={<Settings type="admin" />} />
      </Route>

      {/* User Routes */}
      <Route
        path="/user"
        element={
          <RequireAuth>
            <RequireUser>
              <UserLayout />
            </RequireUser>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/user/dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <RequireTier minTier="GOLD">
              <WinnerProducts />
            </RequireTier>
          }
        />
        <Route path="reporter-setup" element={<ReporterConfig />} />
        <Route
          path="analysis"
          element={
            <RequireTier minTier="SILVER">
              <ReportAnalysis />
            </RequireTier>
          }
        />
        <Route path="subscriptions" element={<Subscriptions />} />
        <Route path="settings" element={<Settings type="user" />} />
      </Route>
    </Routes>
  );
}

export default App;

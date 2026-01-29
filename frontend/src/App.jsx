import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import ErrorBoundary from './components/common/ErrorBoundary';

// Lazy load heavy pages for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const GoldMine = lazy(() => import('./pages/GoldMine'));
const ClusterLab = lazy(() => import('./pages/ClusterLab'));
const SystemStatus = lazy(() => import('./pages/SystemStatus'));

// Auth Pages - Keep synchronous for faster initial load
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';

// User Pages - Lazy load
const UserLayout = lazy(() => import('./components/layout/UserLayout'));
const ClientDashboard = lazy(() => import('./pages/user/ClientDashboard'));
const WinnerProducts = lazy(() => import('./pages/user/WinnerProducts'));
const ReporterConfig = lazy(() => import('./pages/user/ReporterConfig'));
const ReportAnalysis = lazy(() => import('./pages/user/ReportAnalysis'));
const Settings = lazy(() => import('./pages/Settings'));

const Subscriptions = lazy(() => import('./pages/Subscriptions'));
const LandingPage = lazy(() => import('./pages/LandingPage'));

import RequireAuth from './components/auth/RequireAuth';
import RequireAdmin from './components/auth/RequireAdmin';
import RequireUser from './components/auth/RequireUser';
import RequireTier from './components/auth/RequireTier';

// Loading component for Suspense fallback
const LoadingSpinner = () => (
  <div style={{ 
    display: 'flex', 
    flexDirection: 'column', 
    alignItems: 'center', 
    justifyContent: 'center', 
    height: '50vh', 
    color: '#6366f1' 
  }}>
    <div className="spin" style={{
      width: '48px',
      height: '48px',
      border: '4px solid rgba(99, 102, 241, 0.2)',
      borderTop: '4px solid #6366f1',
      borderRadius: '50%',
      animation: 'spin 1s infinite linear'
    }} />
    <p style={{ marginTop: '1rem' }}>Cargando...</p>
    <style>{`
      @keyframes spin {
        100% { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public Routes */}
        <Route 
          path="/" 
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <LandingPage />
            </Suspense>
          } 
        />
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
          <Route 
            index 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <Dashboard />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="gold-mine" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <GoldMine />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="cluster-lab" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <ClusterLab />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="system-status" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <SystemStatus />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="settings" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <Settings type="admin" />
                </ErrorBoundary>
              </Suspense>
            } 
          />
        </Route>

        {/* User Routes */}
        <Route
          path="/user"
          element={
            <RequireAuth>
              <RequireUser>
                <Suspense fallback={<LoadingSpinner />}>
                  <UserLayout />
                </Suspense>
              </RequireUser>
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/user/dashboard" replace />} />
          <Route 
            path="dashboard" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <ClientDashboard />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="reporter-setup" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <ReporterConfig />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route
            path="analysis"
            element={
              <RequireTier minTier="SILVER">
                <Suspense fallback={<LoadingSpinner />}>
                  <ErrorBoundary>
                    <ReportAnalysis />
                  </ErrorBoundary>
                </Suspense>
              </RequireTier>
            }
          />
          <Route 
            path="winner-products" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <WinnerProducts />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="subscriptions" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <Subscriptions />
                </ErrorBoundary>
              </Suspense>
            } 
          />
          <Route 
            path="settings" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <Settings type="user" />
                </ErrorBoundary>
              </Suspense>
            } 
          />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;




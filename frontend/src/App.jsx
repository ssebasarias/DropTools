import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import ErrorBoundary from './components/common/ErrorBoundary';

// Lazy load heavy pages for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const GoldMine = lazy(() => import('./pages/GoldMine'));
const ClusterLab = lazy(() => import('./pages/ClusterLab'));
const SystemStatus = lazy(() => import('./pages/SystemStatus'));
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'));

// Auth Pages - Keep synchronous for faster initial load
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import VerifyEmail from './pages/auth/VerifyEmail';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';

// User Pages - Lazy load
const UserLayout = lazy(() => import('./components/layout/UserLayout'));
const AnalyticsDashboard = lazy(() => import('./pages/user/AnalyticsDashboard'));
const WinnerProducts = lazy(() => import('./pages/user/WinnerProducts'));
const ReporterConfig = lazy(() => import('./pages/user/ReporterConfig'));
const Settings = lazy(() => import('./pages/Settings'));

const Subscriptions = lazy(() => import('./pages/Subscriptions'));
const LandingPage = lazy(() => import('./pages/LandingPage'));
const NotFound = lazy(() => import('./pages/NotFound'));

import RequireAuth from './components/auth/RequireAuth';
import RequireAdmin from './components/auth/RequireAdmin';
import RequireUser from './components/auth/RequireUser';
import RequireTier from './components/auth/RequireTier';
import { getAuthUser } from './services/authService';
import { getUserHomePath } from './utils/subscription';

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

const UserHomeRedirect = () => {
  const user = getAuthUser();
  return <Navigate to={getUserHomePath(user)} replace />;
};

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
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

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
            path="users" 
            element={
              <Suspense fallback={<LoadingSpinner />}>
                <ErrorBoundary>
                  <AdminUsersPage />
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
          <Route index element={<UserHomeRedirect />} />
          <Route path="dashboard" element={<UserHomeRedirect />} />
          <Route 
            path="analytics" 
            element={
              <RequireTier minTier="SILVER" fallbackPath="/user/reporter-setup">
                <Suspense fallback={<LoadingSpinner />}>
                  <ErrorBoundary>
                    <AnalyticsDashboard />
                  </ErrorBoundary>
                </Suspense>
              </RequireTier>
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
            path="winner-products" 
            element={
              <RequireTier minTier="GOLD" fallbackPath="/user/analytics">
                <Suspense fallback={<LoadingSpinner />}>
                  <ErrorBoundary>
                    <WinnerProducts />
                  </ErrorBoundary>
                </Suspense>
              </RequireTier>
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

        <Route
          path="*"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <NotFound />
            </Suspense>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}

export default App;




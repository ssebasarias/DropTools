/**
 * Constantes Centralizadas - DropTools Frontend
 * Lugar único para configuraciones, URLs, y valores constantes
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Polling Intervals (milliseconds)
export const POLLING_INTERVALS = {
    SYSTEM_STATUS: 5000,      // 5 segundos
    DASHBOARD: 30000,         // 30 segundos
    CLUSTER_LAB: 10000,       // 10 segundos
    GOLD_MINE: 15000,         // 15 segundos
};

// Pagination
export const PAGINATION = {
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100,
    GOLD_MINE_PAGE_SIZE: 20,
    CLUSTER_LAB_PAGE_SIZE: 15,
};

// Routes
export const ROUTES = {
    HOME: '/',
    DASHBOARD: '/admin',
    GOLD_MINE: '/admin/gold-mine',
    CLUSTER_LAB: '/admin/cluster-lab',
    SYSTEM_STATUS: '/admin/system-status',
};

// API Endpoints
export const API_ENDPOINTS = {
    // Dashboard
    DASHBOARD_STATS: '/dashboard/stats/',

    // Gold Mine
    GOLD_MINE: '/gold-mine/',
    GOLD_MINE_STATS: '/gold-mine/stats/',
    CATEGORIES: '/categories/',

    // Cluster Lab
    CLUSTER_LAB_STATS: '/cluster-lab/stats/',
    CLUSTER_AUDIT: '/cluster-lab/audit-logs/',
    CLUSTER_ORPHANS: '/cluster-lab/orphans/',
    CLUSTER_FEEDBACK: '/cluster-lab/feedback/',

    // System
    SYSTEM_LOGS: '/system-logs/',
    CONTAINER_STATS: '/control/stats/',
    CONTAINER_CONTROL: '/control/container/',
};

// Competition Tiers
export const COMPETITION_TIERS = {
    LOW: { max: 2, label: 'Baja', color: '#10b981' },
    MEDIUM: { min: 3, max: 5, label: 'Media', color: '#f59e0b' },
    HIGH: { min: 6, label: 'Alta', color: '#ef4444' },
};

// Cluster Actions
export const CLUSTER_ACTIONS = {
    MERGE: 'MERGE_SELECTED',
    CONFIRM_SINGLETON: 'CONFIRM_SINGLETON',
    TRASH: 'TRASH',
};

// Docker Services
export const DOCKER_SERVICES = {
    SCRAPER: 'scraper',
    LOADER: 'loader',
    VECTORIZER: 'vectorizer',
    CLASSIFIER: 'classifier',
    CLASSIFIER_2: 'classifier_2',
    CLUSTERIZER: 'clusterizer',
    SHOPIFY_AUDITOR: 'shopify_auditor',
    MARKET_TRENDER: 'market_trender',
    META_SCHOLAR: 'meta_scholar',
    CELERY_WORKER: 'celery_worker',
};

// Container Actions
export const CONTAINER_ACTIONS = {
    START: 'start',
    STOP: 'stop',
    RESTART: 'restart',
};

// UI Constants
export const UI = {
    TOAST_DURATION: 3000,
    ANIMATION_DURATION: 300,
    DEBOUNCE_DELAY: 500,
};

// Price Ranges (COP - Colombian Pesos)
export const PRICE_RANGES = {
    MIN: 0,
    MAX: 1000000,
    DEFAULT_MIN: 0,
    DEFAULT_MAX: 500000,
};

// Chart Colors
export const CHART_COLORS = {
    PRIMARY: '#3b82f6',
    SUCCESS: '#10b981',
    WARNING: '#f59e0b',
    DANGER: '#ef4444',
    INFO: '#06b6d4',
    PURPLE: '#8b5cf6',
};

export default {
    API_BASE_URL,
    POLLING_INTERVALS,
    PAGINATION,
    ROUTES,
    API_ENDPOINTS,
    COMPETITION_TIERS,
    CLUSTER_ACTIONS,
    DOCKER_SERVICES,
    CONTAINER_ACTIONS,
    UI,
    PRICE_RANGES,
    CHART_COLORS,
};

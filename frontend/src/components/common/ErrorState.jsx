import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import GlassCard from './GlassCard';

/**
 * ErrorState - Displays error message with retry option
 * 
 * @param {Object} props
 * @param {Error|string} props.error - Error object or error message
 * @param {function} props.onRetry - Callback function to retry the operation
 * @param {string} props.title - Custom error title (default: "Something went wrong")
 */
export default function ErrorState({ error, onRetry, title = 'Something went wrong' }) {
  const errorMessage = error?.message || error || 'An unexpected error occurred';

  return (
    <GlassCard style={{ textAlign: 'center', padding: '2rem' }}>
      <AlertTriangle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
      <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>{title}</h3>
      <p style={{ color: '#94a3b8', marginBottom: '1.5rem' }}>
        {errorMessage}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            margin: '0 auto',
            padding: '0.75rem 1.5rem',
            background: 'rgba(99, 102, 241, 0.8)',
            border: '1px solid rgba(99, 102, 241, 0.5)',
            borderRadius: '8px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'all 0.2s'
          }}
          onMouseOver={(e) => {
            e.target.style.background = 'rgba(99, 102, 241, 1)';
          }}
          onMouseOut={(e) => {
            e.target.style.background = 'rgba(99, 102, 241, 0.8)';
          }}
        >
          <RefreshCw size={18} />
          Try Again
        </button>
      )}
    </GlassCard>
  );
}

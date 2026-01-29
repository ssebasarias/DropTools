import React from 'react';
import { Inbox } from 'lucide-react';
import GlassCard from './GlassCard';

/**
 * EmptyState - Displays empty state message with optional action
 * 
 * @param {Object} props
 * @param {React.Component} props.icon - Icon component (default: Inbox)
 * @param {string} props.title - Empty state title
 * @param {string} props.description - Empty state description
 * @param {Object} props.action - Optional action button { label, onClick }
 */
export default function EmptyState({ 
  icon: Icon = Inbox, 
  title, 
  description, 
  action 
}) {
  return (
    <GlassCard style={{ textAlign: 'center', padding: '3rem' }}>
      <Icon size={64} color="#64748b" style={{ marginBottom: '1rem' }} />
      {title && (
        <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>{title}</h3>
      )}
      {description && (
        <p style={{ color: '#94a3b8', marginBottom: '1.5rem' }}>{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          style={{
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
          {action.label}
        </button>
      )}
    </GlassCard>
  );
}

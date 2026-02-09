import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import GlassCard from './GlassCard';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console and potentially to error tracking service
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // TODO: Log to error tracking service (e.g., Sentry, LogRocket)
    // logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null,
      errorInfo: null 
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      return (
        <ErrorFallback 
          error={this.state.error} 
          errorInfo={this.state.errorInfo}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

function ErrorFallback({ error, errorInfo, onReset }) {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <GlassCard style={{ maxWidth: '600px', width: '100%' }}>
        <div style={{ textAlign: 'center' }}>
          <AlertTriangle 
            size={64} 
            color="#ef4444" 
            style={{ marginBottom: '1rem' }}
          />
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 'bold', 
            color: '#fff',
            marginBottom: '0.5rem'
          }}>
            Algo salió mal
          </h1>
          <p style={{ 
            color: '#94a3b8', 
            marginBottom: '1.5rem',
            lineHeight: '1.6'
          }}>
            Ha ocurrido un error inesperado. Por favor, intenta recargar la página o regresar al inicio.
          </p>

          {import.meta.env.DEV && error && (
            <details style={{
              marginBottom: '1.5rem',
              padding: '1rem',
              background: 'rgba(0,0,0,0.3)',
              borderRadius: '8px',
              textAlign: 'left',
              fontSize: '0.875rem',
              color: '#cbd5e1'
            }}>
              <summary style={{ 
                cursor: 'pointer', 
                marginBottom: '0.5rem',
                fontWeight: '600'
              }}>
                Detalles del error (solo en desarrollo)
              </summary>
              <pre style={{ 
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {error.toString()}
                {errorInfo && errorInfo.componentStack}
              </pre>
            </details>
          )}

          <div style={{ 
            display: 'flex', 
            gap: '1rem', 
            justifyContent: 'center',
            flexWrap: 'wrap'
          }}>
            <button
              onClick={onReset}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
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
              Reintentar
            </button>
            <button
              onClick={() => navigate('/')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.2)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.1)';
              }}
            >
              <Home size={18} />
              Ir al Inicio
            </button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

export default ErrorBoundary;

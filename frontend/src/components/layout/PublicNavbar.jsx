import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Zap } from 'lucide-react';

const PublicNavbar = () => {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <nav style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            padding: '1rem 2rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            zIndex: 1000,
            background: scrolled ? 'rgba(0,0,0,0.6)' : 'transparent',
            backdropFilter: scrolled ? 'blur(10px)' : 'none',
            borderBottom: scrolled ? '1px solid var(--glass-border)' : 'none',
            transition: 'all 0.3s ease'
        }}>
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                    width: '36px', height: '36px',
                    background: 'var(--primary)',
                    borderRadius: '8px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)'
                }}>
                    <Zap size={20} color="white" fill="white" />
                </div>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold', letterSpacing: '-0.02em', color: 'white' }}>DropTools</span>
            </Link>

            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <Link to="/login" style={{ color: 'var(--text-main)', textDecoration: 'none', fontWeight: '500' }}>Iniciar sesi&oacute;n</Link>
                <Link to="/register" className="btn-primary" style={{ padding: '0.6rem 1.5rem', borderRadius: '50px', textDecoration: 'none' }}>
                    Crear cuenta
                </Link>
            </div>
        </nav>
    );
}

export default PublicNavbar;

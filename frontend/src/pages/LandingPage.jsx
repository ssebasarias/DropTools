import React, { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Zap, ArrowRight, TrendingUp, Shield, BarChart2 } from 'lucide-react';
import Subscriptions from './Subscriptions';

import PublicNavbar from '../components/layout/PublicNavbar';

const HeroSection = () => (
    <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        padding: '6rem 2rem 2rem',
        position: 'relative',
        overflow: 'hidden'
    }}>
        {/* Animated Background Elements */}
        <div className="glow-orb" style={{ top: '20%', left: '20%', background: 'rgba(99, 102, 241, 0.3)' }} />
        <div className="glow-orb" style={{ bottom: '20%', right: '20%', background: 'rgba(236, 72, 153, 0.2)' }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: '900px' }}>
            <div className="fade-in-up" style={{ animationDelay: '0.1s' }}>
                <span style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '50px',
                    background: 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    fontSize: '0.9rem',
                    color: '#c7d2fe',
                    marginBottom: '1.5rem',
                    display: 'inline-block'
                }}>
                    🚀 The Ultimate Tool for Dropshippers
                </span>
            </div>

            <h1 className="hero-text fade-in-up" style={{
                fontSize: 'clamp(3rem, 6vw, 5rem)',
                fontWeight: '900',
                lineHeight: '1.1',
                marginBottom: '1.5rem',
                letterSpacing: '-0.03em',
                background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                animationDelay: '0.2s'
            }}>
                Dominate the Market with <span style={{ color: 'var(--primary)', WebkitTextFillColor: 'var(--primary)' }}>Dahell Intelligence</span>
            </h1>

            <p className="fade-in-up" style={{
                fontSize: '1.25rem',
                color: 'var(--text-muted)',
                marginBottom: '3rem',
                maxWidth: '700px',
                margin: '0 auto 3rem',
                lineHeight: '1.6',
                animationDelay: '0.3s'
            }}>
                Unleash the power of automated reporting, AI-driven analytics, and exclusive winner product alerts. Stop guessing, start scaling.
            </p>

            <div className="fade-in-up" style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', animationDelay: '0.4s' }}>
                <Link to="/register" className="btn-primary" style={{
                    padding: '1rem 2.5rem',
                    fontSize: '1.1rem',
                    borderRadius: '12px',
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    boxShadow: '0 0 30px rgba(99, 102, 241, 0.4)',
                    textDecoration: 'none'
                }}>
                    Start Free Trial <ArrowRight size={20} />
                </Link>
                <button style={{
                    padding: '1rem 2.5rem',
                    fontSize: '1.1rem',
                    borderRadius: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: 'white',
                    cursor: 'pointer',
                    backdropFilter: 'blur(10px)'
                }}>
                    View Demo
                </button>
            </div>
        </div>

        {/* Floating Cards Animation */}
        <div style={{
            marginTop: '5rem',
            perspective: '1000px',
            transform: 'rotateX(20deg) scale(0.9)',
            opacity: 0.8
        }}>
            <div className="glass-card" style={{
                width: '800px',
                height: '400px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
            }}>
                <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--glass-border)', display: 'flex', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#EF4444' }} />
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#F59E0B' }} />
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10B981' }} />
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Dahell Dashboard</div>
                </div>
                <div style={{ padding: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
                    <div style={{ height: '120px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }} />
                    <div style={{ height: '120px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }} />
                    <div style={{ height: '120px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }} />
                    <div style={{ gridColumn: '1 / -1', height: '80px', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '8px', border: '1px dashed rgba(99, 102, 241, 0.3)' }} />
                </div>
            </div>
        </div>
    </div>
);

const FeatureCard = ({ icon: Icon, title, description, color }) => (
    <div className="glass-card feature-card" style={{
        padding: '2rem',
        height: '100%',
        transition: 'all 0.3s ease',
        border: '1px solid var(--glass-border)',
    }}>
        <div style={{
            width: '60px', height: '60px',
            borderRadius: '16px',
            background: `rgba(${color}, 0.15)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '1.5rem',
            color: `rgb(${color})`
        }}>
            <Icon size={32} />
        </div>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', fontWeight: 'bold' }}>{title}</h3>
        <p className="text-muted" style={{ lineHeight: '1.6' }}>{description}</p>
    </div>
);

const LandingPage = () => {
    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-dark)', color: 'var(--text-main)', overflowX: 'hidden' }}>
            <PublicNavbar />

            <HeroSection />

            <div style={{ padding: '4rem 2rem', position: 'relative' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
                        <h2 style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>Why Choose Dahell?</h2>
                        <p className="text-muted" style={{ maxWidth: '600px', margin: '0 auto' }}>Everything you need to automate, analyze, and scale your e-commerce empire.</p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
                        <FeatureCard
                            icon={Zap}
                            title="Instant Automation"
                            description="Connect your secondary worker accounts and let our bots handle the repetitive CAS reporting tasks for you."
                            color="245, 158, 11"
                        />
                        <FeatureCard
                            icon={TrendingUp}
                            title="Winner Products"
                            description="Get exclusive real-time alerts on high-potential swimming products before your competitors do."
                            color="99, 102, 241"
                        />
                        <FeatureCard
                            icon={Shield}
                            title="Secure & Private"
                            description="Enterprise-grade security for your data and credentials. Your operational secrets are safe with us."
                            color="16, 185, 129"
                        />
                    </div>
                </div>
            </div>

            <div style={{ padding: '4rem 2rem 8rem', background: 'linear-gradient(to top, rgba(0,0,0,0.3), transparent)' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    {/* Temporarily using the Subscriptions component's layout style by wrapping it */}
                    {/* In a real app we might refactor to shared components, but reuse works for now */}
                    <Subscriptions />
                </div>
            </div>

            <footer style={{
                padding: '4rem 2rem',
                borderTop: '1px solid var(--glass-border)',
                textAlign: 'center',
                color: 'var(--text-muted)'
            }}>
                <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'center', gap: '1rem', alignItems: 'center' }}>
                    <Zap size={24} color="var(--primary)" fill="var(--primary)" />
                    <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white' }}>Dahell</span>
                </div>
                <p>&copy; 2026 Dahell Intelligence. All rights reserved.</p>
            </footer>

            <style>{`
                .glow-orb {
                    position: absolute;
                    width: 400px;
                    height: 400px;
                    border-radius: 50%;
                    filter: blur(100px);
                    opacity: 0.4;
                    z-index: 0;
                    animation: float 10s infinite ease-in-out;
                }
                @keyframes float {
                    0%, 100% { transform: translate(0, 0); }
                    50% { transform: translate(20px, -20px); }
                }
                .feature-card:hover {
                    transform: translateY(-10px);
                    background: rgba(255,255,255,0.05);
                }
                .fade-in-up {
                    opacity: 0;
                    transform: translateY(20px);
                    animation: fadeInUp 0.8s forwards;
                }
                @keyframes fadeInUp {
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default LandingPage;

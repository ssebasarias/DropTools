import React, { useMemo, useState } from 'react';
import { Check, X, Shield, Medal, Trophy, Crown } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getAuthUser } from '../services/authService';

const PlanCard = ({ plan, billingCycle, onSelect }) => {
    const isPremium = plan.tier === 'PLATINUM';

    return (
        <div className={`glass-card ${isPremium ? 'premium-glow' : ''}`} style={{
            position: 'relative',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            border: isPremium ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid var(--glass-border)',
            background: isPremium ? 'linear-gradient(145deg, rgba(99, 102, 241, 0.1), rgba(0,0,0,0))' : 'var(--glass-bg)',
        }}>
            {isPremium && (
                <div style={{
                    position: 'absolute',
                    top: '-12px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'linear-gradient(90deg, var(--primary), var(--secondary))',
                    padding: '0.25rem 1rem',
                    borderRadius: '20px',
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)'
                }}>
                    Most Popular
                </div>
            )}

            <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
                <div style={{
                    width: '60px',
                    height: '60px',
                    margin: '0 auto 1rem',
                    background: `rgba(${plan.colorRgb}, 0.1)`,
                    borderRadius: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: plan.color
                }}>
                    <plan.icon size={32} />
                </div>
                <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>{plan.name}</h3>
                <p className="text-muted" style={{ fontSize: '0.9rem', minHeight: '40px' }}>{plan.description}</p>
            </div>

            <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: '0.25rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '6px' }}>$</span>
                    <span style={{ fontSize: '3.5rem', fontWeight: '800', lineHeight: '1', color: 'var(--text-main)' }}>
                        {billingCycle === 'monthly' ? plan.priceMonthly : plan.priceYearly}
                    </span>
                    <span className="text-muted" style={{ marginBottom: '6px' }}>/mo</span>
                </div>
                {billingCycle === 'yearly' && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: '0.5rem' }}>
                        Billed ${plan.priceYearly * 12} yearly
                    </p>
                )}
            </div>

            <div style={{ flex: 1, marginBottom: '2rem' }}>
                <ul style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {plan.features.map((feature, idx) => (
                        <li key={idx} style={{ display: 'flex', gap: '0.75rem', fontSize: '0.95rem', alignItems: 'flex-start', opacity: feature.included ? 1 : 0.5 }}>
                            {feature.included ? (
                                <div style={{
                                    minWidth: '20px',
                                    height: '20px',
                                    borderRadius: '50%',
                                    background: `rgba(${plan.colorRgb}, 0.2)`,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: plan.color,
                                    marginTop: '2px'
                                }}>
                                    <Check size={12} strokeWidth={3} />
                                </div>
                            ) : (
                                <div style={{
                                    minWidth: '20px',
                                    height: '20px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    marginTop: '2px'
                                }}>
                                    <X size={16} />
                                </div>
                            )}
                            <span style={{ color: feature.included ? 'var(--text-main)' : 'var(--text-muted)', textDecoration: feature.included ? 'none' : 'line-through' }}>
                                {feature.name}
                            </span>
                        </li>
                    ))}
                </ul>
            </div>

            <button
                className={isPremium ? 'btn-primary' : ''}
                style={{
                    width: '100%',
                    padding: '1rem',
                    borderRadius: '12px',
                    fontWeight: '600',
                    background: isPremium ? undefined : 'rgba(255,255,255,0.05)',
                    border: isPremium ? 'none' : '1px solid var(--glass-border)',
                    color: isPremium ? 'white' : 'var(--text-main)',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                }}
                onClick={() => onSelect(plan)}
            >
                {plan.cta}
            </button>
        </div>
    );
};

const Subscriptions = () => {
    const [billingCycle, setBillingCycle] = useState('monthly'); // 'monthly' | 'yearly'
    const navigate = useNavigate();
    const location = useLocation();
    const user = getAuthUser();

    const plans = useMemo(() => ([
        {
            tier: 'BRONZE',
            name: 'Bronze',
            description: 'Acceso a Reporter y automatización básica.',
            priceMonthly: 29,
            priceYearly: 24,
            icon: Medal,
            color: '#b45309', // amber-700
            colorRgb: '180, 83, 9',
            cta: 'Comprar Bronze (próximamente)',
            features: [
                { name: 'Generación de reportes (Reporter/Orchestrator)', included: true },
                { name: 'Gestión de cuentas worker (DropiAccount)', included: true },
                { name: 'Análisis de reportes', included: false },
                { name: 'Winner products', included: false },
                { name: 'Análisis de mercado + creativos (próximo)', included: false },
            ],
        },
        {
            tier: 'SILVER',
            name: 'Silver',
            description: 'Incluye análisis de reportes (AnalystReporter).',
            priceMonthly: 79,
            priceYearly: 65,
            icon: Shield,
            color: '#94a3b8',
            colorRgb: '148, 163, 184',
            cta: 'Comprar Silver (próximamente)',
            features: [
                { name: 'Generación de reportes (Reporter/Orchestrator)', included: true },
                { name: 'Análisis de reportes', included: true },
                { name: 'Winner products', included: false },
                { name: 'Análisis de mercado + creativos (próximo)', included: false },
            ],
        },
        {
            tier: 'GOLD',
            name: 'Gold',
            description: 'Desbloquea Winner Products.',
            priceMonthly: 149,
            priceYearly: 124,
            icon: Trophy,
            color: '#f59e0b',
            colorRgb: '245, 158, 11',
            cta: 'Comprar Gold (próximamente)',
            features: [
                { name: 'Generación de reportes (Reporter/Orchestrator)', included: true },
                { name: 'Análisis de reportes', included: true },
                { name: 'Winner products', included: true },
                { name: 'Análisis de mercado + creativos (próximo)', included: false },
            ],
        },
        {
            tier: 'PLATINUM',
            name: 'Platinum',
            description: 'Incluye Winner Products + Market Intelligence (próximo).',
            priceMonthly: 249,
            priceYearly: 199,
            icon: Crown,
            color: '#6366f1',
            colorRgb: '99, 102, 241',
            cta: 'Comprar Platinum (próximamente)',
            features: [
                { name: 'Generación de reportes (Reporter/Orchestrator)', included: true },
                { name: 'Análisis de reportes', included: true },
                { name: 'Winner products', included: true },
                { name: 'Análisis de mercado + creativos (próximo)', included: true },
            ],
        },
    ]), []);

    const selectedPlan = useMemo(() => {
        const params = new URLSearchParams(location.search);
        return (params.get('plan') || '').toUpperCase();
    }, [location.search]);

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
                <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem', background: 'linear-gradient(135deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Choose Your Plan
                </h1>
                <p className="text-muted" style={{ fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>
                    Planes por suscripción. El pago aún no está habilitado, pero ya puedes ver qué desbloquea cada tier.
                </p>
                {user && !user.is_admin && (
                    <p className="text-muted" style={{ marginTop: '1rem' }}>
                        Tu estado actual: <strong>{user.subscription_tier || 'BRONZE'}</strong> ·{' '}
                        {user.subscription_active ? (
                            <span style={{ color: 'var(--success)' }}>ACTIVA</span>
                        ) : (
                            <span style={{ color: 'var(--warning)' }}>INACTIVA (trial)</span>
                        )}
                    </p>
                )}
                {selectedPlan && (
                    <div className="glass-panel" style={{ marginTop: '1.5rem', padding: '1rem' }}>
                        <strong>Compra no disponible aún.</strong> Plan seleccionado: <strong>{selectedPlan}</strong>. Aquí luego irá el checkout.
                    </div>
                )}

                {/* Billing Toggle */}
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    background: 'rgba(255,255,255,0.05)',
                    padding: '0.4rem',
                    borderRadius: '99px',
                    marginTop: '2rem',
                    border: '1px solid var(--glass-border)'
                }}>
                    <button
                        onClick={() => setBillingCycle('monthly')}
                        style={{
                            padding: '0.5rem 1.5rem',
                            borderRadius: '99px',
                            border: 'none',
                            background: billingCycle === 'monthly' ? 'var(--glass-bg-hover)' : 'transparent',
                            color: billingCycle === 'monthly' ? 'var(--text-main)' : 'var(--text-muted)',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        Monthly
                    </button>
                    <button
                        onClick={() => setBillingCycle('yearly')}
                        style={{
                            padding: '0.5rem 1.5rem',
                            borderRadius: '99px',
                            border: 'none',
                            background: billingCycle === 'yearly' ? 'var(--glass-bg-hover)' : 'transparent',
                            color: billingCycle === 'yearly' ? 'var(--text-main)' : 'var(--text-muted)',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        Yearly <span style={{ fontSize: '0.7em', background: 'var(--primary)', color: 'white', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>-20%</span>
                    </button>
                </div>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '2rem',
                alignItems: 'start'
            }}>
                {plans.map((plan, index) => (
                    <PlanCard
                        key={index}
                        plan={plan}
                        billingCycle={billingCycle}
                        onSelect={(p) => navigate(`/user/subscriptions?plan=${p.tier}`)}
                    />
                ))}
            </div>

            <div style={{ marginTop: '4rem', textAlign: 'center', padding: '2rem', background: 'rgba(255,255,255,0.02)', borderRadius: '16px' }}>
                <h3 style={{ marginBottom: '1rem' }}>Frequently Asked Questions</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', textAlign: 'left', marginTop: '2rem' }}>
                    <div>
                        <h4 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Can I switch plans later?</h4>
                        <p className="text-muted" style={{ fontSize: '0.9rem' }}>Yes, you can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.</p>
                    </div>
                    <div>
                        <h4 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Do I need a secondary account?</h4>
                        <p className="text-muted" style={{ fontSize: '0.9rem' }}>For the Automated Reporter and Chatbot features, a secondary "worker" account is highly recommended for security.</p>
                    </div>
                    <div>
                        <h4 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Is support included?</h4>
                        <p className="text-muted" style={{ fontSize: '0.9rem' }}>Yes, all plans come with support. Priority support is exclusive to Operator and Elite tiers.</p>
                    </div>
                </div>
            </div>

            <style>{`
                .premium-glow {
                    box-shadow: 0 0 30px rgba(99, 102, 241, 0.15);
                    transition: transform 0.3s;
                }
                .premium-glow:hover {
                    box-shadow: 0 0 50px rgba(99, 102, 241, 0.25);
                    transform: translateY(-5px);
                }
            `}</style>
        </div>
    );
};

export default Subscriptions;

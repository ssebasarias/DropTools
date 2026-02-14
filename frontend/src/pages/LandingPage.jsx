import React, { useEffect, useId, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    Zap, ArrowRight, TrendingUp, BarChart2, CheckCircle, ChevronDown, ChevronUp,
    HelpCircle, Activity, Box, Truck, Instagram, Facebook, Mail, Star, Crown
} from 'lucide-react';
import PublicNavbar from '../components/layout/PublicNavbar';

const legalContent = {
    terms: {
        title: 'Términos de Servicio',
        paragraphs: [
            'DropTools ofrece herramientas de automatización y análisis para operaciones de dropshipping. Al usar la plataforma, aceptas utilizarla de forma responsable y conforme a la normativa aplicable.',
            'El acceso y uso de ciertas funciones puede depender de tu plan activo. El uso indebido, intentos de vulnerar la seguridad o actividades fraudulentas pueden resultar en suspensión de la cuenta.',
            'Estos términos pueden actualizarse para reflejar mejoras del servicio o cambios normativos. Cuando ocurra, publicaremos la versión vigente en esta sección.'
        ]
    },
    privacy: {
        title: 'Política de Privacidad',
        paragraphs: [
            'Procesamos únicamente los datos necesarios para operar la plataforma, mejorar tu experiencia y brindar soporte. No vendemos tus datos a terceros.',
            'Protegemos tu información con medidas técnicas y organizativas, incluyendo cifrado en tránsito y controles de acceso internos.',
            'Puedes solicitar actualización o eliminación de tus datos cuando aplique, escribiendo a nuestro canal de soporte.'
        ]
    },
    refunds: {
        title: 'Política de Reembolsos',
        paragraphs: [
            'Puedes cancelar tu suscripción en cualquier momento desde tu panel. La cancelación detiene renovaciones futuras.',
            'Los reembolsos se revisan caso por caso según tiempo de uso, incidencias técnicas reportadas y condiciones del plan.',
            'Para solicitar revisión de reembolso, contáctanos por soporte con el correo de tu cuenta y el motivo de la solicitud.'
        ]
    }
};

const heroInsights = [
    {
        id: 'reported',
        label: 'Reporte Enviado',
        value: 'Orden #29301',
        icon: CheckCircle,
        tone: 'success',
        position: 'orbit-pos-1',
        delay: 0
    },
    {
        id: 'winner',
        label: 'Producto Ganador',
        value: '+200 Ventas/día',
        icon: TrendingUp,
        tone: 'warning',
        position: 'orbit-pos-2',
        delay: 0.9
    },
    {
        id: 'efficiency',
        label: 'Eficiencia Operativa',
        value: '+45% vs mes anterior',
        icon: Activity,
        tone: 'primary',
        position: 'orbit-pos-3',
        delay: 1.8
    },
    {
        id: 'sales-up',
        label: 'Ventas en Alza',
        value: '+34% mensual',
        icon: BarChart2,
        tone: 'secondary',
        position: 'orbit-pos-4',
        delay: 2.9
    },
    {
        id: 'response',
        label: 'Tiempo de Respuesta',
        value: '-28 min promedio',
        icon: Zap,
        tone: 'success',
        position: 'orbit-pos-5',
        delay: 3.4
    }
];

const HeroSection = () => (
    <div className="hero-section">
        <div className="glow-bg">
            <div className="glow-orb glow-1" />
            <div className="glow-orb glow-2" />
        </div>

        <div className="container relative z-10 text-center">
            <div className="fade-in-up delay-100">
                <span className="pill-badge">
                    🚀 Potencia tu E-commerce
                </span>
            </div>

            <div className="hero-title-wrap">
                <h1 className="hero-title fade-in-up delay-200">
                    Tu Operación de Dropshipping,<br />
                    <span className="text-gradient-primary">En Piloto Automático.</span>
                </h1>
                <div className="hero-orbit" aria-hidden="true">
                    {heroInsights.map((item) => {
                        const Icon = item.icon;
                        return (
                            <div
                                key={item.id}
                                className={`floating-card orbit-card ${item.position}`}
                                style={{ animationDelay: `${item.delay}s` }}
                            >
                                <div className={`icon-box ${item.tone}`}><Icon size={18} /></div>
                                <div>
                                    <div className="card-label">{item.label}</div>
                                    <div className="card-value">{item.value}</div>
                                </div>
                            </div>
                        );
                    })}
                    <div className="orbit-ring ring-1" />
                    <div className="orbit-ring ring-2" />
                </div>
            </div>

            <p className="hero-subtitle fade-in-up delay-300">
                Deja de perder tiempo en tareas repetitivas. Automatiza tus reportes,
                descubre productos ganadores y toma el control total de tus ventas con DropTools.
            </p>

            <div className="hero-cta fade-in-up delay-400">
                <a href="#beneficios" className="btn-primary-lg icon-hover-move">
                    Ver c&oacute;mo funciona <ArrowRight size={20} />
                </a>
                <div className="hero-stat">
                    <span className="stat-dot" /> +10,000 &Oacute;rdenes Analizadas
                </div>
            </div>
            <a href="#beneficios" className="scroll-hint fade-in-up delay-500">
                Sigue bajando para conocer c&oacute;mo funciona
                <ChevronDown size={16} />
            </a>
        </div>
    </div>
);

const PainPointSection = () => (
    <div className="section-padding bg-darker">
        <div className="container text-center">
            <h2 className="section-title">&iquest;Cansado de operar a ciegas?</h2>
            <p className="section-subtitle">
                Sabemos lo frustrante que es ver &oacute;rdenes estancadas y no saber por qu&eacute;.
                La falta de informaci&oacute;n mata tu rentabilidad.
            </p>
            <div className="grid-3">
                <div className="pain-card">
                    <div className="pain-icon"><Truck size={32} /></div>
                    <h3>&Oacute;rdenes Estancadas</h3>
                    <p>Paquetes que no se mueven y clientes reclamando.</p>
                </div>
                <div className="pain-card">
                    <div className="pain-icon"><HelpCircle size={32} /></div>
                    <h3>Falta de Datos</h3>
                    <p>Decisiones basadas en intuici&oacute;n en lugar de m&eacute;tricas reales.</p>
                </div>
                <div className="pain-card">
                    <div className="pain-icon"><Box size={32} /></div>
                    <h3>Productos Saturados</h3>
                    <p>Vender lo mismo que todos y competir solo por precio.</p>
                </div>
            </div>
        </div>
    </div>
);

const OrdersFlowVisual = () => (
    <div className="feature-mockup orders-mockup">
        <div className="mockup-header">
            <div className="dots"><span /><span /><span /></div>
            <span className="mockup-label">Estado de &oacute;rdenes</span>
        </div>
        <div className="mockup-body orders-body">
            <div className="orders-scene">
                <div className="scene-rail" />
                <div className="scene-stop stop-1">
                    <span className="stop-dot" />
                    <span>Novedad reportada</span>
                </div>
                <div className="scene-stop stop-2">
                    <span className="stop-dot" />
                    <span>Bodega confirma</span>
                </div>
                <div className="scene-stop stop-3">
                    <span className="stop-dot" />
                    <span>En ruta</span>
                </div>
                <div className="scene-stop stop-4 success">
                    <span className="stop-dot" />
                    <span>Entregada</span>
                </div>
                <div className="truck-node" aria-hidden="true">
                    <Truck size={17} />
                </div>
            </div>
            <div className="orders-events">
                <div className="event-pill">Orden #29301 actualizada</div>
                <div className="event-pill">Tiempo de respuesta: 12 min</div>
            </div>
        </div>
    </div>
);

const SalesGrowthVisual = () => (
    <div className="feature-mockup sales-mockup">
        <div className="mockup-header">
            <div className="dots"><span /><span /><span /></div>
            <span className="mockup-label">Evoluci&oacute;n de ventas</span>
        </div>
        <div className="mockup-body sales-body">
            <div className="sales-line-wrap">
                <svg viewBox="0 0 320 170" className="sales-line-chart" aria-hidden="true">
                    <defs>
                        <linearGradient id="sales-gradient" x1="0%" y1="100%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#ec4899" />
                            <stop offset="100%" stopColor="#22d3ee" />
                        </linearGradient>
                    </defs>
                    <line x1="24" y1="140" x2="296" y2="140" className="grid-line" />
                    <line x1="24" y1="104" x2="296" y2="104" className="grid-line faded" />
                    <line x1="24" y1="68" x2="296" y2="68" className="grid-line faded" />
                    <line x1="24" y1="32" x2="296" y2="32" className="grid-line faded" />
                    <path
                        d="M28 132 C70 126, 92 118, 126 106 C164 92, 182 76, 214 66 C236 58, 264 46, 292 34"
                        className="sales-line-track"
                    />
                    <path
                        d="M28 132 C70 126, 92 118, 126 106 C164 92, 182 76, 214 66 C236 58, 264 46, 292 34"
                        className="sales-line-path"
                    />
                    <circle cx="292" cy="34" r="5" className="sales-line-endpoint" />
                </svg>
                <div className="sales-arrow" aria-hidden="true">
                    <ArrowRight size={16} />
                </div>
            </div>
            <div className="sales-metric">
                <TrendingUp size={16} /> +34% crecimiento mensual
            </div>
        </div>
    </div>
);

const BestsellerVisual = () => (
    <div className="feature-mockup bestseller-mockup">
        <div className="mockup-header">
            <div className="dots"><span /><span /><span /></div>
            <span className="mockup-label">Top productos</span>
        </div>
        <div className="mockup-body bestseller-body">
            <div className="podium-scene">
                <div className="podium podium-second">
                    <div className="podium-product">Mini impresora</div>
                    <div className="podium-rank">#2</div>
                </div>
                <div className="podium podium-first">
                    <div className="winner-crown"><Crown size={16} /></div>
                    <div className="podium-product">Faja moldeadora</div>
                    <div className="podium-rank">#1</div>
                </div>
                <div className="podium podium-third">
                    <div className="podium-product">Cepillo vapor</div>
                    <div className="podium-rank">#3</div>
                </div>
            </div>
            <div className="podium-footer">
                <span className="trend-tag"><Star size={14} /> Alta demanda sostenida</span>
            </div>
        </div>
    </div>
);

const FeatureVisual = ({ variant }) => {
    if (variant === 'orders') return <OrdersFlowVisual />;
    if (variant === 'sales') return <SalesGrowthVisual />;
    return <BestsellerVisual />;
};

const FeatureSection = ({
    icon: Icon,
    title,
    description,
    badge,
    imagePlace,
    color = 'primary',
    variant = 'orders'
}) => (
    <div className="section-padding relative overflow-hidden">
        <div className={`glow-spot spot-${color}`} />
        <div className="container grid-split items-center">
            <div className={`feature-content ${imagePlace === 'left' ? 'order-2' : ''}`}>
                <div className={`feature-icon-lg bg-${color}-soft`}>
                    <Icon size={32} className={`text-${color}`} />
                </div>
                <h2 className="feature-title">{title}</h2>
                <p className="feature-desc">{description}</p>
                <div className="feature-badges">
                    {badge && <span className="badge-outline">{badge}</span>}
                </div>
            </div>
            <div className={`feature-visual ${imagePlace === 'left' ? 'order-1' : ''}`}>
                <div className="glass-panel feature-panel">
                    <FeatureVisual variant={variant} />
                </div>
            </div>
        </div>
    </div>
);

const FAQItem = ({ question, answer }) => {
    const [isOpen, setIsOpen] = useState(false);
    const answerId = useId();

    return (
        <div className="faq-item">
            <button
                type="button"
                className="faq-question"
                aria-expanded={isOpen}
                aria-controls={answerId}
                onClick={() => setIsOpen((prev) => !prev)}
            >
                <span>{question}</span>
                {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
            <div id={answerId} className={`faq-answer ${isOpen ? 'open' : ''}`}>
                <p>{answer}</p>
            </div>
        </div>
    );
};

const FAQSection = () => (
    <div className="section-padding" id="faq">
        <div className="container max-w-800">
            <div className="text-center mb-16">
                <h2 className="section-title">Preguntas Frecuentes</h2>
                <p className="text-muted">Respuestas claras para empezar con seguridad.</p>
            </div>
            <div className="faq-grid">
                <FAQItem
                    question="&iquest;Necesito conocimientos de programaci&oacute;n?"
                    answer="No. DropTools est&aacute; pensado para equipos de operaci&oacute;n y ventas. Conectas tu cuenta, eliges configuraciones y el sistema trabaja por ti."
                />
                <FAQItem
                    question="&iquest;Es seguro conectar mi cuenta de Dropi?"
                    answer="S&iacute;. Aplicamos controles de seguridad y cifrado para proteger accesos y datos operativos. No compartimos credenciales con terceros."
                />
                <FAQItem
                    question="&iquest;Qu&eacute; mejora exactamente el m&oacute;dulo de reportador?"
                    answer="Detecta &oacute;rdenes sin movimiento, automatiza gesti&oacute;n de novedades y te ayuda a reducir tiempos de respuesta frente a reclamos."
                />
                <FAQItem
                    question="&iquest;C&oacute;mo identifica productos ganadores?"
                    answer="Cruza tendencia de ventas, saturaci&oacute;n y potencial de demanda para destacar productos con mejor oportunidad comercial."
                />
                <FAQItem
                    question="&iquest;Puedo cancelar en cualquier momento?"
                    answer="S&iacute;. No manejamos permanencia obligatoria. Puedes cancelar tu suscripci&oacute;n desde el panel cuando lo necesites."
                />
                <FAQItem
                    question="&iquest;Hay soporte si me quedo atascado?"
                    answer="Claro. Nuestro equipo te acompa&ntilde;a en la configuraci&oacute;n inicial y en dudas operativas para que obtengas resultados r&aacute;pido."
                />
            </div>
        </div>
    </div>
);

const CTASection = () => (
    <div className="cta-section" id="cta">
        <div className="container text-center relative z-10">
            <h2 className="cta-title">&iquest;Listo para escalar tu negocio?</h2>
            <p className="cta-subtitle">&Uacute;nete a los dropshippers que ya est&aacute;n automatizando su &eacute;xito.</p>
            <div className="cta-buttons">
                <Link to="/register" className="btn-primary-lg">Crear cuenta</Link>
                <a href="mailto:soporte@droptools.app" className="btn-secondary-lg">Contactar soporte</a>
            </div>
        </div>
        <div className="cta-bg-glow" />
    </div>
);

const Footer = ({ onOpenLegal }) => (
    <footer className="footer section-padding-sm border-t glass-border">
        <div className="container grid-4">
            <div className="footer-col">
                <div className="brand-logo mb-4">
                    <Zap size={24} className="text-primary" />
                    <span className="font-bold text-xl text-white">DropTools</span>
                </div>
                <p className="text-muted text-sm">
                    La plataforma definitiva para automatizaci&oacute;n y an&aacute;lisis de dropshipping en LATAM.
                </p>
            </div>
            <div className="footer-col">
                <h4>Producto</h4>
                <ul className="footer-links">
                    <li><a href="#beneficios">Caracter&iacute;sticas</a></li>
                    <li><a href="#cta">Planes</a></li>
                    <li><a href="#faq">Preguntas frecuentes</a></li>
                </ul>
            </div>
            <div className="footer-col">
                <h4>Legal</h4>
                <ul className="footer-links">
                    <li><button type="button" onClick={() => onOpenLegal('terms')}>T&eacute;rminos de Servicio</button></li>
                    <li><button type="button" onClick={() => onOpenLegal('privacy')}>Pol&iacute;tica de Privacidad</button></li>
                    <li><button type="button" onClick={() => onOpenLegal('refunds')}>Reembolsos</button></li>
                </ul>
            </div>
            <div className="footer-col">
                <h4>Contacto</h4>
                <ul className="social-links">
                    <li><a href="mailto:soporte@droptools.app" aria-label="Correo de soporte"><Mail size={20} /></a></li>
                    <li><a href="#" aria-label="Instagram"><Instagram size={20} /></a></li>
                    <li><a href="#" aria-label="Facebook"><Facebook size={20} /></a></li>
                </ul>
            </div>
        </div>
        <div className="container text-center mt-12 pt-8 border-t glass-border-light">
            <p className="footer-love">Hecho con amor para quienes construyen con amor.</p>
            <p className="text-muted text-sm">&copy; 2026 DropTools. Todos los derechos reservados.</p>
        </div>
    </footer>
);

const LegalModal = ({ section, isOpen, onClose }) => {
    if (!isOpen) return null;
    const content = legalContent[section];

    return (
        <div className="legal-modal-backdrop" onClick={onClose}>
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="legal-modal-title"
                className="legal-modal"
                onClick={(event) => event.stopPropagation()}
            >
                <div className="legal-modal-header">
                    <h3 id="legal-modal-title">{content.title}</h3>
                    <button type="button" className="legal-close" onClick={onClose} aria-label="Cerrar modal legal">
                        ×
                    </button>
                </div>
                <div className="legal-modal-body">
                    {content.paragraphs.map((paragraph) => (
                        <p key={paragraph}>{paragraph}</p>
                    ))}
                </div>
            </div>
        </div>
    );
};

const LandingPage = () => {
    const [legalSection, setLegalSection] = useState('terms');
    const [isLegalOpen, setIsLegalOpen] = useState(false);

    useEffect(() => {
        if (!isLegalOpen) return undefined;
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') setIsLegalOpen(false);
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isLegalOpen]);

    const openLegalModal = (section) => {
        setLegalSection(section);
        setIsLegalOpen(true);
    };

    return (
        <div className="landing-page">
            <PublicNavbar />

            <HeroSection />
            <PainPointSection />

            <div id="beneficios">
                <FeatureSection
                    icon={Truck}
                    title="Mant&eacute;n tus &oacute;rdenes en movimiento"
                    description="Nuestro Reportador Autom&aacute;tico detecta y gestiona &oacute;rdenes estancadas para que tu operaci&oacute;n avance todos los d&iacute;as."
                    badge="Flujo operativo"
                    imagePlace="right"
                    color="primary"
                    variant="orders"
                />

                <FeatureSection
                    icon={BarChart2}
                    title="Lleva tus ventas a otro nivel"
                    description="Visualiza resultados en tiempo real y toma decisiones con datos claros para crecer de forma predecible."
                    badge="Anal&iacute;tica accionable"
                    imagePlace="left"
                    color="secondary"
                    variant="sales"
                />

                <FeatureSection
                    icon={TrendingUp}
                    title="Descubre tu pr&oacute;ximo bestseller"
                    description="Detecta oportunidades con mayor potencial y enfoca tu energ&iacute;a en productos que realmente pueden escalar."
                    badge="Alerta top ventas"
                    imagePlace="right"
                    color="warning"
                    variant="bestseller"
                />
            </div>

            <FAQSection />
            <CTASection />
            <Footer onOpenLegal={openLegalModal} />
            <LegalModal section={legalSection} isOpen={isLegalOpen} onClose={() => setIsLegalOpen(false)} />

            <style>{`
                .landing-page {
                    min-height: 100vh;
                    background: var(--bg-app);
                    color: var(--text-main);
                    overflow-x: hidden;
                    font-family: 'Inter', sans-serif;
                    position: relative;
                    background-image:
                        radial-gradient(circle at 8% 10%, rgba(99, 102, 241, 0.22) 0%, transparent 34%),
                        radial-gradient(circle at 90% 14%, rgba(236, 72, 153, 0.18) 0%, transparent 30%),
                        radial-gradient(circle at 14% 78%, rgba(56, 189, 248, 0.12) 0%, transparent 34%),
                        radial-gradient(circle at 88% 84%, rgba(129, 140, 248, 0.16) 0%, transparent 40%);
                }
                .landing-page::before,
                .landing-page::after {
                    content: "";
                    position: fixed;
                    width: 38vw;
                    height: 38vw;
                    border-radius: 50%;
                    filter: blur(120px);
                    pointer-events: none;
                    z-index: 0;
                }
                .landing-page::before {
                    top: 28%;
                    left: -12%;
                    background: rgba(99, 102, 241, 0.1);
                }
                .landing-page::after {
                    top: 58%;
                    right: -14%;
                    background: rgba(236, 72, 153, 0.08);
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1.5rem;
                }
                .max-w-800 { max-width: 800px; }
                .section-padding {
                    padding: 6rem 0;
                    position: relative;
                    z-index: 1;
                }
                .section-padding-sm { padding: 4rem 0; }
                .grid-split {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 4rem;
                    align-items: center;
                }
                .grid-3 {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 2rem;
                    margin-top: 3rem;
                }
                .grid-4 {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 2rem;
                }
                .text-center { text-align: center; }
                .relative { position: relative; }
                .z-10 { z-index: 10; }
                .order-1 { order: 1; }
                .order-2 { order: 2; }
                .mb-16 { margin-bottom: 4rem; }

                .hero-section {
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    padding-top: 7rem;
                    padding-bottom: 2.5rem;
                    position: relative;
                }
                .pill-badge {
                    padding: 0.5rem 1.25rem;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 50px;
                    font-size: 0.875rem;
                    color: #c7d2fe;
                    margin-bottom: 1.5rem;
                    display: inline-block;
                    backdrop-filter: blur(5px);
                }
                .hero-title-wrap {
                    position: relative;
                    display: inline-flex;
                    justify-content: center;
                    align-items: center;
                    margin-bottom: 0.35rem;
                    padding: 7.8rem 14rem 6.8rem;
                }
                .hero-title {
                    font-size: clamp(2.5rem, 5vw, 4.5rem);
                    font-weight: 800;
                    line-height: 1.1;
                    margin: 0;
                    letter-spacing: -0.02em;
                    position: relative;
                    z-index: 3;
                }
                .hero-orbit {
                    position: absolute;
                    inset: 0;
                    z-index: 2;
                }
                .orbit-ring {
                    position: absolute;
                    border-radius: 999px;
                    border: 1px dashed rgba(99, 102, 241, 0.22);
                    pointer-events: none;
                    animation: spin 90s linear infinite;
                }
                .ring-1 {
                    inset: 18% 8% 16%;
                }
                .ring-2 {
                    inset: 9% 2% 8%;
                    border-color: rgba(236, 72, 153, 0.2);
                    animation-direction: reverse;
                    animation-duration: 120s;
                }
                .text-gradient-primary {
                    background: linear-gradient(135deg, var(--primary), #a5b4fc);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .hero-subtitle {
                    font-size: 1.2rem;
                    color: var(--text-muted);
                    max-width: 700px;
                    margin: 0 auto 2.5rem;
                    line-height: 1.6;
                }
                .hero-cta {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 1rem;
                    margin-bottom: 1.2rem;
                }
                .hero-stat {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.875rem;
                    color: var(--text-muted);
                }
                .stat-dot {
                    width: 8px;
                    height: 8px;
                    background: var(--success);
                    border-radius: 50%;
                    box-shadow: 0 0 10px var(--success);
                }

                .btn-primary-lg {
                    background: var(--primary);
                    color: white;
                    padding: 1rem 2.5rem;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 1.05rem;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.75rem;
                    box-shadow: 0 10px 30px -10px var(--primary-rgb);
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                }
                .btn-primary-lg:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 20px 40px -12px var(--primary-rgb);
                }
                .btn-secondary-lg {
                    background: rgba(255, 255, 255, 0.05);
                    color: white;
                    padding: 1rem 2.5rem;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 1.05rem;
                    text-decoration: none;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                }
                .btn-secondary-lg:hover { background: rgba(255, 255, 255, 0.1); }
                .icon-hover-move svg { transition: transform 0.3s ease; }
                .icon-hover-move:hover svg { transform: translateX(5px); }

                .scroll-hint {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.4rem;
                    color: #cbd5e1;
                    text-decoration: none;
                    font-size: 0.9rem;
                    opacity: 0.9;
                }
                .scroll-hint svg {
                    animation: bounceDown 1.8s ease-in-out infinite;
                }
                .floating-card {
                    position: absolute;
                    background: rgba(15, 23, 42, 0.78);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    padding: 0.74rem 0.82rem;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    gap: 0.72rem;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    animation: orbitDrift 9s ease-in-out infinite, pulseGlow 4.8s ease-in-out infinite;
                    width: 184px;
                    will-change: transform;
                }
                .orbit-card { z-index: 2; }
                .orbit-pos-1 { top: -2%; left: -6%; }
                .orbit-pos-2 { top: 1%; right: -7%; }
                .orbit-pos-3 { top: 33%; right: -10%; }
                .orbit-pos-4 { bottom: 21%; right: -5%; }
                .orbit-pos-5 { bottom: 18%; left: -6%; }
                .icon-box {
                    width: 36px;
                    height: 36px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .icon-box.success { background: rgba(16, 185, 129, 0.2); color: var(--success); }
                .icon-box.warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
                .icon-box.primary { background: rgba(99, 102, 241, 0.2); color: var(--primary); }
                .icon-box.secondary { background: rgba(236, 72, 153, 0.2); color: var(--secondary); }
                .card-label { font-size: 0.75rem; color: var(--text-muted); }
                .card-value { font-weight: bold; font-size: 0.9rem; }

                .bg-darker {
                    background: linear-gradient(
                        to bottom,
                        rgba(7, 10, 20, 0.42),
                        rgba(8, 11, 24, 0.15)
                    );
                    border-top: 1px solid rgba(255, 255, 255, 0.05);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                }
                .section-title { font-size: clamp(2rem, 4vw, 3rem); margin-bottom: 1rem; }
                .section-subtitle { max-width: 700px; margin: 0 auto; color: var(--text-muted); font-size: 1.1rem; }
                .pain-card {
                    padding: 2rem;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 16px;
                    transition: transform 0.3s;
                }
                .pain-card:hover { transform: translateY(-5px); background: rgba(255, 255, 255, 0.04); }
                .pain-icon { color: var(--danger); margin-bottom: 1rem; }

                .feature-title { font-size: 2.3rem; margin-bottom: 1rem; font-weight: 700; }
                .feature-desc { font-size: 1.05rem; color: var(--text-muted); margin-bottom: 1.5rem; line-height: 1.6; }
                .feature-icon-lg {
                    width: 64px;
                    height: 64px;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 1.5rem;
                }
                .badge-outline {
                    display: inline-flex;
                    align-items: center;
                    border-radius: 999px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    padding: 0.4rem 0.85rem;
                    font-size: 0.85rem;
                    color: #e2e8f0;
                    background: rgba(30, 41, 59, 0.3);
                }
                .bg-primary-soft { background: rgba(99, 102, 241, 0.12); }
                .text-primary { color: var(--primary); }
                .bg-secondary-soft { background: rgba(236, 72, 153, 0.12); }
                .text-secondary { color: var(--secondary); }
                .bg-warning-soft { background: rgba(245, 158, 11, 0.12); }
                .text-warning { color: var(--warning); }

                .glass-panel {
                    width: 100%;
                    max-width: 520px;
                    background: rgba(12, 18, 34, 0.55);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }
                .feature-panel {
                    height: 360px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    padding: 1.1rem;
                }
                .feature-mockup {
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.28);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    overflow: hidden;
                }
                .mockup-header {
                    height: 34px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 12px;
                    background: rgba(255, 255, 255, 0.02);
                }
                .mockup-label { font-size: 0.75rem; color: var(--text-muted); }
                .dots { display: flex; gap: 5px; }
                .dots span { width: 8px; height: 8px; border-radius: 50%; background: rgba(255, 255, 255, 0.22); }
                .mockup-body { padding: 1rem; height: calc(100% - 34px); }

                .orders-body {
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    gap: 1rem;
                }
                .orders-scene {
                    position: relative;
                    height: 130px;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    background: linear-gradient(180deg, rgba(15,23,42,0.45), rgba(15,23,42,0.2));
                    overflow: hidden;
                    padding: 0.75rem;
                }
                .scene-rail {
                    position: absolute;
                    left: 28px;
                    right: 28px;
                    top: 50%;
                    height: 4px;
                    border-radius: 999px;
                    background: linear-gradient(90deg, rgba(99,102,241,0.35), rgba(16,185,129,0.4));
                }
                .scene-stop {
                    position: absolute;
                    top: calc(50% - 26px);
                    transform: translateX(-50%);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 0.35rem;
                    font-size: 0.66rem;
                    color: #cbd5e1;
                    text-align: center;
                    width: 74px;
                }
                .scene-stop.success { color: #86efac; }
                .stop-1 { left: 12%; }
                .stop-2 { left: 37%; }
                .stop-3 { left: 62%; }
                .stop-4 { left: 87%; }
                .stop-dot {
                    width: 11px;
                    height: 11px;
                    border-radius: 999px;
                    background: rgba(148, 163, 184, 0.8);
                    box-shadow: 0 0 12px rgba(148, 163, 184, 0.4);
                }
                .scene-stop.success .stop-dot {
                    background: #10b981;
                    box-shadow: 0 0 14px rgba(16, 185, 129, 0.65);
                }
                .truck-node {
                    position: absolute;
                    top: calc(50% - 16px);
                    left: 8%;
                    width: 28px;
                    height: 28px;
                    border-radius: 9px;
                    display: grid;
                    place-items: center;
                    color: #c4b5fd;
                    background: rgba(99, 102, 241, 0.18);
                    border: 1px solid rgba(129, 140, 248, 0.5);
                    animation: truckMove 5.2s ease-in-out infinite;
                }
                .orders-events {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                .event-pill {
                    border-radius: 999px;
                    padding: 0.36rem 0.68rem;
                    font-size: 0.72rem;
                    color: #dbeafe;
                    background: rgba(30, 58, 138, 0.3);
                    border: 1px solid rgba(96, 165, 250, 0.35);
                }

                .sales-body { display: flex; flex-direction: column; justify-content: space-between; }
                .sales-line-wrap {
                    position: relative;
                    height: 170px;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    background: linear-gradient(180deg, rgba(15, 23, 42, 0.4), rgba(15, 23, 42, 0.12));
                    overflow: hidden;
                    padding: 0.35rem;
                }
                .sales-line-chart {
                    width: 100%;
                    height: 100%;
                }
                .grid-line {
                    stroke: rgba(148, 163, 184, 0.28);
                    stroke-width: 1;
                }
                .grid-line.faded {
                    stroke: rgba(148, 163, 184, 0.15);
                }
                .sales-line-track {
                    fill: none;
                    stroke: rgba(236, 72, 153, 0.2);
                    stroke-width: 4;
                    stroke-linecap: round;
                }
                .sales-line-path {
                    fill: none;
                    stroke: url(#sales-gradient);
                    stroke-width: 4;
                    stroke-linecap: round;
                    stroke-dasharray: 460;
                    stroke-dashoffset: 460;
                    animation: drawLine 2.8s ease-out infinite;
                }
                .sales-line-endpoint {
                    fill: #22d3ee;
                    opacity: 0;
                    animation: endpointPulse 2.8s ease-out infinite;
                }
                .sales-arrow {
                    position: absolute;
                    width: 30px;
                    height: 30px;
                    border-radius: 999px;
                    display: grid;
                    place-items: center;
                    color: #e0e7ff;
                    background: rgba(99, 102, 241, 0.24);
                    border: 1px solid rgba(129, 140, 248, 0.42);
                    transform: translate(26px, 126px) rotate(-32deg);
                    animation: arrowRise 2.8s ease-out infinite;
                }
                .sales-metric {
                    margin-top: 0.9rem;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.45rem;
                    border-radius: 999px;
                    width: fit-content;
                    padding: 0.4rem 0.8rem;
                    background: rgba(16, 185, 129, 0.12);
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    color: #86efac;
                    font-size: 0.8rem;
                }

                .bestseller-body {
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    gap: 0.8rem;
                }
                .podium-scene {
                    height: 170px;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    background: linear-gradient(180deg, rgba(15,23,42,0.4), rgba(15,23,42,0.12));
                    display: flex;
                    align-items: flex-end;
                    justify-content: center;
                    gap: 0.65rem;
                    padding: 0.8rem;
                }
                .podium {
                    width: 31%;
                    border-radius: 12px 12px 8px 8px;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    background: rgba(15, 23, 42, 0.7);
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0.45rem 0.4rem;
                    text-align: center;
                }
                .podium-first {
                    height: 128px;
                    background: linear-gradient(180deg, rgba(245,158,11,0.34), rgba(245,158,11,0.14));
                    border-color: rgba(245, 158, 11, 0.35);
                    animation: winnerBounce 2.2s ease-in-out infinite;
                    position: relative;
                }
                .podium-second {
                    height: 104px;
                    background: linear-gradient(180deg, rgba(99,102,241,0.32), rgba(99,102,241,0.12));
                }
                .podium-third {
                    height: 86px;
                    background: linear-gradient(180deg, rgba(236,72,153,0.3), rgba(236,72,153,0.12));
                }
                .winner-crown {
                    position: absolute;
                    top: -20px;
                    width: 30px;
                    height: 30px;
                    border-radius: 999px;
                    display: grid;
                    place-items: center;
                    background: rgba(251, 191, 36, 0.2);
                    color: #facc15;
                    border: 1px solid rgba(250, 204, 21, 0.5);
                }
                .podium-product {
                    font-size: 0.72rem;
                    color: #e2e8f0;
                    line-height: 1.25;
                }
                .podium-rank {
                    font-size: 0.88rem;
                    font-weight: 800;
                    color: #f8fafc;
                }
                .podium-footer {
                    display: flex;
                    justify-content: flex-start;
                }
                .trend-tag {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.3rem;
                    font-size: 0.7rem;
                    color: #fde68a;
                    background: rgba(245, 158, 11, 0.16);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 999px;
                    padding: 0.2rem 0.5rem;
                }

                .faq-grid { display: grid; gap: 1rem; }
                .faq-item {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid var(--glass-border);
                    border-radius: 12px;
                    overflow: hidden;
                }
                .faq-question {
                    width: 100%;
                    text-align: left;
                    padding: 1.2rem 1.35rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 1rem;
                    font-weight: 600;
                    border: none;
                    color: inherit;
                    background: transparent;
                    cursor: pointer;
                }
                .faq-question:hover { background: rgba(255, 255, 255, 0.04); }
                .faq-answer {
                    max-height: 0;
                    overflow: hidden;
                    transition: max-height 0.35s ease;
                    padding: 0 1.35rem;
                    color: var(--text-muted);
                }
                .faq-answer.open { max-height: 220px; padding-bottom: 1.25rem; }
                .faq-answer p { margin: 0; line-height: 1.55; }

                .cta-section {
                    padding: 8rem 2rem;
                    text-align: center;
                    background: linear-gradient(to bottom, var(--bg-app), #1e1b4b);
                    position: relative;
                    overflow: hidden;
                }
                .cta-title { font-size: clamp(2rem, 4vw, 3rem); margin-bottom: 1rem; }
                .cta-subtitle { color: var(--text-muted); }
                .cta-buttons {
                    margin-top: 2rem;
                    display: flex;
                    gap: 1rem;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .footer { background: #050505; color: var(--text-muted); }
                .footer h4 { color: white; margin-bottom: 1.5rem; font-size: 1.1rem; }
                .footer-links, .social-links { list-style: none; padding: 0; margin: 0; }
                .footer-links li, .social-links li { margin-bottom: 0.8rem; }
                .footer-links a, .social-links a, .footer-links button {
                    color: var(--text-muted);
                    text-decoration: none;
                    transition: color 0.2s;
                    background: transparent;
                    border: none;
                    padding: 0;
                    cursor: pointer;
                    font: inherit;
                }
                .footer-links a:hover, .social-links a:hover, .footer-links button:hover { color: var(--primary); }
                .social-links { display: flex; gap: 1rem; }
                .footer-love { color: #e2e8f0; margin-bottom: 0.5rem; }

                .legal-modal-backdrop {
                    position: fixed;
                    inset: 0;
                    background: rgba(2, 6, 23, 0.72);
                    backdrop-filter: blur(3px);
                    z-index: 1200;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1.2rem;
                }
                .legal-modal {
                    width: min(700px, 100%);
                    max-height: min(78vh, 760px);
                    overflow: auto;
                    background: #090f1f;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 16px;
                    box-shadow: 0 30px 90px rgba(0, 0, 0, 0.5);
                    animation: fadeInUp 0.3s ease forwards;
                }
                .legal-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.2rem 1.2rem 1rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                }
                .legal-modal-header h3 { margin: 0; font-size: 1.2rem; }
                .legal-close {
                    width: 34px;
                    height: 34px;
                    border-radius: 999px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    background: transparent;
                    color: #cbd5e1;
                    cursor: pointer;
                    font-size: 1.2rem;
                    line-height: 1;
                }
                .legal-modal-body { padding: 1.1rem 1.2rem 1.4rem; }
                .legal-modal-body p {
                    margin: 0 0 0.9rem;
                    color: #cbd5e1;
                    line-height: 1.6;
                }

                .glow-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
                .glow-orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.3; }
                .glow-1 { top: -10%; left: -10%; width: 50vw; height: 50vw; background: var(--primary); }
                .glow-2 { bottom: -10%; right: -10%; width: 50vw; height: 50vw; background: var(--secondary); }

                .fade-in-up { opacity: 0; transform: translateY(20px); animation: fadeInUp 0.8s forwards; }
                .delay-100 { animation-delay: 0.1s; }
                .delay-200 { animation-delay: 0.2s; }
                .delay-300 { animation-delay: 0.3s; }
                .delay-400 { animation-delay: 0.4s; }
                .delay-500 { animation-delay: 0.5s; }

                @keyframes fadeInUp {
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes orbitDrift {
                    0% { transform: translate3d(0px, 0px, 0px) scale(1); }
                    25% { transform: translate3d(6px, -10px, 0px) scale(1.01); }
                    50% { transform: translate3d(-5px, -16px, 0px) scale(1); }
                    75% { transform: translate3d(-8px, -8px, 0px) scale(0.995); }
                    100% { transform: translate3d(0px, 0px, 0px) scale(1); }
                }
                @keyframes pulseGlow {
                    0%, 100% { box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
                    50% { box-shadow: 0 14px 34px rgba(99,102,241,0.24); }
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes bounceDown {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(4px); }
                }
                @keyframes truckMove {
                    0% { transform: translateX(0); }
                    52% { transform: translateX(212px); }
                    100% { transform: translateX(252px); }
                }
                @keyframes drawLine {
                    0% { stroke-dashoffset: 460; }
                    70% { stroke-dashoffset: 0; }
                    100% { stroke-dashoffset: 0; }
                }
                @keyframes arrowRise {
                    0% {
                        transform: translate(26px, 126px) rotate(-32deg) scale(0.88);
                        opacity: 0;
                    }
                    20% { opacity: 1; }
                    100% {
                        transform: translate(264px, 28px) rotate(-32deg) scale(1);
                        opacity: 1;
                    }
                }
                @keyframes endpointPulse {
                    0%, 68% { opacity: 0; r: 5; }
                    82% { opacity: 1; r: 6; }
                    100% { opacity: 0.75; r: 5; }
                }
                @keyframes winnerBounce {
                    0%, 100% { transform: translateY(0); }
                    45% { transform: translateY(-8px); }
                }

                @media (prefers-reduced-motion: reduce) {
                    .floating-card,
                    .title-chip,
                    .abstract-circle,
                    .truck-node,
                    .sales-line-path,
                    .sales-arrow,
                    .sales-line-endpoint,
                    .podium-first,
                    .fade-in-up {
                        animation: none !important;
                        transform: none !important;
                        opacity: 1 !important;
                    }
                }

                @media (max-width: 900px) {
                    .grid-split { grid-template-columns: 1fr; gap: 3rem; }
                    .order-1, .order-2 { order: unset; }
                    .feature-panel { max-width: 100%; }
                    .hero-title-wrap { padding: 5.8rem 3.8rem 4.4rem; }
                    .orbit-pos-1 { top: -2%; left: 0%; }
                    .orbit-pos-2 { top: 0%; right: 0%; }
                    .orbit-pos-3 { top: 31%; right: -5%; }
                    .orbit-pos-4 { bottom: 22%; right: -2%; }
                    .orbit-pos-5 { bottom: 20%; left: -2%; }
                }
                @media (max-width: 768px) {
                    .hero-title { font-size: 2.35rem; }
                    .hero-title-wrap { padding: 1rem 0 0.4rem; }
                    .hero-orbit { display: none; }
                    .floating-card { padding: 0.7rem; gap: 0.6rem; }
                    .card-value { font-size: 0.8rem; }
                    .cta-buttons { flex-direction: column; }
                }
            `}</style>
        </div>
    );
};

export default LandingPage;

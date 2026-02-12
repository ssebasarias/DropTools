import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
    Zap, ArrowRight, TrendingUp, Shield, BarChart2, Package, 
    CheckCircle, ChevronDown, HelpCircle, Activity, Box, 
    Truck, Instagram, Facebook, Mail
} from 'lucide-react';
import PublicNavbar from '../components/layout/PublicNavbar';

// --- Components ---

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

            <h1 className="hero-title fade-in-up delay-200">
                Tu Operación de Dropshipping,<br />
                <span className="text-gradient-primary">En Piloto Automático.</span>
            </h1>

            <p className="hero-subtitle fade-in-up delay-300">
                Deja de perder tiempo en tareas repetitivas. Automatiza tus reportes, 
                descubre productos ganadores y toma el control total de tus ventas con DropTools.
            </p>

            <div className="hero-cta fade-in-up delay-400">
                <Link to="/register" className="btn-primary-lg icon-hover-move">
                    Comenzar Prueba Gratis <ArrowRight size={20} />
                </Link>
                <div className="hero-stat">
                    <span className="stat-dot"></span> +10,000 Órdenes Analizadas
                </div>
            </div>

            {/* Abstract Dynamic Visualization */}
            <div className="hero-visual fade-in-up delay-500">
                <div className="floating-card card-1">
                    <div className="icon-box success"><CheckCircle size={20} /></div>
                    <div>
                        <div className="card-label">Reporte Enviado</div>
                        <div className="card-value">Orden #29301</div>
                    </div>
                </div>
                <div className="floating-card card-2">
                    <div className="icon-box warning"><TrendingUp size={20} /></div>
                    <div>
                        <div className="card-label">Producto Ganador</div>
                        <div className="card-value">+200 Ventas/día</div>
                    </div>
                </div>
                <div className="floating-card card-3">
                    <div className="icon-box primary"><Activity size={20} /></div>
                    <div>
                        <div className="card-label">Eficiencia Operativa</div>
                        <div className="card-value">+45% vs mes anterior</div>
                    </div>
                </div>
                <div className="abstract-circle"></div>
            </div>
        </div>
    </div>
);

const PainPointSection = () => (
    <div className="section-padding bg-darker">
        <div className="container text-center">
            <h2 className="section-title">¿Cansado de operar a ciegas?</h2>
            <p className="section-subtitle">
                Sabemos lo frustrante que es ver órdenes estancadas y no saber por qué.
                La falta de información mata tu rentabilidad.
            </p>
            <div className="grid-3">
                <div className="pain-card">
                    <div className="pain-icon"><Truck size={32} /></div>
                    <h3>Órdenes Estancadas</h3>
                    <p>Paquetes que no se mueven y clientes reclamando.</p>
                </div>
                <div className="pain-card">
                    <div className="pain-icon"><HelpCircle size={32} /></div>
                    <h3>Falta de Datos</h3>
                    <p>Decisiones basadas en intuición en lugar de métricas reales.</p>
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

const FeatureSection = ({ icon: Icon, title, description, badge, imagePlace, color = 'primary' }) => (
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
                    {/* Abstract Representation of the Feature */}
                    <div className="feature-mockup">
                        <div className="mockup-header">
                            <div className="dots"><span></span><span></span><span></span></div>
                        </div>
                        <div className="mockup-body">
                            <div className="skeleton-line w-75"></div>
                            <div className="skeleton-line w-50"></div>
                            <div className="skeleton-graph"></div>
                            <div className={`floating-badge float-${imagePlace}`}>
                                <Icon size={16} /> Procesando...
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
);

const FAQItem = ({ question, answer }) => {
    const [isOpen, setIsOpen] = useState(false);
    return (
        <div className="faq-item" onClick={() => setIsOpen(!isOpen)}>
            <div className="faq-question">
                {question}
                {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </div>
            <div className={`faq-answer ${isOpen ? 'open' : ''}`}>
                <p>{answer}</p>
            </div>
        </div>
    );
};

const FAQSection = () => (
    <div className="section-padding">
        <div className="container max-w-800">
            <div className="text-center mb-16">
                <h2 className="section-title">Preguntas Frecuentes</h2>
                <p className="text-muted">Todo lo que necesitas saber antes de empezar.</p>
            </div>
            <div className="faq-grid">
                <FAQItem 
                    question="¿Necesito conocimientos de programación?"
                    answer="Para nada. DropTools está diseñado para ser intuitivo y fácil de usar. Conectas tus cuentas y nosotros nos encargamos del resto."
                />
                <FAQItem 
                    question="¿Es seguro conectar mi cuenta de Dropi?"
                    answer="Absolutamente. Utilizamos encriptación de grado bancario y nunca compartimos tus credenciales o datos de ventas con terceros."
                />
                <FAQItem 
                    question="¿Puedo cancelar en cualquier momento?"
                    answer="Sí, no tenemos contratos forzosos. Puedes cancelar tu suscripción cuando quieras desde tu panel de control."
                />
                <FAQItem 
                    question="¿Cómo funciona el buscador de productos ganadores?"
                    answer="Analizamos miles de productos en tiempo real, cruzando datos de ventas, saturación de competidores y tendencias para sugerirte solo lo que tiene alto potencial de venta."
                />
            </div>
        </div>
    </div>
);

const CTASection = () => (
    <div className="cta-section">
        <div className="container text-center relative z-10">
            <h2 className="cta-title">¿Listo para escalar tu negocio?</h2>
            <p className="cta-subtitle">Únete a los dropshippers que ya están automatizando su éxito.</p>
            <div className="cta-buttons">
                <Link to="/register" className="btn-primary-lg">Crear Cuenta Ahora</Link>
                <a href="#contact" className="btn-secondary-lg">Contactar Soporte</a>
            </div>
        </div>
        <div className="cta-bg-glow" />
    </div>
);

const Footer = () => (
    <footer className="footer section-padding-sm border-t glass-border">
        <div className="container grid-4">
            <div className="footer-col">
                <div className="brand-logo mb-4">
                    <Zap size={24} className="text-primary" />
                    <span className="font-bold text-xl text-white">DropTools</span>
                </div>
                <p className="text-muted text-sm">
                    La plataforma definitiva para automatización y análisis de dropshipping en LATAM.
                </p>
            </div>
            <div className="footer-col">
                <h4>Producto</h4>
                <ul className="footer-links">
                    <li><a href="#">Características</a></li>
                    <li><a href="#">Precios</a></li>
                    <li><a href="#">Roadmap</a></li>
                </ul>
            </div>
            <div className="footer-col">
                <h4>Legal</h4>
                <ul className="footer-links">
                    <li><a href="#">Términos de Servicio</a></li>
                    <li><a href="#">Política de Privacidad</a></li>
                    <li><a href="#">Reembolsos</a></li>
                </ul>
            </div>
            <div className="footer-col">
                <h4>Contacto</h4>
                <ul className="social-links">
                    <li><a href="#"><Mail size={20} /></a></li>
                    <li><a href="#"><Instagram size={20} /></a></li>
                    <li><a href="#"><Facebook size={20} /></a></li>
                </ul>
            </div>
        </div>
        <div className="container text-center mt-12 pt-8 border-t glass-border-light">
            <p className="text-muted text-sm">&copy; 2026 DropTools. Todos los derechos reservados.</p>
        </div>
    </footer>
);

const LandingPage = () => {
    return (
        <div className="landing-page">
            <PublicNavbar />
            
            <HeroSection />
            
            <PainPointSection />
            
            <FeatureSection 
                icon={Truck}
                title="Mantén tus órdenes en movimiento"
                description="Nuestro Reportador Automático detecta y gestiona las órdenes estancadas sin que muevas un dedo. Mejora la eficiencia de tu transportadora y asegura entregas rápidas."
                badge="Eficiencia"
                imagePlace="right"
                color="primary"
            />

            <FeatureSection 
                icon={BarChart2}
                title="Lleva tus ventas a otro nivel"
                description="No es solo vender, es entender. Accede a análisis detallados, conoce qué pasa con tus órdenes y toma decisiones basadas en datos reales."
                badge="Analítica"
                imagePlace="left"
                color="secondary"
            />

            <FeatureSection 
                icon={TrendingUp}
                title="Descubre tu próximo Bestseller"
                description="Nuestro algoritmo analiza la saturación de competidores y te sugiere productos con alto potencial. Deja de vender lo que todos venden."
                badge="Winner Alert"
                imagePlace="right"
                color="warning"
            />

            <FAQSection />
            
            <CTASection />
            
            <Footer />

            <style>{`
                /* --- Layout Utilities --- */
                .landing-page {
                    min-height: 100vh;
                    background: var(--bg-app);
                    color: var(--text-main);
                    overflow-x: hidden;
                    font-family: 'Inter', sans-serif;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1.5rem;
                }
                .max-w-800 { max-width: 800px; }
                .section-padding { padding: 6rem 0; }
                .section-padding-sm { padding: 4rem 0; }
                .grid-split {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 4rem;
                    align-items: center;
                }
                .grid-3 {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
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
                
                /* --- Hero Section --- */
                .hero-section {
                    min-height: 90vh; /* Taller hero */
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    padding-top: 8rem;
                    padding-bottom: 4rem;
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
                .hero-title {
                    font-size: clamp(2.5rem, 5vw, 4.5rem);
                    font-weight: 800;
                    line-height: 1.1;
                    margin-bottom: 1.5rem;
                    letter-spacing: -0.02em;
                }
                .text-gradient-primary {
                    background: linear-gradient(135deg, var(--primary), #a5b4fc);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .hero-subtitle {
                    font-size: 1.25rem;
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
                
                /* --- Buttons --- */
                .btn-primary-lg {
                    background: var(--primary);
                    color: white;
                    padding: 1rem 2.5rem;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 1.125rem;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.75rem;
                    box-shadow: 0 10px 30px -10px var(--primary-rgb);
                    transition: all 0.3s ease;
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
                    font-size: 1.125rem;
                    text-decoration: none;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                }
                .btn-secondary-lg:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
                .icon-hover-move svg { transition: transform 0.3s ease; }
                .icon-hover-move:hover svg { transform: translateX(5px); }

                /* --- Visual Elements --- */
                .hero-visual {
                    margin-top: 5rem;
                    position: relative;
                    width: 100%;
                    max-width: 600px;
                    height: 300px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .abstract-circle {
                    width: 300px;
                    height: 300px;
                    border-radius: 50%;
                    background: radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%);
                    border: 1px dashed rgba(99,102,241,0.2);
                    animation: spin 60s linear infinite;
                }
                .floating-card {
                    position: absolute;
                    background: rgba(15, 23, 42, 0.8);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    padding: 1rem;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    animation: float 6s ease-in-out infinite;
                }
                .card-1 { top: 10%; left: 0; animation-delay: 0s; }
                .card-2 { top: 50%; right: -10%; animation-delay: 2s; }
                .card-3 { bottom: 0; left: 10%; animation-delay: 4s; }
                
                .icon-box {
                    width: 40px; height: 40px;
                    border-radius: 10px;
                    display: flex; align-items: center; justify-content: center;
                }
                .icon-box.success { background: rgba(16, 185, 129, 0.2); color: var(--success); }
                .icon-box.warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
                .icon-box.primary { background: rgba(99, 102, 241, 0.2); color: var(--primary); }
                
                .card-label { font-size: 0.75rem; color: var(--text-muted); }
                .card-value { font-weight: bold; font-size: 0.9rem; }

                /* --- Pain Points --- */
                .bg-darker { background: rgba(0,0,0,0.2); }
                .pain-card {
                    padding: 2rem;
                    background: rgba(255,255,255,0.02);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 16px;
                    transition: transform 0.3s;
                }
                .pain-card:hover { transform: translateY(-5px); background: rgba(255,255,255,0.04); }
                .pain-icon { color: var(--danger); margin-bottom: 1rem; }
                
                /* --- Feature Sections --- */
                .feature-title { font-size: 2.5rem; margin-bottom: 1rem; font-weight: 700; }
                .feature-desc { font-size: 1.1rem; color: var(--text-muted); margin-bottom: 2rem; line-height: 1.6; }
                .feature-icon-lg {
                    width: 64px; height: 64px;
                    border-radius: 16px;
                    display: flex; align-items: center; justify-content: center;
                    margin-bottom: 1.5rem;
                }
                .bg-primary-soft { background: rgba(99, 102, 241, 0.1); }
                .text-primary { color: var(--primary); }
                .bg-secondary-soft { background: rgba(236, 72, 153, 0.1); }
                .text-secondary { color: var(--secondary); }
                .bg-warning-soft { background: rgba(245, 158, 11, 0.1); }
                .text-warning { color: var(--warning); }

                .feature-panel {
                    height: 350px;
                    display: flex; align-items: center; justify-content: center;
                    position: relative;
                }
                .feature-mockup { width: 80%; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); overflow: hidden; }
                .mockup-header { height: 30px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; padding: 0 10px; background: rgba(255,255,255,0.02); }
                .dots { display: flex; gap: 5px; }
                .dots span { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.2); }
                .mockup-body { padding: 20px; position: relative; height: 200px; }
                .skeleton-line { height: 10px; background: rgba(255,255,255,0.1); margin-bottom: 10px; border-radius: 4px; }
                .w-75 { width: 75%; }
                .w-50 { width: 50%; }
                .skeleton-graph { height: 100px; background: linear-gradient(to top, rgba(99,102,241,0.2), transparent); border-radius: 8px; margin-top: 20px; border-bottom: 2px solid rgba(99,102,241,0.5); }
                
                .floating-badge {
                    position: absolute; bottom: 20px; right: 20px;
                    background: var(--bg-app); border: 1px solid var(--glass-border);
                    padding: 8px 16px; border-radius: 30px;
                    display: flex; gap: 8px; align-items: center;
                    font-size: 0.8rem; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                }
                .float-left { left: 20px; right: auto; }

                /* --- FAQ --- */
                .faq-grid { display: grid; gap: 1rem; }
                .faq-item {
                    background: rgba(255,255,255,0.03);
                    border: 1px solid var(--glass-border);
                    border-radius: 12px;
                    overflow: hidden;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .faq-item:hover { background: rgba(255,255,255,0.05); }
                .faq-question {
                    padding: 1.5rem;
                    display: flex; justify-content: space-between; align-items: center;
                    font-weight: 600;
                }
                .faq-answer {
                    max-height: 0; overflow: hidden;
                    transition: max-height 0.3s ease;
                    padding: 0 1.5rem;
                    color: var(--text-muted);
                }
                .faq-answer.open { max-height: 200px; padding-bottom: 1.5rem; }

                /* --- CTA & Footer --- */
                .cta-section {
                    padding: 8rem 2rem;
                    text-align: center;
                    background: linear-gradient(to bottom, var(--bg-app), #1e1b4b);
                    position: relative;
                    overflow: hidden;
                }
                .cta-title { font-size: 3rem; margin-bottom: 1rem; }
                .cta-buttons { margin-top: 2rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
                
                .footer { background: #050505; color: var(--text-muted); }
                .footer h4 { color: white; margin-bottom: 1.5rem; font-size: 1.1rem; }
                .footer-links, .social-links { list-style: none; padding: 0; }
                .footer-links li, .social-links li { margin-bottom: 0.8rem; }
                .footer-links a, .social-links a { color: var(--text-muted); text-decoration: none; transition: color 0.2s; }
                .footer-links a:hover, .social-links a:hover { color: var(--primary); }
                .social-links { display: flex; gap: 1rem; }

                /* --- Animations --- */
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
                
                @keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
                @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0px); } }
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

                /* Responsive */
                @media (max-width: 768px) {
                    .grid-split { grid-template-columns: 1fr; gap: 3rem; }
                    .order-1, .order-2 { order: unset; }
                    .hero-title { font-size: 2.5rem; }
                    .cta-buttons { flex-direction: column; }
                }
            `}</style>
        </div>
    );
};

export default LandingPage;

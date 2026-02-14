// Configuración de Google OAuth
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

// Scopes que solicitamos a Google
export const GOOGLE_SCOPES = [
    'openid',
    'email',
    'profile'
].join(' ');

// Configuración de Google OAuth
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '873344941573-7oqihc52h8mtp8gk80ebjakamtd81gi0.apps.googleusercontent.com';

// Scopes que solicitamos a Google
export const GOOGLE_SCOPES = [
    'openid',
    'email',
    'profile'
].join(' ');

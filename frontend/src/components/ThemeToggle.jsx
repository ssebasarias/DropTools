import React, { useEffect, useState } from 'react';

const THEME_KEY = 'dahell_theme';
const EYE_KEY = 'dahell_eye_protect';

function applyPrefs(theme, eye) {
  const root = document.documentElement;
  if (theme === 'light') root.setAttribute('data-theme', 'light');
  else root.removeAttribute('data-theme');

  if (eye) root.setAttribute('data-eye', 'on');
  else root.removeAttribute('data-eye');
}

const ThemeToggle = () => {
  const [theme, setTheme] = useState('dark');
  const [eyeProtect, setEyeProtect] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem(THEME_KEY) || 'dark';
    const savedEye = localStorage.getItem(EYE_KEY) === 'true';
    setTheme(savedTheme);
    setEyeProtect(savedEye);
    applyPrefs(savedTheme, savedEye);
  }, []);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
    applyPrefs(theme, eyeProtect);
  }, [theme, eyeProtect]);

  return (
    <div className="theme-toggle">
      <button
        className={theme === 'dark' ? 'active' : ''}
        aria-pressed={theme === 'dark'}
        onClick={() => setTheme('dark')}
        title="Modo oscuro"
      >
        🌑
      </button>
      <button
        className={theme === 'light' ? 'active' : ''}
        aria-pressed={theme === 'light'}
        onClick={() => setTheme('light')}
        title="Modo claro"
      >
        ☀️
      </button>
      <button
        className={eyeProtect ? 'active' : ''}
        aria-pressed={eyeProtect}
        onClick={() => setEyeProtect((s) => !s)}
        title="Protección ocular (filtro de luz azul)"
      >
        🟡
      </button>
    </div>
  );
};

export default ThemeToggle;

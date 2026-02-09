import React, { useEffect, useState } from 'react';

const THEME_KEY = 'droptools_theme';
const EYE_KEY = 'droptools_eye_protect';

function applyPrefs(theme, eye) {
  const root = document.documentElement;
  if (theme === 'light') root.setAttribute('data-theme', 'light');
  else root.removeAttribute('data-theme');

  if (eye) root.setAttribute('data-eye', 'on');
  else root.removeAttribute('data-eye');
}

const ThemeToggle = () => {
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || 'dark');
  const [eyeProtect, setEyeProtect] = useState(() => localStorage.getItem(EYE_KEY) === 'true');

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
    localStorage.setItem(EYE_KEY, String(eyeProtect));
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

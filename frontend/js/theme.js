(function () {
    const storageKey = 'eduged_libre-theme';
    const themes = ['dark', 'light'];

    function getStoredTheme() {
        const storedTheme = localStorage.getItem(storageKey);
        return themes.includes(storedTheme) ? storedTheme : 'dark';
    }

    function applyTheme(theme) {
        const selectedTheme = themes.includes(theme) ? theme : 'dark';
        document.documentElement.dataset.theme = selectedTheme;
        localStorage.setItem(storageKey, selectedTheme);

        document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
            const isLight = selectedTheme === 'light';
            button.setAttribute('aria-pressed', String(isLight));
            button.setAttribute('aria-label', isLight ? 'Ativar tema escuro' : 'Ativar tema claro');
            button.innerHTML = isLight
                ? '<i class="fa-solid fa-moon" aria-hidden="true"></i><span>Tema escuro</span>'
                : '<i class="fa-solid fa-sun" aria-hidden="true"></i><span>Tema claro</span>';
        });
    }

    window.toggleTheme = function () {
        applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
    };

    applyTheme(getStoredTheme());
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
            button.addEventListener('click', window.toggleTheme);
        });
        applyTheme(document.documentElement.dataset.theme);
    });
})();

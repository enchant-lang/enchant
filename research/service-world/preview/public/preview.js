/* Presentation only. State and action authorization live in the native writer. */
(() => {
  const root = document.documentElement;
  try { root.dataset.theme = localStorage.getItem('connected-theme') || 'light'; } catch {}
  document.querySelectorAll('[data-demo-theme], [data-theme-toggle]').forEach(button => {
    button.addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('connected-theme', root.dataset.theme); } catch {}
    });
  });
  function drawer(open) {
    document.body.classList.toggle('demo-rail-open', open);
    document.querySelector('.app')?.classList.toggle('rail-open', open);
    document.querySelector('[data-rail-toggle]')?.setAttribute('aria-expanded', String(open));
  }
  document.querySelector('[data-rail-toggle]')?.addEventListener('click', () => drawer(!document.body.classList.contains('demo-rail-open')));
  document.querySelectorAll('[data-rail-close]').forEach(b => b.addEventListener('click', () => drawer(false)));
  document.querySelectorAll('[data-palette-open]').forEach(b => b.addEventListener('click', () => {
    const palette = document.querySelector('#palette');
    if (palette) { palette.hidden = !palette.hidden; palette.querySelector('input')?.focus(); }
  }));
  document.querySelector('#palette-input')?.addEventListener('input', e => {
    document.querySelectorAll('[data-palette-text]').forEach(row => row.hidden = !row.dataset.paletteText.toLowerCase().includes(e.target.value.toLowerCase()));
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { drawer(false); const p = document.querySelector('#palette'); if (p) p.hidden = true; }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); document.querySelector('[data-palette-open]')?.click(); }
  });
  // Never resubmit a write automatically. Native forms navigate to a fresh basis.
  document.querySelectorAll('form[method="post"]').forEach(form => form.addEventListener('submit', () => {
    form.setAttribute('aria-busy', 'true');
  }));
})();

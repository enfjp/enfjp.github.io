/* Progressive enhancement. Public text and links remain usable without JavaScript. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const menuButton = document.querySelector('[data-menu-button]');
  const mobileMenu = document.querySelector('[data-mobile-menu]');
  const closeMenu = () => {
    if (!menuButton || !mobileMenu) return;
    mobileMenu.hidden = true;
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.querySelector('[data-menu-word]').textContent = 'Menu';
  };
  menuButton?.addEventListener('click', () => {
    const opening = menuButton.getAttribute('aria-expanded') !== 'true';
    mobileMenu.hidden = !opening;
    menuButton.setAttribute('aria-expanded', String(opening));
    menuButton.querySelector('[data-menu-word]').textContent = opening ? 'Close' : 'Menu';
  });
  mobileMenu?.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
      closeMenu(); menuButton.focus();
    }
  });
  window.matchMedia('(min-width: 721px)').addEventListener('change', e => { if (e.matches) closeMenu(); });

  const tabs = Array.from(document.querySelectorAll('[data-gallery-tab]'));
  const selectTab = button => {
    tabs.forEach(t => { t.setAttribute('aria-selected', String(t === button)); t.tabIndex = t === button ? 0 : -1; });
    document.querySelectorAll('[data-gallery-panel]').forEach(panel => {
      panel.hidden = panel.id !== button.getAttribute('aria-controls');
    });
  };
  tabs.forEach((button, index) => {
    button.addEventListener('click', () => selectTab(button));
    button.addEventListener('keydown', event => {
      let target;
      if (event.key === 'ArrowRight') target = tabs[(index + 1) % tabs.length];
      if (event.key === 'ArrowLeft') target = tabs[(index - 1 + tabs.length) % tabs.length];
      if (event.key === 'Home') target = tabs[0];
      if (event.key === 'End') target = tabs[tabs.length - 1];
      if (target) { event.preventDefault(); selectTab(target); target.focus(); }
    });
  });
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      const value = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      document.querySelectorAll('[data-photo-item]').forEach(item => {
        item.hidden = value !== 'all' && item.dataset.collection !== value;
        item.style.display = item.hidden ? 'none' : '';
      });
    });
  });
  document.querySelectorAll('[data-copy-bibtex]').forEach(button => {
    button.addEventListener('click', async () => {
      const target = document.getElementById(button.dataset.copyBibtex);
      const status = document.querySelector('[data-copy-status]');
      if (!target || !status) return;
      try {
        if (!navigator.clipboard || !window.isSecureContext) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(target.textContent);
        status.textContent = 'Citation copied.';
      } catch (_) {
        const selection = window.getSelection();
        const range = document.createRange(); range.selectNodeContents(target);
        selection.removeAllRanges(); selection.addRange(range);
        status.textContent = 'Citation selected. Press ⌘C on Mac or Ctrl+C on Windows to copy.';
      }
    });
  });
  const dialog = document.querySelector('[data-lightbox]');
  const photoLinks = Array.from(document.querySelectorAll('[data-photo-open]'));
  if (!dialog || !photoLinks.length || typeof dialog.showModal !== 'function') return;
  const photo = dialog.querySelector('[data-lb-image]');
  const title = dialog.querySelector('[data-lb-title]');
  const detail = dialog.querySelector('[data-lb-detail]');
  const count = dialog.querySelector('[data-lb-count]');
  const error = dialog.querySelector('[data-lb-error]');
  let active = [], current = 0, opener;
  const show = index => {
    current = (index + active.length) % active.length;
    const link = active[current];
    error.hidden = true; photo.hidden = false;
    photo.alt = link.dataset.alt || '';
    photo.src = link.href;
    title.textContent = link.dataset.title || 'Untitled';
    detail.textContent = link.dataset.detail || '';
    count.textContent = `${String(current + 1).padStart(2, '0')} / ${String(active.length).padStart(2, '0')}`;
    dialog.querySelectorAll('[data-lb-step]').forEach(b => b.hidden = active.length < 2);
  };
  photo.onerror = () => { photo.hidden = true; error.hidden = false; };
  photoLinks.forEach(link => link.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault(); opener = link;
    active = photoLinks.filter(l => !l.closest('[data-photo-item]')?.hidden && l.getClientRects().length > 0);
    show(active.indexOf(link)); dialog.showModal(); document.body.classList.add('modal-open');
  }));
  dialog.querySelector('[data-lb-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { document.body.classList.remove('modal-open'); opener?.focus(); });
  dialog.querySelectorAll('[data-lb-step]').forEach(b => b.addEventListener('click', () => show(current + Number(b.dataset.lbStep))));
  dialog.addEventListener('keydown', e => {
    if (e.key === 'Tab') {
      const controls = Array.from(dialog.querySelectorAll('button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')).filter(el => el.getClientRects().length > 0);
      const first = controls[0], last = controls[controls.length - 1];
      if (first && e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (last && !e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    if (e.key === 'ArrowRight') { e.preventDefault(); show(current + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(current - 1); }
  });
  let touchX = null, touchY = null;
  dialog.addEventListener('touchstart', e => { if (e.touches.length === 1) { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; } else { touchX = null; } }, {passive:true});
  dialog.addEventListener('touchend', e => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    const dy = e.changedTouches[0].clientY - touchY;
    if (Math.abs(dx) > 65 && Math.abs(dx) > Math.abs(dy) * 1.5) show(current + (dx < 0 ? 1 : -1));
    touchX = null;
  }, {passive:true});
})();

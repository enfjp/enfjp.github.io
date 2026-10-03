(() => {
  'use strict';
  const photos = Array.from(document.querySelectorAll('[data-sg-work]'));
  const dialog = document.getElementById('sg-viewer');
  if (!photos.length || !dialog) return;
  const image = document.getElementById('sg-viewer-image');
  const title = document.getElementById('sg-viewer-title');
  const location = document.getElementById('sg-viewer-location');
  const categoryName = document.getElementById('sg-viewer-category');
  const previous = document.getElementById('sg-previous');
  const next = document.getElementById('sg-next');
  const close = document.getElementById('sg-close');
  const grid = document.getElementById('sg-grid');
  const filters = Array.from(document.querySelectorAll('[data-sg-filter]'));
  let visible = photos.slice();
  let current = 0;
  let opener = null;
  let oldOverflow = '';
  let touchStart = null;
  let activeCategory = 'all';

  function render() {
    const figure = visible[current];
    if (!figure) return;
    const source = figure.querySelector('.sg-photo-link');
    dialog.classList.remove('failed');
    image.alt = figure.querySelector('img').alt;
    image.src = source.href;
    title.textContent = figure.dataset.title;
    if (location) {
      location.textContent = figure.dataset.location || '';
      location.hidden = !location.textContent;
    }
    categoryName.textContent = figure.dataset.categoryName;
    previous.hidden = next.hidden = visible.length < 2;
    // Adjacent full-size files load only after the visitor opens a photograph.
    if (visible.length > 1) {
      const preload = new Image();
      preload.src = visible[(current + 1) % visible.length].querySelector('.sg-photo-link').href;
    }
  }

  function step(amount) {
    if (!visible.length) return;
    current = (current + amount + visible.length) % visible.length;
    render();
  }

  function applyCategory() {
    photos.forEach(photo => {
      photo.hidden = activeCategory !== 'all' && photo.dataset.category !== activeCategory;
    });
    visible = photos.filter(photo => !photo.hidden);
    grid.classList.toggle('is-filtered', activeCategory !== 'all');
  }

  filters.forEach(button => button.addEventListener('click', () => {
    activeCategory = button.dataset.sgFilter;
    filters.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    applyCategory();
  }));

  const filterBar = document.querySelector('.sg-filters');
  if (filterBar) filterBar.hidden = false;

  function bindFigure(figure) {
    const link = figure.querySelector('.sg-photo-link');
    if (!link || link.dataset.sgViewerBound === 'true') return;
    link.dataset.sgViewerBound = 'true';
    link.addEventListener('click', event => {
      if (typeof dialog.showModal !== 'function' || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = link;
      visible = photos.filter(photo => !photo.hidden);
      current = visible.indexOf(figure);
      oldOverflow = document.body.style.overflow;
      render();
      dialog.showModal();
      document.body.style.overflow = 'hidden';
    });
  }

  photos.forEach(bindFigure);

  image.addEventListener('error', () => dialog.classList.add('failed'));
  image.addEventListener('load', () => dialog.classList.remove('failed'));
  close.addEventListener('click', () => dialog.close());
  previous.addEventListener('click', () => step(-1));
  next.addEventListener('click', () => step(1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight') {event.preventDefault(); step(1);}
    if (event.key === 'ArrowLeft') {event.preventDefault(); step(-1);}
  });
  dialog.addEventListener('close', () => {
    document.body.style.overflow = oldOverflow;
    if (opener && opener.isConnected) opener.focus({preventScroll: true});
  });

  const stage = dialog.querySelector('.sg-stage');
  stage.addEventListener('touchstart', event => {
    touchStart = event.touches.length === 1 ? [event.touches[0].clientX, event.touches[0].clientY] : null;
  }, {passive: true});
  stage.addEventListener('touchend', event => {
    if (!touchStart || event.changedTouches.length !== 1) return;
    const dx = event.changedTouches[0].clientX - touchStart[0];
    const dy = event.changedTouches[0].clientY - touchStart[1];
    touchStart = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);
  }, {passive: true});

  // Progressive enhancement: the static site still contains ordinary pagination
  // links for no-JS browsers and crawlers. Modern browsers automatically fetch
  // the next page when the visitor approaches the bottom of the current grid.
  const pager = document.querySelector('.sg-pagination');
  const firstNext = pager && pager.querySelector('a[rel="next"]');
  if (!pager || !firstNext || !('IntersectionObserver' in window) || !('fetch' in window) || !('DOMParser' in window)) return;

  let nextUrl = new URL(firstNext.getAttribute('href'), window.location.href).href;
  let loading = false;
  let retries = 0;
  const status = document.createElement('p');
  status.className = 'sg-load-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  pager.classList.add('sg-auto-pagination');
  pager.replaceChildren(status);

  function absoluteUrl(value, base) {
    try { return new URL(value, base).href; }
    catch (_) { return value; }
  }

  function normalizeFigureUrls(figure, base) {
    for (const anchor of figure.querySelectorAll('a[href]')) {
      anchor.setAttribute('href', absoluteUrl(anchor.getAttribute('href'), base));
    }
    for (const img of figure.querySelectorAll('img')) {
      if (img.hasAttribute('src')) img.setAttribute('src', absoluteUrl(img.getAttribute('src'), base));
      if (img.hasAttribute('srcset')) {
        const srcset = img.getAttribute('srcset').split(',').map(item => {
          const parts = item.trim().split(/\s+/);
          return absoluteUrl(parts[0], base) + (parts[1] ? ' ' + parts[1] : '');
        }).join(', ');
        img.setAttribute('srcset', srcset);
      }
    }
  }

  async function loadNextPage() {
    if (loading || !nextUrl) return;
    loading = true;
    status.textContent = 'Loading more photographs…';
    try {
      const response = await fetch(nextUrl, {credentials: 'same-origin'});
      if (!response.ok) throw new Error('Unable to load the next gallery page.');
      const markup = await response.text();
      const parsed = new DOMParser().parseFromString(markup, 'text/html');
      const sourceGrid = parsed.getElementById('sg-grid');
      if (!sourceGrid) throw new Error('The next gallery page is missing its photo grid.');

      const newFigures = Array.from(sourceGrid.querySelectorAll('[data-sg-work]'));
      for (const figure of newFigures) {
        normalizeFigureUrls(figure, nextUrl);
        grid.appendChild(figure);
        photos.push(figure);
        bindFigure(figure);
      }
      applyCategory();

      const nextLink = parsed.querySelector('.sg-pagination a[rel="next"]');
      nextUrl = nextLink ? absoluteUrl(nextLink.getAttribute('href'), nextUrl) : '';
      retries = 0;
      status.textContent = nextUrl ? '' : 'End of gallery.';
      if (!nextUrl) observer.disconnect();
    } catch (error) {
      retries += 1;
      status.textContent = retries < 3 ? 'Loading paused. Retrying…' : 'More photographs could not be loaded.';
      if (retries < 3) {
        window.setTimeout(() => {
          loading = false;
          loadNextPage();
        }, 1200 * retries);
        return;
      }
    } finally {
      loading = false;
    }
  }

  const observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) loadNextPage();
  }, {rootMargin: '900px 0px 900px 0px'});

  observer.observe(pager);
})();

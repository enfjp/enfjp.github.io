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
  filters.forEach(button => button.addEventListener('click', () => {
    const category = button.dataset.sgFilter;
    filters.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    photos.forEach(photo => {photo.hidden = category !== 'all' && photo.dataset.category !== category;});
    visible = photos.filter(photo => !photo.hidden);
    grid.classList.toggle('is-filtered', category !== 'all');
  }));
  const filterBar = document.querySelector('.sg-filters');
  if (filterBar) filterBar.hidden = false;
  photos.forEach(figure => {
    const link = figure.querySelector('.sg-photo-link');
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
  });
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
})();

(() => {
  'use strict';

  const ROOT_ID = 'mailtrace-ai-floating-root';
  const POSITION_KEY = 'mailtrace_popup_position';
  const MIN_KEY = 'mailtrace_popup_minimized';

  let popup = null;
  let lastMessageState = null;
  let routeTimer = null;

  const isGmailMessageView = () => {
    if (!location.hostname.endsWith('mail.google.com')) return false;
    const path = `${location.pathname}${location.hash}`;
    if (/\/(settings|search|label|category|starred|snoozed|sent|drafts|trash|spam)(?:\/|$)/i.test(path)) return false;
    // Gmail message/conversation routes normally end with a message/conversation id.
    return /(?:^|[\/#])([a-zA-Z0-9_-]{10,})$/.test(path);
  };

  const getStored = (key, fallback) => new Promise(resolve => {
    try {
      chrome.storage.local.get({ [key]: fallback }, result => resolve(result[key]));
    } catch (_) { resolve(fallback); }
  });

  const setStored = (key, value) => {
    try { chrome.storage.local.set({ [key]: value }); } catch (_) {}
  };

  function removePopup() {
    if (popup) popup.remove();
    popup = null;
  }

  async function createPopup() {
    if (popup || !isGmailMessageView()) return;

    const root = document.createElement('div');
    root.id = ROOT_ID;
    root.innerHTML = `
      <section class="mt-card" role="dialog" aria-label="MailTrace AI email security">
        <header class="mt-header">
          <div class="mt-brand">
            <div class="mt-shield" aria-hidden="true">✓</div>
            <div class="mt-title-wrap">
              <div class="mt-title">MailTrace AI</div>
              <div class="mt-subtitle">Email Security</div>
            </div>
          </div>
          <div class="mt-actions">
            <button class="mt-btn mt-min" type="button" aria-label="Minimize" title="Minimize">−</button>
            <button class="mt-btn mt-close" type="button" aria-label="Close" title="Close">×</button>
          </div>
        </header>
        <div class="mt-body">
          <div class="mt-ready">
            <div class="mt-ready-icon">🛡️</div>
            <div>
              <div class="mt-ready-title">MailTrace is ready</div>
              <div class="mt-ready-text">Security analysis for this email will appear here.</div>
            </div>
          </div>
          <div class="mt-grid">
            <div class="mt-stat"><span>Risk</span><strong>—</strong></div>
            <div class="mt-stat"><span>Status</span><strong class="mt-status">Ready</strong></div>
          </div>
          <div class="mt-placeholder">Analysis content will be connected next.</div>
        </div>
      </section>
      <button class="mt-mini" type="button" aria-label="Restore MailTrace AI" title="Restore MailTrace AI">
        <span class="mt-mini-shield">✓</span><span>MailTrace AI</span><span class="mt-mini-plus">+</span>
      </button>
    `;

    document.documentElement.appendChild(root);
    popup = root;

    const card = root.querySelector('.mt-card');
    const header = root.querySelector('.mt-header');
    const minButton = root.querySelector('.mt-min');
    const closeButton = root.querySelector('.mt-close');
    const miniButton = root.querySelector('.mt-mini');

    const position = await getStored(POSITION_KEY, null);
    if (position && Number.isFinite(position.x) && Number.isFinite(position.y)) {
      applyPosition(root, position.x, position.y);
    } else {
      applyPosition(root, Math.max(16, window.innerWidth - 386), 92);
    }

    const minimized = await getStored(MIN_KEY, false);
    setMinimized(root, Boolean(minimized));

    minButton.addEventListener('click', () => {
      setMinimized(root, true);
      setStored(MIN_KEY, true);
    });
    miniButton.addEventListener('click', () => {
      setMinimized(root, false);
      setStored(MIN_KEY, false);
    });
    closeButton.addEventListener('click', () => removePopup());

    makeDraggable(root, card, header);
  }

  function applyPosition(root, x, y) {
    const maxX = Math.max(8, window.innerWidth - 90);
    const maxY = Math.max(8, window.innerHeight - 52);
    root.style.left = `${Math.min(Math.max(8, x), maxX)}px`;
    root.style.top = `${Math.min(Math.max(8, y), maxY)}px`;
    root.style.right = 'auto';
    root.style.bottom = 'auto';
  }

  function setMinimized(root, minimized) {
    root.classList.toggle('mt-is-minimized', minimized);
  }

  function makeDraggable(root, card, handle) {
    let dragging = false;
    let offsetX = 0;
    let offsetY = 0;

    handle.addEventListener('pointerdown', event => {
      if (event.target.closest('button')) return;
      dragging = true;
      const rect = card.getBoundingClientRect();
      offsetX = event.clientX - rect.left;
      offsetY = event.clientY - rect.top;
      handle.setPointerCapture?.(event.pointerId);
      card.classList.add('mt-dragging');
      event.preventDefault();
    });

    handle.addEventListener('pointermove', event => {
      if (!dragging) return;
      applyPosition(root, event.clientX - offsetX, event.clientY - offsetY);
    });

    const stop = event => {
      if (!dragging) return;
      dragging = false;
      card.classList.remove('mt-dragging');
      handle.releasePointerCapture?.(event.pointerId);
      const rect = card.getBoundingClientRect();
      setStored(POSITION_KEY, { x: rect.left, y: rect.top });
    };
    handle.addEventListener('pointerup', stop);
    handle.addEventListener('pointercancel', stop);
  }

  function routeChanged() {
    clearTimeout(routeTimer);
    routeTimer = setTimeout(async () => {
      const state = isGmailMessageView();
      if (state !== lastMessageState) {
        lastMessageState = state;
        removePopup();
        if (state) await createPopup();
      } else if (state && !popup) {
        await createPopup();
      }
    }, 250);
  }

  window.addEventListener('hashchange', routeChanged);
  window.addEventListener('popstate', routeChanged);
  window.addEventListener('resize', () => {
    if (!popup) return;
    const rect = popup.querySelector('.mt-card')?.getBoundingClientRect();
    if (rect) applyPosition(popup, rect.left, rect.top);
  });

  const observer = new MutationObserver(() => {
    if (routeTimer) return;
    routeChanged();
  });
  observer.observe(document.body, { childList: true, subtree: true });

  routeChanged();
})();

/* ─── SHERPA Shared Header Component ─── */
(function() {
  'use strict';

  // ─── Theme initialization ───
  (function initTheme() {
    var saved = localStorage.getItem('sherpa-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
  })();

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('sherpa-theme', next);
    updateThemeIcon();
  }

  function updateThemeIcon() {
    var btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    btn.innerHTML = isDark
      ? '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4"/></svg>'
      : '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5 5.5 5.5 0 1 0 13.5 9.5Z"/></svg>';
    btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
  }

  // ─── Tech badge colors (Percona brand) ───
  window.TECH_COLORS = {
    'MySQL':      { color: 'var(--tech-mysql)',      tint: 'rgba(230,90,21,0.10)' },
    'PostgreSQL': { color: 'var(--tech-postgres)',    tint: 'rgba(0,94,214,0.10)' },
    'MongoDB':    { color: 'var(--tech-mongo)',       tint: 'rgba(31,162,58,0.10)' },
    'Valkey':     { color: 'var(--tech-valkey)',      tint: 'rgba(168,63,239,0.10)' },
    'PMM':        { color: 'var(--tech-pmm)',         tint: 'rgba(110,63,243,0.10)' },
    'Operators':  { color: 'var(--tech-kubernetes)',   tint: 'rgba(42,166,223,0.10)' },
  };

  // Determine active page from URL
  var path = window.location.pathname;
  var activePage = (path === '/' || path === '/portal') ? 'portal'
    : path.startsWith('/signals') ? 'signals'
    : path.startsWith('/evidence') ? 'evidence'
    : path.startsWith('/admin') ? 'admin' : '';

  // Nav items
  var navItems = [
    { id: 'portal',   label: 'Portal',   href: '/',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 1.8 1.5 6.2 8 10.6l6.5-4.4L8 1.8Z"/><path d="M1.5 11l6.5 4.4 6.5-4.4"/></svg>' },
    { id: 'signals',  label: 'Signals',  href: '/signals',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v3M8 11v3M2 8h3M11 8h3M3.8 3.8l2.1 2.1M10.1 10.1l2.1 2.1M3.8 12.2l2.1-2.1M10.1 5.9l2.1-2.1"/></svg>' },
    { id: 'evidence', label: 'Evidence', href: '/evidence',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2h6l4 4v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z"/><path d="M9 2v4h4"/><path d="M5 9h6M5 12h4"/></svg>' },
  ];

  // Build nav pills
  var navHTML = navItems.map(function(n) {
    var isActive = activePage === n.id;
    return '<a href="' + n.href + '" class="nav-btn" data-active="' + isActive + '">' +
      n.icon + ' <span>' + n.label + '</span></a>';
  }).join('');

  // Percona logomark SVG
  var perconaLogo = '<svg width="30" height="30" viewBox="0 0 300 300" fill="var(--brand-purple)" aria-label="Percona">' +
    '<path d="M108.9,139.5l63.5,110.1h-127L108.9,139.5z M178.8,82.2c10.3-4.9,21.8-6,33-3c12.3,3.3,22.6,11.2,29,22.3 c12.6,21.8,6,49.4-14.4,63.3L178.8,82.2z M119.3,121.4l30.6-53l0,0l104.5,181.2h-61.2L119.3,121.4z M108.9,103.4L14.2,267.6h271.5 l-50.3-87.2c29-18.9,38.4-57.6,20.9-88c-8.8-15.2-23-26.1-40-30.7c-15.7-4.2-32.2-2.5-46.6,4.8l-19.8-34.2L108.9,103.4z"/>' +
    '</svg>';

  // Build header HTML
  var headerHTML =
    '<header class="app-header" id="sherpa-header">' +
      '<div class="app-header__brand">' +
        '<a href="/" class="app-header__logo">' + perconaLogo + '</a>' +
        '<div class="app-header__title">' +
          '<span>SHERPA</span>' +
          '<span class="app-header__subtitle">Demand Intelligence &middot; Percona</span>' +
        '</div>' +
        '<span class="beta-pill">Beta</span>' +
      '</div>' +
      '<nav class="app-header__nav">' + navHTML + '</nav>' +
      '<div class="app-header__spacer"></div>' +
      '<div class="app-header__cluster">' +
        '<button class="icon-btn" id="themeToggleBtn" onclick="window.__toggleTheme()" title="Toggle theme"></button>' +
        '<div class="auth-area" id="authArea">' +
          '<button class="btn btn--primary btn--sm" onclick="openAuthModal()">Sign in to vote</button>' +
        '</div>' +
      '</div>' +
    '</header>' +
    '<div class="modal-backdrop" id="authModal" style="display:none">' +
      '<div class="modal" style="max-width:480px; position:relative">' +
        '<button class="modal__close" onclick="closeAuthModal()">' +
          '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m4 4 8 8M12 4l-8 8"/></svg>' +
        '</button>' +
        '<div class="modal__head">' +
          '<h2 class="t-h2">Sign in to vote</h2>' +
          '<p class="t-body">Use your Percona email to vote and comment on features.</p>' +
        '</div>' +
        '<div class="modal__body">' +
          '<div class="form-group">' +
            '<label class="t-eyebrow" style="margin-bottom:6px; display:block">Your name</label>' +
            '<div class="input"><input type="text" id="authName" placeholder="Jane Smith" onkeydown="if(event.key===\'Enter\')document.getElementById(\'authEmail\').focus()"></div>' +
          '</div>' +
          '<div class="form-group">' +
            '<label class="t-eyebrow" style="margin-bottom:6px; display:block">Percona email</label>' +
            '<div class="input"><input type="email" id="authEmail" placeholder="you@percona.com" onkeydown="if(event.key===\'Enter\')doLogin()"></div>' +
          '</div>' +
          '<button class="btn btn--primary" onclick="doLogin()" id="loginBtn" style="width:100%">Sign in</button>' +
          '<div id="authError" class="form-error" style="display:none; color:var(--red); font-size:13px; margin-top:8px"></div>' +
        '</div>' +
      '</div>' +
    '</div>';

  // Insert header at top of body
  document.body.insertAdjacentHTML('afterbegin', headerHTML);

  // Insert footer at bottom of body
  var footerHTML =
    '<footer class="app-footer">' +
      '<div class="app-footer__inner">' +
        '<svg width="14" height="14" viewBox="0 0 300 300" fill="var(--text-muted)" style="vertical-align:-2px; margin-right:4px">' +
          '<path d="M108.9,139.5l63.5,110.1h-127L108.9,139.5z M178.8,82.2c10.3-4.9,21.8-6,33-3c12.3,3.3,22.6,11.2,29,22.3 c12.6,21.8,6,49.4-14.4,63.3L178.8,82.2z M119.3,121.4l30.6-53l0,0l104.5,181.2h-61.2L119.3,121.4z M108.9,103.4L14.2,267.6h271.5 l-50.3-87.2c29-18.9,38.4-57.6,20.9-88c-8.8-15.2-23-26.1-40-30.7c-15.7-4.2-32.2-2.5-46.6,4.8l-19.8-34.2L108.9,103.4z"/>' +
        '</svg>' +
        '<b>SHERPA</b>' +
        ' &mdash; Stakeholder Hub for Enhancement Request Prioritization &amp; Action' +
        ' &nbsp;&bull;&nbsp; Internal &middot; Percona' +
        ' &nbsp;&bull;&nbsp; v0.4 beta' +
      '</div>' +
    '</footer>';
  document.body.insertAdjacentHTML('beforeend', footerHTML);

  // Set up theme toggle icon
  window.__toggleTheme = toggleTheme;
  updateThemeIcon();

  // Close modal on backdrop click
  document.getElementById('authModal').addEventListener('click', function(e) {
    if (e.target === this) this.style.display = 'none';
  });

  // ─── Auth State ───
  window.currentUser = null;

  window.esc = function(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  };

  window.loadSession = function() {
    var saved = localStorage.getItem('percona_voter');
    if (saved) {
      try { window.currentUser = JSON.parse(saved); } catch(e) { /* ignore */ }
      updateAuthUI();
    }
  };

  window.updateAuthUI = function() {
    var area = document.getElementById('authArea');
    if (!area) return;
    if (window.currentUser) {
      var name = window.currentUser.display_name || window.currentUser.email;
      var initials = name.split(/\s+/).map(function(w) { return w[0]; }).join('').substring(0, 2).toUpperCase();
      area.innerHTML =
        '<div class="user-pill">' +
          '<span class="user-pill__avatar">' + esc(initials) + '</span>' +
          '<span>' + esc(name) + '</span>' +
        '</div>';
    } else {
      // SSO handles login automatically via Remote-User header
      area.innerHTML = '';
    }
  };

  window.signOut = function() {
    window.currentUser = null;
    localStorage.removeItem('percona_voter');
    updateAuthUI();
    if (typeof window.onAuthChange === 'function') window.onAuthChange();
  };

  window.openAuthModal = function() {
    document.getElementById('authError').style.display = 'none';
    document.getElementById('authModal').style.display = '';
    setTimeout(function() { document.getElementById('authName').focus(); }, 100);
  };

  window.closeAuthModal = function() {
    document.getElementById('authModal').style.display = 'none';
  };

  window.doLogin = async function() {
    var nameEl = document.getElementById('authName');
    var emailEl = document.getElementById('authEmail');
    var btn = document.getElementById('loginBtn');
    var err = document.getElementById('authError');
    var name = nameEl.value.trim();
    var email = emailEl.value.trim();

    if (!name || !email) {
      err.textContent = 'Name and email are required';
      err.style.display = '';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Signing in…';
    err.style.display = 'none';

    try {
      var resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, display_name: name })
      });
      var data = await resp.json();

      btn.disabled = false;
      btn.textContent = 'Sign in';

      if (data.error) {
        err.textContent = data.error;
        err.style.display = '';
        return;
      }

      window.currentUser = {
        voter_id: data.voter_id,
        email: data.email,
        display_name: data.display_name
      };
      localStorage.setItem('percona_voter', JSON.stringify(window.currentUser));
      updateAuthUI();
      closeAuthModal();
      if (typeof window.onAuthChange === 'function') window.onAuthChange();
    } catch(e) {
      btn.disabled = false;
      btn.textContent = 'Sign in';
      err.textContent = 'Network error. Please try again.';
      err.style.display = '';
    }
  };

  // Try SSO auto-login, then fall back to localStorage session
  window.trySSO = async function() {
    try {
      var resp = await fetch('/api/auth/sso');
      var data = await resp.json();
      if (data.authenticated && data.voter_id) {
        window.currentUser = {
          voter_id: data.voter_id,
          email: data.email,
          display_name: data.display_name
        };
        localStorage.setItem('percona_voter', JSON.stringify(window.currentUser));
        updateAuthUI();
        if (typeof window.onAuthChange === 'function') window.onAuthChange();
        return;
      }
    } catch(e) { /* SSO not available, fall through */ }
    // Fall back to localStorage session
    loadSession();
  };

  trySSO();
})();

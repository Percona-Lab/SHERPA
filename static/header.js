/* ─── SHERPA Shared Header Component ─── */
(function() {
  'use strict';

  // Determine active page from URL
  var path = window.location.pathname;
  var activePage = (path === '/' || path === '/portal') ? 'portal'
    : path.startsWith('/signals') ? 'signals'
    : path.startsWith('/evidence') ? 'evidence' : '';

  // Build header HTML
  var headerHTML =
    '<header class="header" id="sherpa-header">' +
      '<div class="header-inner">' +
        '<a href="/" class="logo-area">' +
          '<img src="/static/logo-small.png" alt="SHERPA" class="logo-img">' +
          '<div class="logo-text">SHERPA <span>Demand Intelligence</span></div>' +
        '</a>' +
        '<div class="prototype-badge">BETA</div>' +
        '<nav style="margin-left:auto">' +
          '<a href="/"' + (activePage === 'portal' ? ' class="active"' : '') + '>Portal</a>' +
          '<a href="/signals"' + (activePage === 'signals' ? ' class="active"' : '') + '>Signals</a>' +
          '<a href="/evidence"' + (activePage === 'evidence' ? ' class="active"' : '') + '>Evidence</a>' +
        '</nav>' +
        '<div class="auth-area" id="authArea">' +
          '<button class="sign-in-btn" onclick="openAuthModal()">Sign in to vote</button>' +
        '</div>' +
      '</div>' +
    '</header>' +
    '<div class="modal-overlay" id="authModal">' +
      '<div class="modal">' +
        '<button class="modal-close" onclick="closeAuthModal()">&times;</button>' +
        '<h2>Sign in to vote</h2>' +
        '<p class="subtitle">Use your Percona email to vote and comment on features.</p>' +
        '<div class="form-group">' +
          '<label>Your name</label>' +
          '<input class="form-input" type="text" id="authName" placeholder="Jane Smith" onkeydown="if(event.key===\'Enter\')document.getElementById(\'authEmail\').focus()">' +
        '</div>' +
        '<div class="form-group">' +
          '<label>Percona email</label>' +
          '<input class="form-input" type="email" id="authEmail" placeholder="you@percona.com" onkeydown="if(event.key===\'Enter\')doLogin()">' +
        '</div>' +
        '<button class="btn-primary" onclick="doLogin()" id="loginBtn">Sign in</button>' +
        '<div id="authError" class="form-error" style="display:none"></div>' +
      '</div>' +
    '</div>';

  // Insert header at top of body
  document.body.insertAdjacentHTML('afterbegin', headerHTML);

  // Close modal on overlay click
  document.getElementById('authModal').addEventListener('click', function(e) {
    if (e.target === this) this.classList.remove('open');
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
      area.innerHTML =
        '<div class="user-pill"><div class="dot"></div>' + esc(name) + '</div>' +
        '<button class="sign-out-btn" onclick="signOut()">Sign out</button>';
    } else {
      area.innerHTML = '<button class="sign-in-btn" onclick="openAuthModal()">Sign in to vote</button>';
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
    document.getElementById('authModal').classList.add('open');
    setTimeout(function() { document.getElementById('authName').focus(); }, 100);
  };

  window.closeAuthModal = function() {
    document.getElementById('authModal').classList.remove('open');
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
    btn.textContent = 'Signing in\u2026';
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

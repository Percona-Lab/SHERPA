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
    'MySQL': { color: 'var(--tech-mysql)', tint: 'rgba(230,90,21,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%23ea6525%3B%20stroke%3A%20%23ea6525%3B%20stroke-width%3A%2030%3B%20%7D%20%3C/style%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1082.02%2C1010.89H41.49L561.75%2C109.77l520.26%2C901.12ZM69.93%2C994.47h983.65L561.75%2C142.61%2C69.93%2C994.47Z%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22355.31%20798.52%20446.37%20798.52%20401.31%20719.55%20355.31%20798.52%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22287.72%20808.89%20271.19%20834.94%20271.19%20899.17%20332.21%20836.75%20364.12%20864.61%20404.64%20863.85%20357.54%20808.89%20287.72%20808.89%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M668.31%2C608.9h-103.63l-115.28-47.15%2C29.15%2C51.04-112.11%2C61.96-64.71%2C111.7h34.92l64.98-111.54%2C63.62%2C111.51h66.14l-20%2C34.32%2C43.46%2C76.17%2C100.45-173.04-28.41-49.66%2C82.27.19%2C28.45%2C49.82h-56.27l-78.13%2C133.72%2C23.45%2C40%2C64.76-110.43%2C13.62-.48c36.63%2C0%2C126.32-8.48%2C126.32-45.12%2C0-65.16-97.9-133.01-163.07-133.01ZM764.38%2C754.63c0%2C5.13-4.19%2C9.32-9.32%2C9.32h-8.67c-5.13%2C0-9.32-4.2-9.32-9.32v-8.67c0-5.13%2C4.19-9.32%2C9.32-9.32h8.67c5.13%2C0%2C9.32%2C4.19%2C9.32%2C9.32v8.67Z%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
    'PostgreSQL': { color: 'var(--tech-postgres)', tint: 'rgba(0,94,214,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20xmlns%3Axlink%3D%22http%3A//www.w3.org/1999/xlink%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%23005ed6%3B%20stroke%3A%20%23005ed6%3B%20stroke-width%3A%2030%3B%20%7D%20.cls-2%20%7B%20clip-path%3A%20url%28%23clippath%29%3B%20%7D%20%3C/style%3E%20%3CclipPath%20id%3D%22clippath%22%3E%20%3Cpolyline%20class%3D%22cls-1%22%20points%3D%22305.31%20827.37%20328.46%20787.35%20378.35%20787.35%20442.63%20898.29%20498.94%20898.29%20433.67%20787.35%20548.29%20787.45%20573.7%20743.44%20516.78%20645.54%20473.31%20569.38%20374.65%20570.25%20305.94%20688.19%20305.88%20704.68%20279.05%20752.33%20279.05%20799.28%20306.72%20752.18%22/%3E%20%3C/clipPath%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1082.02%2C1010.89H41.49L561.75%2C109.77l520.26%2C901.12ZM69.93%2C994.47h983.65L561.75%2C142.61%2C69.93%2C994.47Z%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22681.51%20899.1%20625.22%20899.1%20567.09%20798.9%20609.3%20726.62%20620.68%20791.4%20681.51%20899.1%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M718.7%2C562.3h-14.61l-6.06%2C10.37-45.26%2C78.39-33.43%2C57.9-3.84%2C6.66h107.44l32.67%2C32.67v59.03h-52.4c-5.34%2C0-9.67%2C4.33-9.67%2C9.67v39.11h62.55c26.37%2C0%2C47.78-21.13%2C48.27-47.38h.02v-160.72c0-47.33-38.37-85.7-85.7-85.7ZM740.29%2C646.03c0%2C5.32-4.35%2C9.67-9.67%2C9.67h-8.99c-5.32%2C0-9.67-4.35-9.67-9.67v-8.99c0-5.32%2C4.35-9.67%2C9.67-9.67h8.99c5.32%2C0%2C9.67%2C4.35%2C9.67%2C9.67v8.99Z%22/%3E%20%3Cg%3E%20%3Cpolyline%20class%3D%22cls-1%22%20points%3D%22305.31%20827.37%20328.46%20787.35%20378.35%20787.35%20442.63%20898.29%20498.94%20898.29%20433.67%20787.35%20548.29%20787.45%20573.7%20743.44%20516.78%20645.54%20473.31%20569.38%20374.65%20570.25%20305.94%20688.19%20305.88%20704.68%20279.05%20752.33%20279.05%20799.28%20306.72%20752.18%22/%3E%20%3Cg%20class%3D%22cls-2%22%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22276.72%20828.89%20276.34%20828.67%20276.34%20829.2%20276.72%20828.89%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22586.76%20720.72%20689.75%20542.35%20483.78%20542.35%20586.76%20720.72%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M557.54%2C809.88h-30.45v79.55c0%2C5.34%2C4.33%2C9.67%2C9.67%2C9.67h46.53l-.23-44.84-25.52-44.38Z%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M362.46%2C867.89l23.21-40.05-10.35-17.95h-43.93l-22.88%2C39.62v39.32c0%2C5.34%2C4.33%2C9.67%2C9.67%2C9.67h61.73l-17.45-30.6Z%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
    'MongoDB': { color: 'var(--tech-mongo)', tint: 'rgba(31,162,58,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%23239948%3B%20stroke%3A%20%23239948%3B%20stroke-width%3A%2030%3B%20%7D%20%3C/style%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1082.02%2C1010.89H41.49L561.75%2C109.77l520.26%2C901.12ZM69.93%2C994.47h983.65L561.75%2C142.61%2C69.93%2C994.47Z%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22513.47%20707.59%20561.75%20791.22%20610.04%20707.59%20513.47%20707.59%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22501.47%20689.8%20538.47%20689.8%20465.86%20564.04%20316.59%20822.07%20353.59%20822.07%20465.86%20628.12%20501.47%20689.8%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22641.18%20545.29%20562.77%20409.33%20484.16%20544.96%20562.58%20680.92%20641.18%20545.29%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22514.56%20896.3%20498.23%20924.58%20552.88%20924.58%20552.88%20813.64%20468.86%20668.12%20379.94%20822.14%20529.5%20822.14%20529.5%20896.3%20514.56%20896.3%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22744.56%20822.14%20655.64%20668.12%20572.47%20812.18%20572.47%20924.58%20626.28%20924.58%20609.95%20896.3%20595%20896.3%20595%20822.14%20744.56%20822.14%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22657.64%20564.04%20585.04%20689.8%20622.03%20689.8%20657.64%20628.12%20769.92%20822.07%20806.91%20822.07%20657.64%20564.04%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
    'Valkey': { color: 'var(--tech-valkey)', tint: 'rgba(168,63,239,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%23a83fef%3B%20stroke%3A%20%23a83fef%3B%20stroke-width%3A%2030%3B%20%7D%20%3C/style%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1080.68%2C1011.16H42.83L561.75%2C112.35l518.93%2C898.8ZM71.19%2C994.78h981.12L561.75%2C145.1%2C71.19%2C994.78Z%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22517.94%20702.96%20562.06%20779.37%20606.17%20702.96%20517.94%20702.96%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M561.75%2C639.99c-49.97%2C0-90.63%2C40.66-90.63%2C90.63s40.66%2C90.63%2C90.63%2C90.63%2C90.63-40.66%2C90.63-90.63-40.66-90.63-90.63-90.63ZM561.75%2C793.62c-34.74%2C0-63-28.26-63-63s28.26-63%2C63-63%2C63%2C28.26%2C63%2C63-28.26%2C63-63%2C63Z%22/%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M385.89%2C898.8l10.66-18.38h112.31l10.66%2C18.38h301.34l-259.1-448.78-259.1%2C448.78h83.24ZM497.79%2C619.82h127.93l63.97%2C110.79-63.97%2C110.79h-127.93l-63.97-110.79%2C63.97-110.79Z%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
    'PMM': { color: 'var(--tech-pmm)', tint: 'rgba(110,63,243,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%23653df4%3B%20stroke%3A%20%23653df4%3B%20stroke-width%3A%2030%3B%20%7D%20%3C/style%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1080.68%2C1011.16H42.83L561.75%2C112.35l518.93%2C898.8ZM71.19%2C994.78h981.12L561.75%2C145.1%2C71.19%2C994.78Z%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22529.44%20662.42%20529.44%20662.42%20773.07%20662.42%20651.25%20451.44%20529.44%20662.42%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22435.89%20555.32%20419.17%20526.36%20340.61%20662.42%20374.06%20662.42%20435.89%20555.32%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22587.99%20516.98%20535.5%20426.08%20399.05%20662.42%20504.03%20662.42%20587.99%20516.98%22/%3E%20%3Cg%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22529.44%20683.48%20529.44%20683.48%20773.07%20683.48%20651.25%20894.45%20529.44%20683.48%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22435.89%20790.57%20419.17%20819.53%20340.61%20683.48%20374.06%20683.48%20435.89%20790.57%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22587.99%20828.91%20535.5%20919.81%20399.05%20683.48%20504.03%20683.48%20587.99%20828.91%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
    'Operators': { color: 'var(--tech-kubernetes)', tint: 'rgba(42,166,223,0.10)', icon: 'data:image/svg+xml,%3Csvg%20id%3D%22Layer_12%22%20data-name%3D%22Layer%2012%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%201123.51%201123.51%22%3E%20%3Cdefs%3E%20%3Cstyle%3E%20.cls-1%20%7B%20fill%3A%20%232aa6df%3B%20stroke%3A%20%232aa6df%3B%20stroke-width%3A%2030%3B%20%7D%20%3C/style%3E%20%3C/defs%3E%20%3Cg%20id%3D%22Background%22%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M1079.79%2C1010.89H43.71L561.75%2C113.62l518.04%2C897.27ZM72.03%2C994.54h979.44L561.75%2C146.32%2C72.03%2C994.54Z%22/%3E%20%3Cg%3E%20%3Cpath%20class%3D%22cls-1%22%20d%3D%22M285.46%2C815.31l31.02%2C82.63h452.56l68.58-82.63H285.46Z%22/%3E%20%3Cpolyline%20class%3D%22cls-1%22%20points%3D%22338.58%20786.24%20485.24%20528.52%20504.78%20562.26%20376.93%20786.24%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22607.11%20706.43%20653.19%20786.24%20801.39%20786.24%20607.11%20449.74%20412.83%20786.24%20561.03%20786.24%20607.11%20706.43%22/%3E%20%3Cpolygon%20class%3D%22cls-1%22%20points%3D%22471.65%20449.74%20521.09%20535.38%20570.54%20449.74%20471.65%20449.74%22/%3E%20%3C/g%3E%20%3C/g%3E%20%3C/g%3E%20%3C/svg%3E' },
  };

  // Global tech badge helper with product logo
  window.techBadgeHTML = function(tech) {
    var tc = TECH_COLORS[tech] || { color: 'var(--brand-purple)', tint: 'rgba(110,63,243,0.10)' };
    var iconHTML = tc.icon
      ? '<img src="' + tc.icon + '" width="14" height="14" style="display:block;flex-shrink:0">'
      : '';
    return '<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600;font-family:var(--font-mono);background:' + tc.tint + ';color:' + tc.color + ';white-space:nowrap;line-height:1">' +
      iconHTML + tech + '</span>';
  };

  // Determine active page from URL
  var path = window.location.pathname;
  var activePage = (path === '/' || path === '/portal') ? 'portal'
    : path.startsWith('/signals') ? 'signals'
    : path.startsWith('/evidence') ? 'evidence'
    : path.startsWith('/cut-keep') ? 'cut-keep'
    : path.startsWith('/admin') ? 'admin' : '';

  // Nav items
  var navItems = [
    { id: 'portal',   label: 'Portal',   href: '/',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 1.8 1.5 6.2 8 10.6l6.5-4.4L8 1.8Z"/><path d="M1.5 11l6.5 4.4 6.5-4.4"/></svg>' },
    { id: 'signals',  label: 'Signals',  href: '/signals',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v3M8 11v3M2 8h3M11 8h3M3.8 3.8l2.1 2.1M10.1 10.1l2.1 2.1M3.8 12.2l2.1-2.1M10.1 5.9l2.1-2.1"/></svg>' },
    { id: 'evidence', label: 'Evidence', href: '/evidence',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2h6l4 4v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z"/><path d="M9 2v4h4"/><path d="M5 9h6M5 12h4"/></svg>' },
    { id: 'cut-keep', label: 'Cut/Keep', href: '/cut-keep',
      icon: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3H3v4h3V3ZM13 3h-3v4h3V3ZM6 9H3v4h3V9Z"/><path d="M10 11h3M10 13h3"/></svg>' },
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
        ' &nbsp;&bull;&nbsp; v0.8 beta' +
      '</div>' +
    '</footer>';
  // Defer footer injection until DOM is fully parsed so it appears after all page content
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      document.body.insertAdjacentHTML('beforeend', footerHTML);
    });
  } else {
    document.body.insertAdjacentHTML('beforeend', footerHTML);
  }

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
      var email = window.currentUser.email || '';
      area.innerHTML =
        '<div class="user-pill" onclick="document.getElementById(\'userPopover\').classList.toggle(\'open\')" style="cursor:pointer; position:relative">' +
          '<span class="user-pill__avatar">' + esc(initials) + '</span>' +
          '<span>' + esc(name) + '</span>' +
          '<div class="user-popover" id="userPopover">' +
            '<div style="font-weight:600; font-size:14px; margin-bottom:4px">' + esc(name) + '</div>' +
            '<div style="font-size:12px; color:var(--text-muted)">' + esc(email) + '</div>' +
          '</div>' +
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

/* Foundation Studio - page interactions (presentation only; no calculation happens here).
 *
 *  - Result tiles and contents links: switch to the source tab, glide to the section, pulse its card
 *  - Section badges (P3·a ...): copy a deep link (#sec-...) and show a toast; links open on load
 *  - Metrics with a "why" note: click / Enter opens a glass dialog (formula, numbers, source)
 *  - Footing tile: opens the sidebar and highlights the footing & load inputs
 *  - "Back to results" floating button once the result tiles scroll out of view
 *  - "On this tab" contents list in the sidebar with scroll-spy
 *  - Keyboard: 1-7 switch tabs, / footing inputs, ? shortcuts, Esc closes the dialog
 *
 * Installed once per page load and re-applied to new DOM after every Streamlit rerun.
 */
(function () {
  var VER = 3;
  if (window.__fsUiVer === VER) return;
  window.__fsUiVer = VER;

  var doc = document;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DOCK = 120;               // clearance for the sticky tab dock, px
  function $(s, r) { return (r || doc).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || doc).querySelectorAll(s)); }
  function mainEl() { return $('[data-testid="stMain"]') || doc.scrollingElement; }
  function tabEls() { return $$('.stTabs [data-testid="stTab"]'); }
  function panelEls() { return $$('.stTabs [data-testid="stTabPanel"]'); }
  function visible(el) { return el && el.offsetParent !== null; }

  // ------------------------------------------------------------------ helpers
  function glideTo(el, offset) {
    var m = mainEl();
    var top = el.getBoundingClientRect().top - m.getBoundingClientRect().top + m.scrollTop - (offset || 0);
    m.scrollTo({ top: Math.max(0, top), behavior: reduce ? 'auto' : 'smooth' });
  }
  function flash(el, cls) {
    cls = cls || 'fs-flash';
    clearTimeout(el['__t' + cls]);
    el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls);
    el['__t' + cls] = setTimeout(function () { el.classList.remove(cls); }, 2400);
  }
  function selectTab(i) {
    var t = tabEls()[i];
    if (t && t.getAttribute('aria-selected') !== 'true') t.click();
    return t;
  }
  function toast(msg) {
    var t = $('.fs-toast');
    if (!t) {
      t = doc.createElement('div');
      t.className = 'fs-toast';
      t.setAttribute('role', 'status');
      t.setAttribute('aria-live', 'polite');
      doc.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.remove('show'); void t.offsetWidth; t.classList.add('show');
    clearTimeout(t.__h);
    t.__h = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (ok, fail) {
      var ta = doc.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      doc.body.appendChild(ta); ta.select();
      try { doc.execCommand('copy') ? ok() : fail(); } catch (e) { fail(e); }
      doc.body.removeChild(ta);
    });
  }

  // ------------------------------------------------- reveal a section anywhere
  function reveal(anchor, maxWaitMs) {
    var t0 = performance.now();
    (function wait() {
      var sec = $('[data-fs-section="' + anchor + '"]');
      if (sec) {
        var panel = sec.closest('[data-testid="stTabPanel"]');
        var idx = panel ? panelEls().indexOf(panel) : -1;
        if (idx >= 0) selectTab(idx);
        if (visible(sec)) {
          glideTo(sec, DOCK);
          flash(sec.closest('[class*="st-key-glass"]') || sec);
          return;
        }
      }
      if (performance.now() - t0 < (maxWaitMs || 1500)) requestAnimationFrame(wait);
    })();
  }

  // ------------------------------------------------------------- the dialog
  var lastFocus = null;
  function modal() {
    var m = $('.fs-modal');
    if (m) return m;
    m = doc.createElement('div');
    m.className = 'fs-modal';
    m.hidden = true;
    m.innerHTML =
      '<div class="fs-scrim" data-fs-close></div>' +
      '<div class="fs-dialog" role="dialog" aria-modal="true" aria-labelledby="fs-dlg-title">' +
      '<button type="button" class="fs-x" data-fs-close aria-label="Close">' +
      '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button>' +
      '<div class="fs-dlg-body"></div></div>';
    doc.body.appendChild(m);
    return m;
  }
  function openWhy(holder) {
    var why = $('.fs-why', holder);
    if (!why) return;
    var m = modal();
    var body = $('.fs-dlg-body', m);
    body.innerHTML = why.innerHTML;
    var h = $('.fs-why-h', body);
    if (h) h.id = 'fs-dlg-title';
    lastFocus = doc.activeElement;
    m.hidden = false;
    requestAnimationFrame(function () { m.classList.add('open'); $('.fs-x', m).focus(); });
  }
  function closeWhy() {
    var m = $('.fs-modal');
    if (!m || m.hidden) return;
    m.classList.remove('open');
    setTimeout(function () { m.hidden = true; }, reduce ? 0 : 220);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  // ------------------------------------------------------ sidebar & inputs
  function openSidebar() {
    var sb = $('section[data-testid="stSidebar"]');
    var collapsed = sb && (sb.getAttribute('aria-expanded') === 'false' || sb.offsetWidth < 40);
    if (collapsed) {
      var btn = $('[data-testid="stExpandSidebarButton"]') || $('[data-testid="stSidebarCollapsedControl"] button');
      if (btn) btn.click();
    }
  }
  function highlightInputs(keys) {
    openSidebar();
    setTimeout(function () {
      var first = null;
      keys.forEach(function (k) {
        var el = $('.st-key-' + k);
        if (!el) return;
        if (!first) first = el;
        flash(el, 'fs-hl');
      });
      if (first) {
        var sc = $('[data-testid="stSidebarContent"]');
        if (sc) {
          var top = first.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop - 90;
          sc.scrollTo({ top: Math.max(0, top), behavior: reduce ? 'auto' : 'smooth' });
        }
        var inp = $('input', first);
        if (inp) inp.focus({ preventScroll: true });
      }
    }, 260);
  }

  // --------------------------------------------------------------- clicks
  doc.addEventListener('click', function (e) {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var t = e.target;
    if (!t.closest) return;

    if (t.closest('[data-fs-close]')) { e.preventDefault(); closeWhy(); return; }

    var a = t.closest('a[data-fs-inputs]');                       // footing tile
    if (a) { e.preventDefault(); highlightInputs(a.getAttribute('data-fs-inputs').split(',')); return; }

    a = t.closest('a[data-fs-anchor]');                           // result tiles, contents links
    if (a) { e.preventDefault(); reveal(a.getAttribute('data-fs-anchor')); return; }

    a = t.closest('a[data-fs-copy]');                             // section badges
    if (a) {
      e.preventDefault();
      var anchor = a.getAttribute('data-fs-copy');
      var url = location.href.split('#')[0] + '#sec-' + anchor;
      history.replaceState(null, '', '#sec-' + anchor);
      var title = (a.getAttribute('data-fs-title') || anchor);
      copyText(url).then(function () { toast('Link to “' + title + '” copied'); },
                         function () { toast('Copy failed — the link is now in the address bar'); });
      flash(a.closest('[class*="st-key-glass"]') || a);
      return;
    }

    if (t.closest('.fs-back')) {                                   // back to results
      e.preventDefault();
      var tiles = $('.tiles');
      if (tiles) { glideTo(tiles, 24); flash(tiles, 'fs-flash-soft'); }
      return;
    }

    var mx = t.closest('[class*="st-key-mx_"]');                   // metric with a "why" note
    if (mx && $('.fs-why', mx) && t.closest('[data-testid="stMetric"]')) { e.preventDefault(); openWhy(mx); }
  });

  // ------------------------------------------------------------- keyboard
  doc.addEventListener('keydown', function (e) {
    var m = $('.fs-modal');
    if (e.key === 'Escape' && m && !m.hidden) { e.preventDefault(); closeWhy(); return; }
    if (m && !m.hidden && e.key === 'Tab') {                         // keep focus inside the dialog
      var f = $$('button, a[href], [tabindex]:not([tabindex="-1"])', m);
      if (f.length) {
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
      }
      return;
    }
    var t = e.target;
    if ((e.key === 'Enter' || e.key === ' ') && t.closest && t.closest('[data-testid="stMetric"]')) {
      var mx = t.closest('[class*="st-key-mx_"]');
      if (mx && $('.fs-why', mx)) { e.preventDefault(); openWhy(mx); }
      return;
    }
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return;
    if (t.closest && t.closest('input, textarea, select, [contenteditable], [role="grid"], [role="listbox"], ' +
                                '[data-testid="stDataEditor"], [data-testid="stDataFrame"]')) return;
    if (/^[1-9]$/.test(e.key)) {
      var i = +e.key - 1;
      var tab = tabEls()[i];
      if (!tab) return;
      e.preventDefault();
      selectTab(i);
      tab.focus({ preventScroll: true });
      var dock = $('.stTabs [role="tablist"]');
      if (dock && mainEl().scrollTop > dock.offsetTop) glideTo(dock.closest('.stTabs'), 16);
    } else if (e.key === '/') {
      e.preventDefault();
      highlightInputs(['in_shape', 'in_B', 'in_L', 'in_Df']);
    } else if (e.key === '?') {
      e.preventDefault();
      toast('1–7 switch tabs · / footing inputs · click a metric for its formula · Esc closes');
    }
  });

  // -------------------------------------------- per-rerun decoration pass
  function decorate() {
    // metrics with a "why" note become buttons for assistive tech & keyboard
    $$('[class*="st-key-mx_"]').forEach(function (mx) {
      var met = $('[data-testid="stMetric"]', mx);
      if (!met || !$('.fs-why', mx) || met.getAttribute('role') === 'button') return;
      met.setAttribute('role', 'button');
      met.setAttribute('tabindex', '0');
      met.setAttribute('aria-haspopup', 'dialog');
      var lbl = met.innerText.split('\n')[0];
      met.setAttribute('aria-label', lbl + ': show formula, numbers and source');
      met.classList.add('fs-why-able');
    });
    // floating "back to results" button
    if (!$('.fs-back')) {
      var b = doc.createElement('button');
      b.type = 'button';
      b.className = 'fs-back';
      b.innerHTML = '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>' +
        '<span>Back to results</span>';
      doc.body.appendChild(b);
    }
    buildToc();
    spy();
  }

  // ------------------------------------------- contents list ("On this tab")
  var tocSig = '';
  function buildToc() {
    var nav = $('.fs-toc');
    if (!nav) return;
    var panel = panelEls().filter(visible)[0];
    var secs = panel ? $$('[data-fs-section]', panel) : [];
    var sig = secs.map(function (s) { return s.getAttribute('data-fs-section'); }).join('|');
    if (sig === tocSig && nav.children.length) return;
    tocSig = sig;
    var html = '<div class="fs-toc-h">On this tab</div>';
    secs.forEach(function (s) {
      var no = $('.no', s), h = $('h3', s);
      html += '<a href="#sec-' + s.getAttribute('data-fs-section') + '" data-fs-anchor="' +
              s.getAttribute('data-fs-section') + '"><span class="b">' + (no ? no.textContent : '') +
              '</span><span class="t">' + (h ? h.textContent : '') + '</span></a>';
    });
    nav.innerHTML = secs.length ? html : '';
  }
  function spy() {
    var nav = $('.fs-toc');
    var m = mainEl();
    var tiles = $('.tiles');
    var back = $('.fs-back');
    if (back) {
      var gone = tiles ? tiles.getBoundingClientRect().bottom < 40 : m.scrollTop > 600;
      back.classList.toggle('show', gone);
    }
    if (!nav) return;
    var links = $$('a', nav), best = null, bestTop = -Infinity;
    links.forEach(function (a) {
      var s = $('[data-fs-section="' + a.getAttribute('data-fs-anchor') + '"]');
      if (!visible(s)) return;
      var top = s.getBoundingClientRect().top;
      if (top - DOCK - 40 <= 0 && top > bestTop) { bestTop = top; best = a; }
    });
    if (!best && links.length) best = links[0];
    links.forEach(function (a) { a.classList.toggle('on', a === best); });
  }

  var pending = null;
  function schedule() {
    if (pending) return;
    pending = setTimeout(function () { pending = null; decorate(); }, 120);
  }
  new MutationObserver(schedule).observe(doc.body, { childList: true, subtree: true, attributes: true,
                                                      attributeFilter: ['aria-selected', 'hidden'] });
  var ticking = false;
  doc.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { ticking = false; spy(); });
  }, true);

  // ------------------------------------------------------- deep link on load
  // Streamlit re-mounts the tabs during its first full render, which can reset a tab chosen too
  // early, so the deep link is re-checked once the page has settled.  A link pasted into an
  // already-open tab only changes the hash, so hashchange is handled too.
  function followHash(settle) {
    if (!/^#sec-/.test(location.hash)) return;
    var target = location.hash.slice(5);
    reveal(target, 8000);
    if (!settle) return;
    [2500, 5000].forEach(function (ms) {
      setTimeout(function () {
        var sec = $('[data-fs-section="' + target + '"]');
        if (sec && !visible(sec)) reveal(target, 3000);
      }, ms);
    });
  }
  window.addEventListener('hashchange', function () { followHash(false); });
  followHash(true);
  decorate();
})();


/* SGJM blog shared include: analytics + subscribe form (every blog page).
 * Reads window.SITE_CONFIG from the site-root config.js.
 * - GoatCounter loads ONLY when SITE_CONFIG.goatcounterCode is set.
 * - Never sends names, emails, phones, addresses or form values to analytics. */
(function () {
  'use strict';
  var cfg = (typeof window !== 'undefined' && window.SITE_CONFIG) ? window.SITE_CONFIG : {};
  var COLLECT_DATA_ENABLED = cfg.COLLECT_DATA_ENABLED === true; /* default false: forms stay closed */
  var PRE_REGISTRATION_MODE = cfg.PRE_REGISTRATION_MODE !== false; /* default true: services hidden */

  function cleanCode(v) {
    v = String(v == null ? '' : v).trim();
    if (!v || /^(PASTE_|GOATCOUNTER_CODE|X+$)/i.test(v)) return '';
    return v;
  }

  /* ---- GoatCounter (cookieless page views) ---- */
  var gcCode = cleanCode(cfg.goatcounterCode);
  if (gcCode && typeof document !== 'undefined') {
    try {
      var s = document.createElement('script');
      s.setAttribute('data-goatcounter', 'https://' + gcCode + '.goatcounter.com/count');
      s.async = true;
      s.src = '//gc.zgo.at/count.js';
      document.head.appendChild(s);
    } catch (e) { /* analytics is optional - never break the page */ }
  }

  /* ---- Guarded event helper (no-op if GoatCounter blocked/absent) ---- */
  function gcEvent(path, title) {
    try {
      if (window.goatcounter && typeof window.goatcounter.count === 'function') {
        window.goatcounter.count({ path: String(path), title: String(title || path), event: true });
      }
    } catch (e3) { /* analytics is optional */ }
  }
  window.sgjmEvent = gcEvent;

  /* ---- data-gc click tracking (CTA + contact links) ---- */
  try {
    document.addEventListener('click', function (e) {
      var el = (e.target && e.target.closest) ? e.target.closest('[data-gc]') : null;
      if (!el) return;
      var name = el.getAttribute('data-gc');
      if (name) gcEvent(name, (el.textContent || name).trim().slice(0, 80));
    });
  } catch (e4) { /* optional */ }

  /* ---- Blog subscribe form -> SAME endpoint as the deal-alert form ---- */
  function endpointReady(url) {
    url = String(url || '').trim();
    return !!url && url !== 'PASTE_APPS_SCRIPT_WEB_APP_URL_HERE' && /^https?:\/\//.test(url);
  }
  function postViaForm(payload, endpoint) {
    try {
      var f = document.createElement('form');
      f.method = 'POST'; f.action = endpoint; f.target = 'bsIframe'; f.style.display = 'none';
      var fr = document.getElementById('bsIframe');
      if (!fr) {
        fr = document.createElement('iframe');
        fr.name = 'bsIframe'; fr.id = 'bsIframe'; fr.style.display = 'none';
        document.body.appendChild(fr);
      }
      Object.keys(payload).forEach(function (k) {
        var i = document.createElement('input');
        i.type = 'hidden'; i.name = k;
        i.value = (payload[k] === undefined || payload[k] === null) ? '' : String(payload[k]);
        f.appendChild(i);
      });
      document.body.appendChild(f);
      f.submit();
      setTimeout(function () { try { f.remove(); } catch (e) {} }, 15000);
      return true;
    } catch (e) { return false; }
  }
  /* ---- Nav CTA gating: alerts need COLLECT, review needs live services ---- */
  function initNavGating() {
    if (!document.querySelectorAll) return;
    function gate(selector, hide) {
      var nodes = document.querySelectorAll(selector);
      for (var i = 0; i < nodes.length; i++) {
        if (hide) { nodes[i].setAttribute('hidden', ''); nodes[i].style.display = 'none'; }
        else { nodes[i].removeAttribute('hidden'); nodes[i].style.display = ''; }
      }
    }
    gate('a[data-gc="blog-cta-alerts"]', !COLLECT_DATA_ENABLED);
    gate('a.pill[href*="contact"]', PRE_REGISTRATION_MODE);
  }
  /* ---- CTA copy swap: service offers need live services (auto-restores) ---- */
  function initCtaSwap() {
    if (!document.querySelectorAll || !PRE_REGISTRATION_MODE) return;
    var nodes, i, h, p;
    /* Post "second opinion" box -> reader-questions wording (Ask-a-question button kept). */
    nodes = document.querySelectorAll('aside.ctabox');
    for (i = 0; i < nodes.length; i++) {
      if (nodes[i].querySelector('#blog-subscribe')) continue;
      h = nodes[i].querySelector('h3');
      if (h && /second opinion/i.test(h.textContent || '')) {
        h.textContent = 'Have a question about this breakdown?';
        p = nodes[i].querySelector('p');
        if (p) p.textContent = 'Reader questions are welcome - use the contact page and we reply within one working day.';
      }
    }
    /* About page: pre-launch wording drops "invest alongside us" + 24/7 assistant line. */
    nodes = document.querySelectorAll('section.wrap p');
    for (i = 0; i < nodes.length; i++) {
      if (/invest alongside us/i.test(nodes[i].textContent || '')) {
        nodes[i].innerHTML = 'Want to collaborate or advertise? <a href="contact.html">Get in touch</a> - ' +
          'reader questions welcome too.';
      }
    }
  }
  function initForm() {
    var form = document.getElementById('blog-subscribe');
    if (!form) return;
    var soon = document.getElementById('bs-soon');
    if (!COLLECT_DATA_ENABLED) {
      form.setAttribute('hidden', '');
      form.style.display = 'none';
      if (soon) { soon.removeAttribute('hidden'); soon.style.display = ''; }
    } else {
      form.removeAttribute('hidden');
      form.style.display = '';
      if (soon) { soon.setAttribute('hidden', ''); soon.style.display = 'none'; }
    }
    var emailEl = document.getElementById('bs-email');
    var nameEl = document.getElementById('bs-name');
    var hpEl = document.getElementById('bs-website');
    var consentEl = document.getElementById('bs-consent');
    var btn = document.getElementById('bs-btn');
    var msg = document.getElementById('bs-msg');
    function say(html, ok) {
      if (!msg) return;
      msg.innerHTML = html;
      msg.style.color = ok ? '#4ade80' : '#fca5a5';
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      /* COLLECT_DATA_ENABLED=false: collect nothing - not even into local variables. */
      if (!COLLECT_DATA_ENABLED) { say('Email alerts opening soon.', false); return; }
      var email = String(emailEl.value || '').trim();
      var name = String(nameEl.value || '').trim();
      var hp = String(hpEl.value || '').trim();
      var consent = !!(consentEl && consentEl.checked);
      /* Honeypot: bots fill it; humans never see it. Pretend success, store nothing. */
      if (hp) {
        say('<b>You are subscribed &mdash; check your inbox weekly.</b>', true);
        form.reset();
        return;
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
        say('Please enter a valid email address.', false);
        return;
      }
      if (name.length > 100) { say('Please shorten your name.', false); return; }
      if (!consent) { say('Please tick the consent box so we can email you.', false); return; }
      var endpoint = cfg.alertEndpoint || '';
      if (!endpointReady(endpoint)) {
        say('Subscriptions are not live yet &mdash; please check back shortly.', false);
        return;
      }
      var payload = { name: name, email: email, phone: '', strategy: 'Any',
        budgetMin: '', budgetMax: '', areas: '', consent: true, source: 'blog', website: '' };
      if (btn) { btn.disabled = true; btn.style.opacity = '.6'; }
      say('Sending&hellip;', true);
      /* JSON body, NO Content-Type header: Apps Script rejects preflighted CORS. */
      fetch(endpoint, { method: 'POST', body: JSON.stringify(payload) })
        .then(function (res) {
          if (!res || !res.ok) throw new Error('http');
          return res.text().then(function (t) {
            try { return JSON.parse(t); } catch (e) { return { ok: true }; }
          });
        })
        .then(function (data) {
          if (btn) { btn.disabled = false; btn.style.opacity = ''; }
          if (data && data.ok === false) {
            var why = (data.error && String(data.error).replace(/[<>&]/g, '')) || 'Please try again.';
            say('<b>Sorry &mdash; that did not go through.</b> ' + why, false);
            return;
          }
          gcEvent('blog-subscribe-submit', 'Blog subscribe');
          say('<b>You are subscribed &mdash; check your inbox weekly.</b>', true);
          form.reset();
        })
        .catch(function () {
          /* Apps Script answers via a redirect that ad-blockers sometimes stop;
             the POST itself usually landed (the server de-dupes by email), so
             resend as a plain hidden-form navigation, which nothing blocks. */
          if (postViaForm(payload, endpoint)) {
            if (btn) { btn.disabled = false; btn.style.opacity = ''; }
            gcEvent('blog-subscribe-submit', 'Blog subscribe');
            say('<b>You are subscribed &mdash; check your inbox weekly.</b>', true);
            form.reset();
          } else {
            if (btn) { btn.disabled = false; btn.style.opacity = ''; }
            say('<b>Sorry &mdash; that did not go through.</b> Please check your connection and try again.', false);
          }
        });
    });
  }
  function initAll() { initForm(); initNavGating(); initCtaSwap(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll);
  else initAll();
})();

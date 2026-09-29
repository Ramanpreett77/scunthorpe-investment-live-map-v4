
(function () {
  var A = window.PB_ARTICLES || [];
  function find(re) { for (var i = 0; i < A.length; i++) if (re.test(A[i].title + A[i].cat)) return A[i]; return null; }
  var box = document.createElement('div');
  box.innerHTML =
    '<button id="pbFab" style="position:fixed;right:22px;bottom:22px;z-index:99;width:58px;height:58px;border-radius:50%;background:#d9b45b;border:none;font-size:26px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.3)">&#128172;</button>' +
    '<div id="pbChat" style="display:none;position:fixed;right:22px;bottom:92px;z-index:99;width:340px;max-width:calc(100vw - 32px);height:460px;max-height:70vh;background:#fff;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.35);display:none;flex-direction:column;overflow:hidden;font-family:inherit">' +
    '<div style="background:#0f2a43;color:#fff;padding:14px 16px"><b>Property Assistant</b><div style="font-size:.78rem;color:#9fd6a4">&#9679; Online 24/7</div></div>' +
    '<div id="pbMsgs" style="flex:1;overflow-y:auto;padding:14px;background:#f4f6f9"></div>' +
    '<div id="pbChips" style="padding:8px 12px;background:#f4f6f9;display:flex;flex-wrap:wrap;gap:6px"></div>' +
    '<form id="pbForm" style="display:flex;border-top:1px solid #e2e7ee"><input id="pbIn" placeholder="Type a message..." style="flex:1;border:none;padding:12px;font:inherit;outline:none"><button style="background:#0f2a43;color:#fff;border:none;padding:0 16px;cursor:pointer">&#10148;</button></form>' +
    '</div>';
  document.body.appendChild(box);
  var msgs = box.querySelector('#pbMsgs'), chips = box.querySelector('#pbChips');
  var fab = box.querySelector('#pbFab'), panel = box.querySelector('#pbChat');
  var waitingForEmail = false;
  fab.onclick = function () {
    var open = panel.style.display === 'flex';
    panel.style.display = open ? 'none' : 'flex';
    if (!open && !msgs.childElementCount) {
      bot("Hi there! I'm the assistant for this property blog - here 24/7 for questions about our articles, strategies (HMO, BRR, buy-to-let) or how to work with us. How can I help?");
      showChips(["What is BRR?", "HMO basics", "First buy-to-let", "Work with us"]);
    }
  };
  function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
  function add(who, html) {
    var m = document.createElement('div');
    m.style.cssText = 'max-width:85%;margin:6px 0;padding:10px 13px;border-radius:12px;font-size:.9rem;line-height:1.45;' +
      (who === 'bot' ? 'background:#fff;border:1px solid #e2e7ee;' : 'background:#0f2a43;color:#fff;margin-left:auto;');
    m.innerHTML = html;
    msgs.appendChild(m); msgs.scrollTop = msgs.scrollHeight;
  }
  function bot(t) { setTimeout(function(){ add('bot', t); }, 350); }
  function showChips(list) {
    chips.innerHTML = '';
    list.forEach(function (c) {
      var b = document.createElement('button');
      b.textContent = c;
      b.style.cssText = 'background:#eef3f8;border:none;border-radius:16px;padding:6px 12px;font-size:.78rem;cursor:pointer';
      b.onclick = function () { user(c); };
      chips.appendChild(b);
    });
  }
  function articleLink(a) {
    return a ? '<br><a href="' + a.slug + '.html" style="color:#0a66c2;font-weight:600">Read: ' + esc(a.title) + ' &rarr;</a>' : '';
  }
  function answer(q) {
    var t = q.toLowerCase();
    if (waitingForEmail) {
      var m = t.match(/[\w.+-]+@[\w-]+\.[\w.]+/);
      if (m) {
        waitingForEmail = false;
        var leads = []; try { leads = JSON.parse(localStorage.pb_leads || '[]'); } catch (e) {}
        leads.push({ email: m[0], when: new Date().toISOString() });
        localStorage.pb_leads = JSON.stringify(leads);
        return "Perfect - thanks! I've noted <b>" + esc(m[0]) + "</b> and we'll be in touch shortly. Meanwhile, browse the articles above or email us any time. \u{1F3E0}";
      }
      waitingForEmail = false;
    }
    if (/\b(hi|hello|hey)\b/.test(t)) return "Hello! Ask me about BRR, HMOs, buy-to-let, or how to work with us.";
    if (/brr|refurbish|refinance/.test(t)) { var a = find(/BRR/i); return "BRR = <b>Buy, Refurbish, Refinance</b>: buy below market value, add value through refurbishment, then refinance on the new valuation to recycle your capital into the next deal." + articleLink(a); }
    if (/hmo|licen|room/.test(t)) { var b = find(/HMO/i); return "An HMO rents by the room, which can lift yields well above single lets - but licensing (mandatory, additional, selective) and setup costs are the key details." + articleLink(b); }
    if (/first|start|begin|new/.test(t)) { var c = find(/First|Buy-to-Let/i); return "For your first buy-to-let: sort your structure (personal vs company), budget ~25% deposit plus the extra SDLT surcharge, and buy for the tenant - not for yourself." + articleLink(c); }
    if (/mortgage|finance|refinan|equity/.test(t)) { var d = find(/Refinanc|Finance/i); return "Refinancing releases equity from existing properties - typically up to ~75% LTV on the new valuation - to fund your next purchase. Timing and costs (ERCs, fees) decide whether it's worth it." + articleLink(d); }
    if (/deal|sourc|find/.test(t)) { var e = find(/Sourc|Deal/i); return "The best deals come from auctions, direct-to-vendor, probate and networking - and a genuine bargain always has evidence: comps, real quotes, a proven exit." + articleLink(e); }
    if (/contact|talk|human|call|email|work|service|help me|invest with|advert/.test(t)) {
      waitingForEmail = true;
      return "Of course! For sales, partnerships or support we reply within one working day. What's the best <b>email address</b> for us to reach you?";
    }
    if (/sourc|deal for me|find me a|off-market/.test(t)) return "SGJM's sourcing service launches as soon as our registrations complete - meanwhile we're building the <b>investor waitlist</b>. Type 'work with us' to leave your buying criteria and you'll be first in line (plus I'll send you the free sourcing checklist today).";
    if (/dubai/.test(t)) return "For Dubai I introduce investors to vetted, RERA-licensed partners - plain-English market education, and any referral fee is always disclosed. Want the Dubai intro pack? Type 'work with us'.";
    if (/yield|return|profit/.test(t)) return "Yields vary by strategy: well-run HMOs in strong areas can reach double-digit gross yields, while single lets typically land lower with less effort. The articles include worked examples.";
    return "I can help with: <b>BRR</b>, <b>HMOs</b>, <b>first buy-to-let</b>, <b>refinancing</b>, <b>deal sourcing</b> - or type 'work with us' to leave your details.";
  }
  function user(t) { add('user', esc(t)); setTimeout(function () { add('bot', answer(t)); }, 500); }
  box.querySelector('#pbForm').onsubmit = function (e) {
    e.preventDefault();
    var v = box.querySelector('#pbIn').value.trim();
    if (!v) return;
    box.querySelector('#pbIn').value = '';
    user(v);
  };
})();

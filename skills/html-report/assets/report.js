    (function () {
      var btn = document.getElementById('copy-btn');
      var menu = document.getElementById('copy-menu');
      var toast = document.getElementById('copy-toast');
      var content = document.querySelector('.content');
      var STRIP = '.copy-wrap, .copy-toast, footer, .block-copy';
      function openMenu(open) { menu.classList.toggle('open', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
      btn.addEventListener('click', function (e) { e.stopPropagation(); openMenu(!menu.classList.contains('open')); });
      document.addEventListener('click', function (e) { if (!menu.contains(e.target) && e.target !== btn) openMenu(false); });
      function showToast(msg) { toast.textContent = msg; toast.classList.add('show'); setTimeout(function(){ toast.classList.remove('show'); }, 1600); }
      function htmlToMarkdown(root) {
        var clone = root.cloneNode(true);
        clone.querySelectorAll(STRIP).forEach(function(n){ n.remove(); });
        var out = [];
        function walk(node) {
          if (node.nodeType === 3) { out.push(node.nodeValue.replace(/\s+/g, ' ')); return; }
          if (node.nodeType !== 1) return;
          var tag = node.tagName.toLowerCase();
          if (tag === 'h1') { out.push('\n# '); node.childNodes.forEach(walk); out.push('\n\n'); return; }
          if (tag === 'h2') { out.push('\n\n## '); node.childNodes.forEach(walk); out.push('\n\n'); return; }
          if (tag === 'h3') { out.push('\n\n### '); node.childNodes.forEach(walk); out.push('\n\n'); return; }
          if (tag === 'summary') { out.push('**'); node.childNodes.forEach(walk); out.push('**\n\n'); return; }
          if (tag === 'p') { node.childNodes.forEach(walk); out.push('\n\n'); return; }
          if (tag === 'br') { out.push('\n'); return; }
          if (tag === 'strong' || tag === 'b') { out.push('**'); node.childNodes.forEach(walk); out.push('**'); return; }
          if (tag === 'em' || tag === 'i') { out.push('_'); node.childNodes.forEach(walk); out.push('_'); return; }
          if (tag === 'code' && (!node.parentElement || node.parentElement.tagName.toLowerCase() !== 'pre')) { out.push('`'); node.childNodes.forEach(walk); out.push('`'); return; }
          if (tag === 'pre') { out.push('\n```\n' + (node.textContent || '') + '\n```\n\n'); return; }
          if (tag === 'a') { var href = node.getAttribute('href') || ''; out.push('['); node.childNodes.forEach(walk); out.push('](' + href + ')'); return; }
          if (tag === 'ul' || tag === 'ol') { out.push('\n'); var i = 1; node.childNodes.forEach(function(c){ if (c.nodeType===1 && c.tagName.toLowerCase()==='li') { out.push(tag==='ol' ? (i++)+'. ' : '- '); c.childNodes.forEach(walk); out.push('\n'); } }); out.push('\n'); return; }
          if (tag === 'table') {
            var rows = node.querySelectorAll('tr');
            if (!rows.length) return;
            var headRow = rows[0];
            var headCells = headRow.querySelectorAll('th,td');
            var headers = Array.from(headCells).map(function(c){ return (c.textContent || '').trim().replace(/\s+/g, ' '); });
            out.push('\n| ' + headers.join(' | ') + ' |\n');
            out.push('|' + headers.map(function(){ return ' --- '; }).join('|') + '|\n');
            for (var r = 1; r < rows.length; r++) {
              var cells = rows[r].querySelectorAll('th,td');
              var line = Array.from(cells).map(function(c){ return (c.textContent || '').trim().replace(/\s+/g, ' ').replace(/\|/g, '\\|'); });
              out.push('| ' + line.join(' | ') + ' |\n');
            }
            out.push('\n');
            return;
          }
          if (tag === 'div' && node.classList.contains('tldr')) { out.push('\n> '); node.childNodes.forEach(walk); out.push('\n\n'); return; }
          node.childNodes.forEach(walk);
        }
        walk(clone);
        return out.join('').replace(/\n{3,}/g, '\n\n').trim() + '\n';
      }
      function buildRichHtml(root) {
        var clone = root.cloneNode(true);
        clone.querySelectorAll(STRIP).forEach(function(n){ n.remove(); });
        return '<div style="font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; color: #1a1a1a; line-height: 1.55;">' + clone.innerHTML + '</div>';
      }
      function buildPlain(root) { return htmlToMarkdown(root).replace(/[#*_`>]/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1'); }
      async function copyFormat(fmt) {
        try {
          if (fmt === 'rich') {
            var html = buildRichHtml(content);
            var plain = buildPlain(content);
            if (navigator.clipboard && window.ClipboardItem) {
              await navigator.clipboard.write([new ClipboardItem({ 'text/html': new Blob([html], {type:'text/html'}), 'text/plain': new Blob([plain], {type:'text/plain'}) })]);
            } else { await navigator.clipboard.writeText(plain); }
            showToast('Rich text copied');
          } else if (fmt === 'markdown') { await navigator.clipboard.writeText(htmlToMarkdown(content)); showToast('Markdown copied'); }
          else { await navigator.clipboard.writeText(buildPlain(content)); showToast('Plain text copied'); }
          btn.classList.add('ok'); setTimeout(function(){ btn.classList.remove('ok'); }, 1200);
        } catch (err) { showToast('Copy failed — ' + (err && err.message ? err.message : 'unknown')); }
        openMenu(false);
      }
      menu.querySelectorAll('button[data-fmt]').forEach(function(b){ b.addEventListener('click', function(){ copyFormat(b.getAttribute('data-fmt')); }); });

      // ── Per-block copy icons ──────────────────────────────────────────────
      var COPY_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
      function mkBtn(title) { var b = document.createElement('button'); b.className = 'block-copy'; b.type = 'button'; b.title = title; b.setAttribute('aria-label', title); b.innerHTML = COPY_SVG; return b; }
      function flash(b) { b.classList.add('ok'); setTimeout(function(){ b.classList.remove('ok'); }, 1200); }
      async function copyPlain(text, b) { try { await navigator.clipboard.writeText(text); flash(b); showToast('Block copied'); } catch (e) { showToast('Copy failed'); } }
      async function copyRich(el, b) {
        try {
          var md = htmlToMarkdown(el);
          if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([new ClipboardItem({ 'text/html': new Blob([buildRichHtml(el)], {type:'text/html'}), 'text/plain': new Blob([md], {type:'text/plain'}) })]);
          } else { await navigator.clipboard.writeText(md); }
          flash(b); showToast('Block copied');
        } catch (e) { showToast('Copy failed'); }
      }
      // Logical blocks: conversations, callouts, TL;DR (copy the whole block as rich/markdown)
      content.querySelectorAll('details, .callout, .tldr').forEach(function(el){
        el.classList.add('copyable');
        var b = mkBtn(el.tagName.toLowerCase() === 'details' ? 'Copy this conversation' : 'Copy this block');
        b.addEventListener('click', function(e){ e.preventDefault(); e.stopPropagation(); copyRich(el, b); });
        el.appendChild(b);
      });
      // Standalone code snippets only — skip <pre> transcripts nested inside conversation <details>
      content.querySelectorAll('pre').forEach(function(el){
        if (el.closest('details')) return;
        el.classList.add('copyable');
        var b = mkBtn('Copy this snippet');
        b.addEventListener('click', function(e){ e.preventDefault(); e.stopPropagation(); copyPlain(el.textContent || '', b); });
        el.appendChild(b);
      });
      // Section headings: copy the heading + its content up to the next heading of same/higher level
      content.querySelectorAll('main h2, main h3').forEach(function(h){
        var lvl = h.tagName.toLowerCase();
        var b = mkBtn('Copy this section');
        b.addEventListener('click', function(e){
          e.preventDefault(); e.stopPropagation();
          var tmp = document.createElement('div');
          tmp.appendChild(h.cloneNode(true));
          var n = h.nextElementSibling;
          while (n) {
            var t = n.tagName ? n.tagName.toLowerCase() : '';
            if (t === 'h2') break;
            if (lvl === 'h3' && t === 'h3') break;
            tmp.appendChild(n.cloneNode(true));
            n = n.nextElementSibling;
          }
          copyRich(tmp, b);
        });
        h.appendChild(b);
      });

      // ── Sidebar scroll-spy ────────────────────────────────────────────────
      var links = document.querySelectorAll('.sidebar a[href^="#"]');
      var secs = Array.from(links).map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); }).filter(Boolean);
      function onScroll() {
        var y = window.scrollY + 80;
        var current = secs[0];
        for (var i = 0; i < secs.length; i++) { if (secs[i] && secs[i].offsetTop <= y) current = secs[i]; }
        links.forEach(function (a) { a.classList.toggle('active', a.getAttribute('href') === '#' + (current && current.id)); });
      }
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    })();
  

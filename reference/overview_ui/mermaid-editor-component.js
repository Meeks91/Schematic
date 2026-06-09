/**
 * MermaidEditorComponent — Reusable mermaid editor with full feature set.
 *
 * Embeddable in any page. Instantiate with:
 *   new MermaidEditor(containerEl, { content, onSave, onNote, onQuestion, onOpenIde, pathsMap })
 *
 * Features: split-pane (source left, preview right), resizable, node-click-to-source highlight,
 * right-click context menu (notes, questions, copy SVG, download SVG, open in VS Code / IntelliJ),
 * draggable sticky notes and Q&A bubbles, multi-turn Q&A thread.
 */

const ME_INPUT_MAX_PX = 90;  // reply box grows with content up to this height, then scrolls

const MERMAID_EDITOR_CSS = `
.me-container{display:flex;height:100%;background:#1e1e2e;border-radius:6px;overflow:hidden;border:1px solid #3a3a5e;position:relative}
.me-container.me-fullscreen{position:fixed!important;inset:0;z-index:900;border-radius:0;border:none;height:100vh!important}
.me-container.me-fullscreen .me-exit-fs{display:block}
.me-editor{width:40%;min-width:180px;display:flex;flex-direction:column;background:#2a2a3e;position:relative}
.me-resizer{width:4px;cursor:col-resize;background:#3a3a5e;flex-shrink:0;transition:background .15s}
.me-resizer:hover{background:#89b4fa}
.me-src-wrap{flex:1;position:relative;overflow:hidden}
.me-src-highlight{position:absolute;left:38px;top:0;right:0;height:100%;pointer-events:none;overflow:hidden;padding:12px;font:12px/1.6 'JetBrains Mono',monospace;white-space:pre-wrap;word-wrap:break-word;color:transparent}
.me-src-highlight .hl-line{background:rgba(137,180,250,.15);border-left:2px solid #89b4fa;margin-left:-12px;padding-left:10px;display:block}
.me-textarea{width:100%;height:100%;border:0;padding:12px 12px 12px 42px;font:12px/1.6 'JetBrains Mono',monospace;resize:none;outline:none;background:transparent;color:#cdd6f4;tab-size:2;position:relative;z-index:2}
.me-line-nums{position:absolute;left:0;top:0;width:32px;height:100%;overflow:hidden;padding:12px 4px 12px 0;text-align:right;font:12px/1.6 'JetBrains Mono',monospace;color:#7f849c;pointer-events:none;user-select:none;border-right:1px solid #3a3a5e;z-index:3}
.me-bar{padding:6px 10px;border-top:1px solid #3a3a5e;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.me-bar button{padding:4px 8px;cursor:pointer;border:1px solid #3a3a5e;border-radius:3px;background:#2a2a3e;color:#cdd6f4;font-size:11px;font-family:inherit;transition:all .12s}
.me-bar button:hover{background:#89b4fa;color:#1e1e2e;border-color:#89b4fa}
.me-exit-fs{display:none;position:absolute;top:8px;right:8px;z-index:10;padding:4px 10px;cursor:pointer;border:1px solid #3a3a5e;border-radius:3px;background:#2a2a3e;color:#cdd6f4;font-size:11px}
.me-exit-fs:hover{background:#f38ba8;color:#1e1e2e;border-color:#f38ba8}
.me-bar .me-status{color:#7f849c;font-size:10px;margin-left:auto}
.me-preview{flex:1;overflow:auto;padding:16px;position:relative;background:#181825}
.me-preview svg .node{cursor:pointer;transition:opacity .15s}
.me-preview svg .node:hover{opacity:.8}
.me-preview svg .node.highlighted rect,.me-preview svg .node.highlighted polygon{stroke:#89b4fa!important;stroke-width:3px!important;filter:drop-shadow(0 0 6px rgba(137,180,250,.4))}
.me-preview svg text{font-family:'Inter','SF Pro',-apple-system,sans-serif!important}
.me-preview svg .nodeLabel{font-size:12px!important;line-height:1.5!important;text-align:left!important}
.me-preview svg .nodeLabel p{text-align:left!important;margin:0;color:#dde0f0!important}
.me-preview svg .nodeLabel b{font-size:13px!important;font-weight:700!important;color:#a6e3a1!important;display:block;margin-bottom:3px}
.me-preview svg .cluster-label text,.me-preview svg .cluster-label .nodeLabel,.me-preview svg .cluster-label .nodeLabel p{font-size:14px!important;font-weight:700!important;fill:#b4d0fb!important;color:#b4d0fb!important}
.me-preview svg .edgeLabel{font-size:11px!important;font-weight:600}
.me-preview svg .edgeLabel span,.me-preview svg .edgeLabel p{color:#f9e2af!important;background:rgba(30,30,46,.9)!important;padding:2px 5px;border-radius:3px;font-family:'JetBrains Mono',monospace!important;font-feature-settings:'liga' 0,'calt' 0!important;font-variant-ligatures:none!important}
.me-preview svg rect.basic{fill:#1e1e2e!important;stroke:#4a4a7a!important;stroke-width:1.5px;rx:8;ry:8}
.me-preview svg .cluster rect{fill:rgba(30,30,46,.8)!important;stroke:#5a5a8a!important;stroke-width:2px;rx:10;ry:10}
.me-preview svg .edgePath path{stroke:#6a6a9a!important;stroke-width:1.5px}
.me-preview svg .arrowheadPath{fill:#6a6a9a!important;stroke:#6a6a9a!important}
.me-preview svg polygon{fill:#2a2a4e!important;stroke:#5a5a8a!important}
.me-preview svg foreignObject div{font-family:'Inter','SF Pro',-apple-system,sans-serif!important;color:#dde0f0!important}
.me-ctxmenu{display:none;position:fixed;background:#2a2a3e;border:1px solid #3a3a5e;border-radius:6px;box-shadow:0 4px 20px rgba(0,0,0,.4);padding:4px 0;z-index:999;min-width:160px}
.me-ctxmenu div{padding:7px 14px;cursor:pointer;font-size:11px;display:flex;align-items:center;gap:6px}
.me-ctxmenu div:hover{background:#89b4fa;color:#1e1e2e}
.me-ctxmenu .shortcut{margin-left:auto;color:#7f849c;font-size:9px}
.me-notepanel{display:none;position:fixed;background:#2a2a3e;border:1px solid #89b4fa;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.5);padding:10px;z-index:1000;width:280px}
.me-notepanel textarea{width:100%;height:60px;font:11px/1.3 'JetBrains Mono',monospace;border:1px solid #3a3a5e;border-radius:4px;padding:6px;background:#1e1e2e;color:#cdd6f4;resize:vertical;outline:none}
.me-notepanel textarea:focus{border-color:#89b4fa}
.me-notepanel .np-bar{display:flex;gap:4px;margin-top:6px;align-items:center}
.me-notepanel .np-bar button{padding:3px 8px;font-size:10px}
.me-notepanel .np-hint{font-size:9px;color:#7f849c;margin-left:auto}
.me-sticky{position:absolute;background:#3a3a5e;border:1px solid #89b4fa;border-radius:6px;padding:5px 9px;font-size:10px;color:#cdd6f4;max-width:180px;word-wrap:break-word;box-shadow:0 2px 8px rgba(0,0,0,.3);cursor:grab;user-select:none;z-index:50}
.me-sticky.dragging{cursor:grabbing;opacity:.9}
.me-sticky::before{content:'';position:absolute;top:-4px;left:10px;width:6px;height:6px;background:#89b4fa;border-radius:50%}
.me-sticky .close{position:absolute;top:1px;right:5px;cursor:pointer;color:#7f849c;font-size:9px}
.me-sticky .close:hover{color:#f38ba8}
.me-qa{position:absolute;background:#1e1e2e;border:1px solid #89b4fa;border-radius:8px;padding:9px 11px;font-size:10px;color:#cdd6f4;max-width:280px;min-width:180px;box-shadow:0 2px 12px rgba(0,0,0,.4);cursor:grab;user-select:none;z-index:50}
.me-qa.dragging{cursor:grabbing;opacity:.9}
.me-qa .close{position:absolute;top:3px;right:7px;cursor:pointer;color:#7f849c;font-size:9px}
.me-qa .close:hover{color:#f38ba8}
.me-qa .thread{max-height:160px;overflow-y:auto;margin-bottom:5px;cursor:default;user-select:text;scroll-behavior:smooth}
.me-qa .msg{padding:3px 0;border-bottom:1px solid #3a3a5e;font-size:10px}
.me-qa .msg:last-child{border-bottom:none}
.me-qa .msg.user{color:#89b4fa}
.me-qa .msg.agent{color:#a6e3a1}
.me-qa .msg.pending{color:#f9e2af;font-style:italic}
.me-qa .msg .role{font-weight:600;font-size:8px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:1px;display:block}
.me-qa .reply-bar{display:flex;gap:3px;margin-top:4px;cursor:default;align-items:flex-end}
.me-qa .reply-bar textarea{flex:1;box-sizing:border-box;min-height:42px;max-height:${ME_INPUT_MAX_PX}px;overflow-y:auto;resize:none;background:#2a2a3e;border:1px solid #3a3a5e;border-radius:3px;padding:3px 5px;font:10px/1.2 'JetBrains Mono',monospace;color:#cdd6f4;outline:none}
.me-qa .reply-bar textarea:focus{border-color:#89b4fa}
.me-qa .reply-bar button{padding:2px 6px;font-size:9px}
`;

class MermaidEditor {
  constructor(container, opts = {}) {
    this.container = container;
    this.content = opts.content || '';
    this.onSave = opts.onSave || (() => {});
    this.onNote = opts.onNote || (() => {});
    this.onQuestion = opts.onQuestion || (() => {});
    this.onOpenIde = opts.onOpenIde || (() => {});
    this.pathsMap = opts.pathsMap || {};
    this.pollAnswers = opts.pollAnswers || (async () => []);
    this.scale = 1;
    this.notes = [];
    this.highlightedLines = new Set();
    this.renderCount = 0;
    this.dragTarget = null;
    this.dragStart = {x:0,y:0};
    this.dragStartPos = {x:0,y:0};
    this.ctxNodeId = null;
    this.noteCtx = {x:0,y:0,previewX:0,previewY:0};
    this.pollIntervals = {};
    this._injectStyles();
    this._build();
    this._bind();
    this._render();
  }

  _injectStyles() {
    if (!document.getElementById('me-styles')) {
      const s = document.createElement('style');
      s.id = 'me-styles';
      s.textContent = MERMAID_EDITOR_CSS;
      document.head.appendChild(s);
    }
  }

  _build() {
    this.container.innerHTML = `
      <div class="me-container">
        <div class="me-editor">
          <div class="me-src-wrap">
            <div class="me-line-nums"></div>
            <div class="me-src-highlight"></div>
            <textarea class="me-textarea" spellcheck="false"></textarea>
          </div>
          <div class="me-bar">
            <button class="me-save">Save</button>
            <button class="me-zout">−</button><button class="me-zin">+</button><button class="me-zfit">fit</button>
            <button class="me-fs">⤢ Fullscreen</button>
            <span class="me-status"></span>
          </div>
        </div>
        <div class="me-resizer"></div>
        <div class="me-preview"></div>
        <button class="me-exit-fs">✕ Exit Fullscreen</button>
      </div>
    `;
    this.editorEl = this.container.querySelector('.me-editor');
    this.textarea = this.container.querySelector('.me-textarea');
    this.lineNums = this.container.querySelector('.me-line-nums');
    this.srcHighlight = this.container.querySelector('.me-src-highlight');
    this.preview = this.container.querySelector('.me-preview');
    this.resizer = this.container.querySelector('.me-resizer');
    this.statusEl = this.container.querySelector('.me-status');
    this.textarea.value = this.content;

    // Context menu (appended to body)
    this.ctxmenu = document.createElement('div');
    this.ctxmenu.className = 'me-ctxmenu';
    this.ctxmenu.innerHTML = `
      <div data-action="note">📌 Add note<span class="shortcut">N</span></div>
      <div data-action="question">❓ Ask question<span class="shortcut">Q</span></div>
      <div data-action="open-vscode" class="me-ide-item" style="display:none">✎ Open in VS Code</div>
      <div data-action="open-idea" class="me-ide-item" style="display:none">⚙ Open in IntelliJ</div>
      <div data-action="copy-svg">📋 Copy SVG</div>
      <div data-action="download-svg">💾 Download SVG</div>
    `;
    document.body.appendChild(this.ctxmenu);

    // Note panel (appended to body)
    this.notepanel = document.createElement('div');
    this.notepanel.className = 'me-notepanel';
    this.notepanel.innerHTML = `
      <textarea placeholder="Leave a note..."></textarea>
      <div class="np-bar">
        <button class="me-np-send">Send</button>
        <button class="me-np-cancel">Cancel</button>
        <span class="np-hint">Enter=send · Esc=close</span>
      </div>
    `;
    document.body.appendChild(this.notepanel);
    this.noteInput = this.notepanel.querySelector('textarea');
  }

  _bind() {
    const self = this;
    this.textarea.addEventListener('input', () => { self._updateLineNums(); self._updateHighlight(); self._debouncedRender(); });
    this.textarea.addEventListener('scroll', () => { self._syncScroll(); });
    this.container.querySelector('.me-save').onclick = () => { self.onSave(self.textarea.value); self.statusEl.textContent = 'saved ✓'; };
    this.container.querySelector('.me-zin').onclick = () => { self.scale = Math.min(self.scale*1.25,8); self._applyScale(); };
    this.container.querySelector('.me-zout').onclick = () => { self.scale = Math.max(self.scale/1.25,.05); self._applyScale(); };
    this.container.querySelector('.me-zfit').onclick = () => { self.scale = 1; self._applyScale(); };
    this.container.querySelector('.me-fs').onclick = () => { self.container.querySelector('.me-container').classList.toggle('me-fullscreen'); };
    this.container.querySelector('.me-exit-fs').onclick = () => { self.container.querySelector('.me-container').classList.remove('me-fullscreen'); };

    // Resize
    let resizing = false;
    this.resizer.addEventListener('mousedown', e => { resizing = true; document.body.style.cursor='col-resize'; e.preventDefault(); });
    document.addEventListener('mousemove', e => {
      if (resizing) {
        const rect = self.container.getBoundingClientRect();
        const w = e.clientX - rect.left;
        if (w > 120 && w < rect.width - 150) self.editorEl.style.width = w + 'px';
      }
      if (self.dragTarget) {
        self.dragTarget.style.left = (e.clientX - self.dragStart.x + self.dragStartPos.x) + 'px';
        self.dragTarget.style.top = (e.clientY - self.dragStart.y + self.dragStartPos.y) + 'px';
      }
    });
    document.addEventListener('mouseup', () => {
      resizing = false; document.body.style.cursor = '';
      if (self.dragTarget) { self.dragTarget.classList.remove('dragging'); self.dragTarget = null; }
    });

    // Context menu
    this.preview.addEventListener('contextmenu', e => {
      e.preventDefault();
      const rect = self.preview.getBoundingClientRect();
      self.noteCtx = {x:e.clientX, y:e.clientY, previewX:e.clientX-rect.left+self.preview.scrollLeft, previewY:e.clientY-rect.top+self.preview.scrollTop};
      const nodeEl = e.target.closest('.node');
      self.ctxNodeId = null;
      const ideItems = self.ctxmenu.querySelectorAll('.me-ide-item');
      if (nodeEl) {
        const match = nodeEl.id.match(/(?:flowchart|graph)-(.+)-\d+$/);
        if (match && self.pathsMap[match[1]]) { self.ctxNodeId = match[1]; ideItems.forEach(el => el.style.display = 'flex'); }
        else ideItems.forEach(el => el.style.display = 'none');
      } else ideItems.forEach(el => el.style.display = 'none');
      self.ctxmenu.style.display = 'block';
      self.ctxmenu.style.left = e.clientX + 'px';
      self.ctxmenu.style.top = e.clientY + 'px';
    });

    document.addEventListener('mousedown', e => {
      if (!self.ctxmenu.contains(e.target)) self.ctxmenu.style.display = 'none';
      if (self.notepanel.style.display === 'block' && !self.notepanel.contains(e.target) && !e.target.closest('.me-qa') && !e.target.closest('.me-sticky'))
        self.notepanel.style.display = 'none';
    });

    this.ctxmenu.addEventListener('click', e => {
      const action = e.target.closest('[data-action]')?.dataset.action;
      if (!action) return;
      self.ctxmenu.style.display = 'none';
      if (action === 'note') self._openNotePanel('note');
      else if (action === 'question') self._openNotePanel('question');
      else if (action === 'open-vscode') self.onOpenIde('vscode', self.pathsMap[self.ctxNodeId]);
      else if (action === 'open-idea') self.onOpenIde('idea', self.pathsMap[self.ctxNodeId]);
      else if (action === 'copy-svg') { navigator.clipboard.writeText(self.preview.innerHTML); self.statusEl.textContent = 'copied ✓'; }
      else if (action === 'download-svg') { const b=new Blob([self.preview.innerHTML],{type:'image/svg+xml'}); const u=URL.createObjectURL(b); const a=document.createElement('a'); a.href=u; a.download='diagram.svg'; a.click(); URL.revokeObjectURL(u); }
    });

    // Note panel
    this.notepanel.querySelector('.me-np-cancel').onclick = () => { self.notepanel.style.display = 'none'; };
    this.notepanel.querySelector('.me-np-send').onclick = () => self._submitNote();
    this.noteInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); self._submitNote(); }
      if (e.key === 'Escape') { self.notepanel.style.display = 'none'; self.container.querySelector('.me-container').classList.remove('me-fullscreen'); }
    });

    // Drag + close for notes/qa
    this.preview.addEventListener('mousedown', e => {
      const bubble = e.target.closest('.me-qa,.me-sticky');
      if (!bubble) return;
      if (e.target.closest('.thread,.reply-bar,.close')) return;
      self.dragTarget = bubble;
      self.dragTarget.classList.add('dragging');
      self.dragStart = {x:e.clientX, y:e.clientY};
      self.dragStartPos = {x:bubble.offsetLeft, y:bubble.offsetTop};
      e.preventDefault();
    });

    this.preview.addEventListener('click', e => {
      if (e.target.classList.contains('close')) { const p = e.target.closest('.me-qa,.me-sticky'); if(p) p.remove(); return; }
      if (e.target.closest('.me-reply-btn')) { self._handleReply(e.target.closest('.me-reply-btn')); return; }
      if (!e.target.closest('.node') && !e.target.closest('.me-sticky') && !e.target.closest('.me-qa')) {
        self.preview.querySelectorAll('.node.highlighted').forEach(n => n.classList.remove('highlighted'));
        self.highlightedLines.clear(); self._updateHighlight();
      }
    });

    this.preview.addEventListener('keydown', e => {
      if (e.target.matches('.reply-bar textarea') && e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); self._handleReply(e.target.parentElement.querySelector('.me-reply-btn'));
      }
    });

    this.preview.addEventListener('input', e => {
      if (e.target.matches('.reply-bar textarea')) {
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, ME_INPUT_MAX_PX) + 'px';
      }
    });
  }

  _openNotePanel(mode) {
    this._panelMode = mode;
    this.notepanel.style.display = 'block';
    this.notepanel.style.left = Math.min(this.noteCtx.x, window.innerWidth-300)+'px';
    this.notepanel.style.top = Math.min(this.noteCtx.y, window.innerHeight-150)+'px';
    this.noteInput.value = '';
    this.noteInput.placeholder = mode === 'question' ? 'Ask a question...' : 'Leave a note...';
    this.noteInput.focus();
  }

  _submitNote() {
    const text = this.noteInput.value.trim();
    if (!text) return;
    this.notepanel.style.display = 'none';
    if (this._panelMode === 'question') {
      const idx = this.notes.length;
      const q = {thread:[{role:'user',text}], x:this.noteCtx.previewX, y:this.noteCtx.previewY};
      this.notes.push({type:'question', data:q});
      this._renderQa(q, idx);
      this.onQuestion({...q, idx});
      this._startPolling(idx);
    } else {
      const note = {text, x:this.noteCtx.previewX, y:this.noteCtx.previewY};
      this.notes.push({type:'note', data:note});
      this._renderSticky(note);
      this.onNote(note);
    }
  }

  _handleReply(btn) {
    const idx = parseInt(btn.dataset.idx);
    const input = this.preview.querySelector(`#me-reply-${idx}`);
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.style.height = 'auto';
    this.notes[idx].data.thread.push({role:'user', text});
    this._appendThread(idx, {role:'user', text});
    this._appendThread(idx, {role:'pending', text:'⏳ waiting...'});
    this.onQuestion({idx, thread:this.notes[idx].data.thread, x:this.notes[idx].data.x, y:this.notes[idx].data.y});
    this._startPolling(idx);
  }

  _renderSticky(note) {
    const el = document.createElement('div');
    el.className = 'me-sticky';
    el.style.left = note.x+'px'; el.style.top = note.y+'px';
    el.innerHTML = `<span class="close">✕</span>${this._esc(note.text)}`;
    this.preview.appendChild(el);
  }

  _renderQa(q, idx) {
    const el = document.createElement('div');
    el.className = 'me-qa'; el.style.left = q.x+'px'; el.style.top = q.y+'px'; el.dataset.idx = idx;
    el.innerHTML = `<span class="close">✕</span>
      <div class="thread" id="me-thread-${idx}">${q.thread.map(m=>this._msgHtml(m)).join('')}</div>
      <div class="reply-bar"><textarea id="me-reply-${idx}" rows="3" placeholder="Follow up..."></textarea><button class="me-reply-btn" data-idx="${idx}">→</button></div>`;
    this.preview.appendChild(el);
  }

  _msgHtml(m) {
    const cls = m.role==='user'?'user':m.role==='pending'?'pending':'agent';
    const label = m.role==='user'?'You':m.role==='pending'?'':'Agent';
    return `<div class="msg ${cls}"><span class="role">${label}</span>${this._esc(m.text)}</div>`;
  }

  _appendThread(idx, msg) {
    const el = document.getElementById(`me-thread-${idx}`);
    if (!el) return;
    if (msg.role==='agent') { const p=el.querySelector('.msg.pending'); if(p)p.remove(); }
    el.innerHTML += this._msgHtml(msg);
    el.scrollTop = el.scrollHeight;
  }

  _startPolling(idx) {
    if (this.pollIntervals[idx]) clearInterval(this.pollIntervals[idx]);
    let lastCount = 0;
    const threadEl = document.getElementById(`me-thread-${idx}`);
    if (threadEl) lastCount = threadEl.querySelectorAll('.msg.agent').length;
    this.pollIntervals[idx] = setInterval(async () => {
      const answers = await this.pollAnswers();
      const matching = answers.filter(a => a.idx === idx);
      if (matching.length > lastCount) {
        this._appendThread(idx, {role:'agent', text:matching[matching.length-1].answer});
        lastCount = matching.length;
        clearInterval(this.pollIntervals[idx]); delete this.pollIntervals[idx];
      }
    }, 2000);
  }

  _updateLineNums() {
    const n = this.textarea.value.split('\n').length;
    this.lineNums.innerHTML = Array.from({length:n},(_,i)=>`<div>${i+1}</div>`).join('');
  }

  _updateHighlight() {
    const lines = this.textarea.value.split('\n');
    this.srcHighlight.innerHTML = lines.map((l,i) =>
      this.highlightedLines.has(i) ? `<span class="hl-line">${this._esc(l)}\n</span>` : this._esc(l)+'\n'
    ).join('');
    this.srcHighlight.style.transform = `translateY(-${this.textarea.scrollTop}px)`;
  }

  _syncScroll() {
    this.lineNums.style.transform = `translateY(-${this.textarea.scrollTop}px)`;
    this.srcHighlight.style.transform = `translateY(-${this.textarea.scrollTop}px)`;
  }

  _applyScale() { const svg = this.preview.querySelector('svg'); if(svg) { svg.style.transform=`scale(${this.scale})`; svg.style.transformOrigin='0 0'; } }

  _esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  _debouncedRender() {
    clearTimeout(this._renderTimer);
    this.statusEl.textContent = 'editing…';
    this._renderTimer = setTimeout(() => this._render(), 400);
  }

  async _render() {
    this._updateLineNums(); this._updateHighlight();
    try {
      this.renderCount++;
      const {svg} = await mermaid.render('me-g'+this.renderCount, this.textarea.value);
      this.preview.querySelectorAll('.me-sticky,.me-qa').forEach(el => el.remove()); // preserve? no — rerender clears svg
      this.preview.innerHTML = svg;
      this._attachNodeClicks();
      this.statusEl.textContent = '✓';
    } catch(e) {
      this.statusEl.textContent = 'error';
    }
  }

  _attachNodeClicks() {
    this.preview.querySelectorAll('.node').forEach(node => {
      node.addEventListener('click', e => {
        e.stopPropagation();
        this.preview.querySelectorAll('.node.highlighted').forEach(n=>n.classList.remove('highlighted'));
        node.classList.add('highlighted');
        this._highlightSource(node.id);
      });
    });
  }

  _highlightSource(nodeId) {
    this.highlightedLines.clear();
    const lines = this.textarea.value.split('\n');
    const match = nodeId.match(/(?:flowchart|graph)-(.+)-\d+$/);
    if (!match) return;
    const id = match[1];
    for (let i=0;i<lines.length;i++) {
      const t = lines[i].trim();
      if (t.startsWith(id+'[') || t.startsWith(id+'{') || t.startsWith(id+'(') || t.startsWith(id+'"') || t.startsWith(id+' ') || t.startsWith(id+'-') || t===id)
        this.highlightedLines.add(i);
    }
    if (this.highlightedLines.size) {
      const first = [...this.highlightedLines][0];
      this.textarea.scrollTop = Math.max(0, first*19.2 - 80);
    }
    this._updateHighlight();
  }

  setContent(content) { this.content = content; this.textarea.value = content; this._render(); }
  setPaths(paths) { this.pathsMap = paths; }

  destroy() {
    Object.values(this.pollIntervals).forEach(id => clearInterval(id));
    this.pollIntervals = {};
    clearTimeout(this._renderTimer);
    if (this.ctxmenu.parentNode) this.ctxmenu.parentNode.removeChild(this.ctxmenu);
    if (this.notepanel.parentNode) this.notepanel.parentNode.removeChild(this.notepanel);
    this.container.innerHTML = '';
  }
}

if (typeof module !== 'undefined') module.exports = MermaidEditor;

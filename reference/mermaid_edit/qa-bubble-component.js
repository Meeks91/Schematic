/**
 * QABubbleComponent — Shared Q&A chat bubble for all views.
 *
 * Usage:
 *   const bubble = new QABubble(container, {
 *     context: "task:a.1" | "diagram:sequence.mmd" | "overview",
 *     position: { x, y },
 *     onQuestion: async (text, context) => { POST to server },
 *     pollAnswers: async (serverIdx) => { return answer or null },
 *   });
 *   bubble.appendUserMessage(text);
 *   bubble.appendAgentMessage(text);
 *   bubble.destroy();
 */

const QA_INPUT_MAX_PX = 120;  // reply box grows with content up to this height, then scrolls

const QA_BUBBLE_CSS = `
.qa-bubble{position:absolute;background:var(--bg, #1e1e2e);border:1px solid var(--accent, #89b4fa);border-radius:8px;padding:0;font-size:11px;color:var(--text, #cdd6f4);max-width:350px;min-width:220px;word-wrap:break-word;box-shadow:0 2px 12px rgba(0,0,0,.4);z-index:50;user-select:none;resize:both;overflow:hidden;backdrop-filter:blur(8px)}
.qa-bubble .qa-drag{padding:6px 10px 4px;cursor:grab;background:rgba(137,180,250,0.08);border-bottom:1px solid var(--border, #3a3a5e);font-size:9px;color:var(--text-dim, #7f849c);letter-spacing:0.5px;display:flex;align-items:center;gap:6px}
.qa-bubble .qa-drag::before{content:'⋮⋮';font-size:12px}
.qa-bubble .qa-content{padding:8px 12px}
.qa-bubble .qa-close{position:absolute;top:5px;right:8px;cursor:pointer;color:var(--text-dim, #7f849c);font-size:10px;z-index:5;width:18px;height:18px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:var(--surface, #2a2a3e);border:1px solid var(--border, #3a3a5e);transition:all 0.15s}
.qa-bubble .qa-close:hover{color:var(--red, #f38ba8);background:rgba(243,139,168,0.15);border-color:var(--red, #f38ba8)}
.qa-bubble .qa-thread{max-height:200px;overflow-y:auto;margin-bottom:6px;cursor:default;user-select:text;scroll-behavior:smooth}
.qa-bubble .qa-msg{padding:4px 0;border-bottom:1px solid var(--border, #3a3a5e)}
.qa-bubble .qa-msg:last-child{border-bottom:none}
.qa-bubble .qa-msg.user{color:var(--accent, #89b4fa)}
.qa-bubble .qa-msg.agent{color:var(--green, #a6e3a1)}
.qa-bubble .qa-msg.pending{color:var(--yellow, #f9e2af);font-style:italic}
.qa-bubble .qa-msg .qa-role{font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px;display:block}
.qa-bubble .qa-msg.pending .typing-dots{display:inline-block}
.qa-bubble .qa-msg.pending .typing-dots span{display:inline-block;width:4px;height:4px;border-radius:50%;background:var(--yellow, #f9e2af);margin:0 1px;opacity:0.4;animation:typing-wave 1.4s ease-in-out infinite}
.qa-bubble .qa-msg.pending .typing-dots span:nth-child(2){animation-delay:0.2s}
.qa-bubble .qa-msg.pending .typing-dots span:nth-child(3){animation-delay:0.4s}
@keyframes typing-wave{0%,100%{opacity:0.4}50%{opacity:1}}
.qa-bubble .qa-reply-bar{display:flex;gap:4px;margin-top:6px;cursor:default;align-items:flex-end}
.qa-bubble .qa-reply-bar textarea{flex:1;box-sizing:border-box;min-height:52px;max-height:${QA_INPUT_MAX_PX}px;overflow-y:auto;resize:none;background:var(--surface, #2a2a3e);border:1px solid var(--border, #3a3a5e);border-radius:3px;padding:4px 6px;font:11px/1.3 'JetBrains Mono',ui-monospace,monospace;color:var(--text, #cdd6f4);outline:none}
.qa-bubble .qa-reply-bar textarea:focus{border-color:var(--accent, #89b4fa)}
.qa-bubble .qa-reply-bar button{padding:3px 8px;font-size:10px;cursor:pointer;border:1px solid var(--border, #3a3a5e);border-radius:3px;background:var(--accent, #89b4fa);color:var(--bg, #1e1e2e);font-weight:600}
`;

class QABubble {
  constructor(container, opts = {}) {
    this.container = container;
    this.context = opts.context || 'unknown';
    this.position = opts.position || { x: 100, y: 100 };
    this.onQuestion = opts.onQuestion || (async () => {});
    this.pollAnswers = opts.pollAnswers || (async () => null);
    this.onClose = opts.onClose || (() => {});
    this.thread = [];
    this.pollTimer = null;
    this.serverIdx = null;

    this._injectStyles();
    this._build();
    this._bindDrag();
  }

  _injectStyles() {
    if (!document.getElementById('qa-bubble-styles')) {
      const s = document.createElement('style');
      s.id = 'qa-bubble-styles';
      s.textContent = QA_BUBBLE_CSS;
      document.head.appendChild(s);
    }
  }

  _build() {
    this.el = document.createElement('div');
    this.el.className = 'qa-bubble';
    this.el.style.left = this.position.x + 'px';
    this.el.style.top = this.position.y + 'px';
    this.el.innerHTML = `
      <div class="qa-drag">Q&A · <span style="opacity:0.6">${this._escHtml(this.context)}</span><span class="qa-close">✕</span></div>
      <div class="qa-content">
        <div class="qa-thread"></div>
        <div class="qa-reply-bar">
          <textarea rows="3" placeholder="Ask or follow up..."></textarea>
          <button>→</button>
        </div>
      </div>
    `;
    this.container.appendChild(this.el);

    this.threadEl = this.el.querySelector('.qa-thread');
    this.input = this.el.querySelector('.qa-reply-bar textarea');
    this.sendBtn = this.el.querySelector('.qa-reply-bar button');

    this.el.querySelector('.qa-close').onclick = () => this.destroy();
    this.sendBtn.onclick = () => this._send();
    this.input.oninput = () => this._autosize();
    this.input.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); }
    };
    this._autosize();
  }

  _autosize() {
    const ta = this.input;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, QA_INPUT_MAX_PX) + 'px';
  }

  _bindDrag() {
    const handle = this.el.querySelector('.qa-drag');
    let dragging = false, startX, startY, origX, origY;
    handle.onmousedown = (e) => {
      if (e.target.classList.contains('qa-close')) return;
      dragging = true;
      startX = e.clientX; startY = e.clientY;
      origX = this.el.offsetLeft; origY = this.el.offsetTop;
      e.preventDefault();
    };
    document.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      this.el.style.left = (origX + e.clientX - startX) + 'px';
      this.el.style.top = (origY + e.clientY - startY) + 'px';
    });
    document.addEventListener('mouseup', () => { dragging = false; });
  }

  async _send() {
    const text = this.input.value.trim();
    if (!text) return;
    this.input.value = '';
    this._autosize();

    this.appendUserMessage(text);
    this._appendPending();

    this.sendBtn.textContent = '…';
    this.sendBtn.disabled = true;

    try {
      const result = await this.onQuestion(text, this.context, this.thread);
      this.sendBtn.textContent = '✓';
      setTimeout(() => { this.sendBtn.textContent = '→'; this.sendBtn.disabled = false; }, 1000);
      if (result && result.serverIdx !== undefined) {
        this.serverIdx = result.serverIdx;
        this._startPolling();
      }
    } catch(e) {
      this.sendBtn.textContent = '✕';
      this.sendBtn.disabled = false;
      setTimeout(() => { this.sendBtn.textContent = '→'; }, 2000);
      const pending = this.threadEl.querySelector('.qa-msg.pending');
      if (pending) pending.innerHTML = '<span class="qa-role" style="color:var(--red,#f38ba8)">Error</span>Failed to send — click → to retry';
    }
  }

  appendUserMessage(text) {
    this.thread.push({ role: 'user', text });
    this.threadEl.insertAdjacentHTML('beforeend',
      `<div class="qa-msg user"><span class="qa-role">You</span>${this._escHtml(text)}</div>`
    );
    this._scrollThread();
  }

  appendAgentMessage(text) {
    this.thread.push({ role: 'agent', text });
    const pending = this.threadEl.querySelector('.qa-msg.pending');
    if (pending) pending.remove();
    this.threadEl.insertAdjacentHTML('beforeend',
      `<div class="qa-msg agent"><span class="qa-role">Agent</span>${this._escHtml(text)}</div>`
    );
    this._scrollThread();
  }

  _appendPending() {
    this.threadEl.insertAdjacentHTML('beforeend',
      `<div class="qa-msg pending"><span class="typing-dots"><span></span><span></span><span></span></span></div>`
    );
    this._scrollThread();
  }

  _startPolling() {
    if (this.pollTimer) clearTimeout(this.pollTimer);
    const POLL_INTERVAL = 2000;
    const RELAY_HINT_AFTER = 15000;   // tell the user the question routed to the session agent
    const MAX_POLL_TIME = 600000;     // the agent may be mid-task; keep listening for 10 min
    const startTime = Date.now();
    let hintShown = false;

    const poll = async () => {
      const answer = await this.pollAnswers(this.serverIdx);
      if (answer) {
        this.appendAgentMessage(answer);
        return;
      }
      const elapsed = Date.now() - startTime;
      if (!hintShown && elapsed > RELAY_HINT_AFTER) {
        hintShown = true;
        const pending = this.threadEl.querySelector('.qa-msg.pending');
        if (pending) {
          pending.insertAdjacentHTML('beforeend',
            '<div style="margin-top:3px;color:var(--text-dim,#7f849c);font-style:normal">Routed to your Claude Code session — the agent replies here when it picks it up.</div>');
        }
      }
      if (elapsed > MAX_POLL_TIME) {
        const pending = this.threadEl.querySelector('.qa-msg.pending');
        if (pending) {
          pending.className = 'qa-msg agent';
          pending.innerHTML = '<span class="qa-role" style="color:var(--text-dim)">System</span>No reply yet — in your Claude Code session run <code>schematic questions</code>, then <code>schematic answer &lt;id&gt; "..."</code>.';
        }
        return;
      }
      this.pollTimer = setTimeout(poll, POLL_INTERVAL);
    };
    this.pollTimer = setTimeout(poll, POLL_INTERVAL);
  }

  _scrollThread() {
    requestAnimationFrame(() => { this.threadEl.scrollTop = this.threadEl.scrollHeight; });
  }

  _escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  destroy() {
    if (this.pollTimer) clearTimeout(this.pollTimer);
    this.el.style.transition = 'transform 0.2s ease-in, opacity 0.2s ease-in';
    this.el.style.transform = 'scale(0.9)';
    this.el.style.opacity = '0';
    setTimeout(() => { this.el.remove(); }, 200);
    this.onClose();
  }
}

/**
 * NoteBubble — Shared note input bubble for right-click "Add note" on all screens.
 *
 * Usage:
 *   new NoteBubble(container, {
 *     context: "diagram:sequence.mmd",
 *     position: { x, y },
 *     onSave: async (text, context) => { POST to server },
 *     positioning: "absolute" | "fixed",  // default "absolute"
 *   });
 */
class NoteBubble {
  constructor(container, opts = {}) {
    this.container = container;
    this.context = opts.context || 'unknown';
    this.position = opts.position || { x: 100, y: 100 };
    this.onSave = opts.onSave || (async () => {});
    this.onClose = opts.onClose || (() => {});
    this.positioning = opts.positioning || 'absolute';

    this._injectStyles();
    this._build();
  }

  _injectStyles() {
    if (!document.getElementById('qa-bubble-styles')) {
      const s = document.createElement('style');
      s.id = 'qa-bubble-styles';
      s.textContent = QA_BUBBLE_CSS;
      document.head.appendChild(s);
    }
  }

  _build() {
    this.el = document.createElement('div');
    this.el.className = 'qa-bubble';
    this.el.style.position = this.positioning;
    this.el.style.left = this.position.x + 'px';
    this.el.style.top = this.position.y + 'px';
    this.el.innerHTML = `
      <div class="qa-drag">📌 Note · <span style="opacity:0.6">${this._escHtml(this.context)}</span><span class="qa-close">✕</span></div>
      <div class="qa-content">
        <textarea style="width:100%;height:60px;font:11px/1.4 'JetBrains Mono',monospace;background:var(--bg,#1e1e2e);color:var(--text,#cdd6f4);border:1px solid var(--border,#3a3a5e);border-radius:3px;padding:6px;resize:vertical;outline:none" placeholder="Leave a note..."></textarea>
        <div class="qa-reply-bar" style="margin-top:6px">
          <button class="primary" style="padding:3px 10px;font-size:10px;cursor:pointer;border:1px solid var(--accent,#89b4fa);border-radius:3px;background:var(--accent,#89b4fa);color:var(--bg,#1e1e2e);font-weight:600">Save</button>
          <button style="padding:3px 8px;font-size:10px;cursor:pointer;border:1px solid var(--border,#3a3a5e);border-radius:3px;background:var(--surface,#2a2a3e);color:var(--text,#cdd6f4)">Cancel</button>
        </div>
      </div>
    `;
    this.container.appendChild(this.el);

    const ta = this.el.querySelector('textarea');
    setTimeout(() => ta.focus(), 50);

    this.el.querySelector('.qa-close').onclick = () => this.destroy();
    this.el.querySelector('button:last-child').onclick = () => this.destroy();
    this.el.querySelector('button.primary').onclick = async () => {
      const text = ta.value.trim();
      if (!text) return;
      await this.onSave(text, this.context);
      this.destroy();
    };
    ta.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); this.el.querySelector('button.primary').click(); }
      if (ev.key === 'Escape') this.destroy();
    });
  }

  _escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  destroy() {
    this.el.style.transition = 'transform 0.2s ease-in, opacity 0.2s ease-in';
    this.el.style.transform = 'scale(0.9)';
    this.el.style.opacity = '0';
    setTimeout(() => { this.el.remove(); }, 200);
    this.onClose();
  }
}

if (typeof module !== 'undefined') module.exports = { QABubble, NoteBubble };

// Reconnecting WebSocket with exponential backoff + jitter.
// onOpen(isReconnect) lets the app resync state after a dropped connection.

export function wsUrl(path) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${path}`;
}

export class ReconnectingSocket {
  constructor(path, { onMessage, onStatus, onOpen, maxDelay = 30_000, parseJson = true } = {}) {
    this.path = path;
    this.onMessage = onMessage || (() => {});
    this.onStatus = onStatus || (() => {});
    this.onOpen = onOpen || (() => {});
    this.maxDelay = maxDelay;
    this.parseJson = parseJson;
    this.attempt = 0;
    this.everOpened = false;
    this.closed = false;
    this.ws = null;
    this.timer = null;
  }

  connect() {
    if (this.closed || this.ws) return;
    this.onStatus(this.everOpened ? 'reconnecting' : 'connecting');
    let ws;
    try {
      ws = new WebSocket(wsUrl(this.path));
    } catch {
      this.schedule();
      return;
    }
    this.ws = ws;
    ws.onopen = () => {
      if (this.ws !== ws) return;
      const isReconnect = this.everOpened;
      this.everOpened = true;
      this.attempt = 0;
      this.onStatus('open');
      this.onOpen(isReconnect);
    };
    ws.onmessage = (ev) => {
      if (this.ws !== ws || typeof ev.data !== 'string') return;
      if (!this.parseJson) { this.onMessage(ev.data); return; }
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg && typeof msg === 'object') this.onMessage(msg);
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      if (this.closed) return;
      this.onStatus('reconnecting');
      this.schedule();
    };
    ws.onerror = () => { /* close event follows */ };
  }

  schedule() {
    if (this.closed) return;
    clearTimeout(this.timer);
    const base = Math.min(this.maxDelay, 1000 * 2 ** this.attempt);
    this.attempt += 1;
    const delay = base / 2 + Math.random() * (base / 2);
    this.timer = setTimeout(() => this.connect(), delay);
  }

  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
      return true;
    }
    return false;
  }

  close() {
    this.closed = true;
    clearTimeout(this.timer);
    const ws = this.ws;
    this.ws = null;
    if (ws) {
      try { ws.close(); } catch { /* ignore */ }
    }
    this.onStatus('closed');
  }
}

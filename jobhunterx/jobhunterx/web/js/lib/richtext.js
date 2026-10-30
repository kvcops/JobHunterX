// Inline formatting inside document text — the same rules as jobhunterx/generation/richtext.py (the PDF side):
//   **bold**   *italic*   [label](https://link)   \* \[ \] \\ for the literal characters
// toHtml() escapes everything first and only makes http(s)/mailto links clickable; fromElement() turns what the user
// edited on the page (contenteditable: <b>, <i>, <a>, browser spans) back into that text.

const ESC_RE = /\\([\\*[\]])/g;
const LINK_RE = /\[([^[\]]+)\]\(([^()\s]+)\)/g;
const BOLD_RE = /\*\*(.+?)\*\*/g;
const ITALIC_RE = /\*([^*]+?)\*/g;
const SAFE_URL = /^(https?:\/\/|mailto:)/i;

const escHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&#34;').replace(/'/g, '&#39;');
const hide = (s) => s.replace(ESC_RE, (_, c) => `\u0000${c.charCodeAt(0)}\u0001`);
const show = (s) => s.replace(/\u0000(\d+)\u0001/g, (_, n) => String.fromCharCode(Number(n)));

export function safeLink(url) {
  const u = String(url || '').trim();
  return SAFE_URL.test(u) ? u : '';
}

/** Escaped HTML with <b>, <i> and safe <a> (open in a new tab) for one stored string. */
export function toHtml(text) {
  let s = hide(escHtml(String(text ?? '')));
  s = s.replace(LINK_RE, (_, label, url) => {
    const raw = url.replace(/&amp;/g, '&');
    return SAFE_URL.test(raw) ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>` : label;
  });
  s = s.replace(BOLD_RE, '<b>$1</b>').replace(ITALIC_RE, '<i>$1</i>');
  return show(s);
}

/** The words without the markers. */
export function plain(text) {
  return show(hide(String(text ?? '')).replace(LINK_RE, '$1').replace(BOLD_RE, '$1').replace(ITALIC_RE, '$1'));
}

const escMark = (s) => s.replace(/[\\*[\]]/g, (c) => `\\${c}`);

function walk(node, ctx) {
  if (node.nodeType === 3) return escMark(node.nodeValue.replace(/ /g, ' '));
  if (node.nodeType !== 1) return '';
  const tag = node.tagName;
  if (tag === 'BR') return ' ';
  const st = node.style || {};
  const bold = tag === 'B' || tag === 'STRONG' || Number(st.fontWeight) >= 600 || st.fontWeight === 'bold';
  const italic = tag === 'I' || tag === 'EM' || st.fontStyle === 'italic';
  const href = tag === 'A' ? safeLink(node.getAttribute('href')) : '';
  let inner = Array.from(node.childNodes).map((c) => walk(c, {
    bold: ctx.bold || bold, italic: ctx.italic || italic, link: ctx.link || !!href,
  })).join('');
  if (!inner.trim()) return inner;
  // a marker opened inside the same marker would close it early: nested bold-in-bold is just bold
  if (italic && !ctx.italic) inner = wrap(inner, '*');
  if (bold && !ctx.bold) inner = wrap(inner, '**');
  if (href && !ctx.link) inner = `[${inner}](${href.replace(/[()\s]/g, encodeURIComponent)})`;
  if ((tag === 'DIV' || tag === 'P') && ctx.top) inner = ` ${inner}`;
  return inner;
}

// keep the spaces outside the markers ("** word**" is not bold)
function wrap(s, m) {
  const lead = s.match(/^\s*/)[0];
  const trail = s.match(/\s*$/)[0];
  return `${lead}${m}${s.trim()}${m}${trail}`;
}

/** What the user typed into a contenteditable element, as stored text (one line, markers for formatting). */
export function fromElement(el) {
  const text = Array.from(el.childNodes).map((c) => walk(c, { top: true })).join('');
  return text.replace(/\s+/g, ' ').replace(/\*\*\*\*/g, '').trim();
}

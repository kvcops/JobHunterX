// A windowed list: only the rows near the viewport exist in the page, so a list of thousands scrolls like a list of ten.
// Rows can have any height; each is measured once it renders (until then an estimate is used), and when a row above
// the viewport changes height the scroll position is corrected so nothing on screen jumps.
import { html, useEffect, useLayoutEffect, useRef, useState } from '../lib/preact.js';

/** Index of the first row whose bottom edge is at or below y (binary search over the row tops). */
function firstBelow(tops, heights, y) {
  let lo = 0, hi = tops.length - 1, ans = tops.length;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (tops[mid] + heights[mid] >= y) { ans = mid; hi = mid - 1; } else lo = mid + 1;
  }
  return ans;
}

/** One positioned row; measured while it is on screen, forgotten by the observer when it leaves. */
function VRow({ vkey, top, observer, children }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const node = ref.current;
    observer.observe(node);
    return () => observer.unobserve(node);
  }, [observer]);
  return html`<div ref=${ref} class="vrow" data-vkey=${vkey} style=${{ transform: `translateY(${top}px)` }}>${children}</div>`;
}

/**
 * items: the data; itemKey(item) → stable key; renderItem(item, index) → vnode.
 * before / after: content above and below the rows inside the same scroller (empty states, a footer).
 * onNearEnd(): called when the last rows come into view (load the next page).
 */
export function VirtualList({ items, itemKey, renderItem, estimate = 180, gap = 10, overscan = 900,
  className = '', before = null, after = null, onNearEnd = null, ...rest }) {
  const scroller = useRef(null);
  const body = useRef(null);
  const sizes = useRef(new Map());              // key → measured height
  const layout = useRef({ keys: [], tops: [], heights: [] });
  const frame = useRef(0);
  const [view, setView] = useState({ top: 0, height: 800, offset: 0 });   // read together in one animation frame
  const [, setVersion] = useState(0);
  const observer = useRef(null);
  if (!observer.current) {
    observer.current = new ResizeObserver((entries) => {
      const el = scroller.current;
      const anchor = el ? el.scrollTop - (body.current ? body.current.offsetTop : 0) : 0;
      const { keys: ks, tops: ts } = layout.current;
      let changed = false, shift = 0;
      for (const e of entries) {
        const k = e.target.dataset.vkey;
        const hgt = e.borderBoxSize && e.borderBoxSize[0] ? e.borderBoxSize[0].blockSize : e.target.offsetHeight;
        if (k == null || !hgt) continue;
        const prev = sizes.current.get(k) ?? estimate;
        if (sizes.current.get(k) === hgt) continue;
        const idx = ks.indexOf(k);
        // a row above what you are looking at grew or shrank: move the scroll by the same amount
        if (idx >= 0 && ts[idx] + prev <= anchor) shift += hgt - prev;
        sizes.current.set(k, hgt);
        changed = true;
      }
      if (shift && el) el.scrollTop += shift;
      if (changed) setVersion((v) => v + 1);
    });
  }

  // row tops from measured / estimated heights
  const keys = items.map(itemKey);
  const heights = keys.map((k) => sizes.current.get(k) ?? estimate);
  const tops = new Array(keys.length);
  let y = 0;
  for (let i = 0; i < keys.length; i++) { tops[i] = y; y += heights[i] + gap; }
  const total = Math.max(0, y - gap);
  layout.current = { keys, tops, heights };

  const from = view.top - view.offset - overscan, to = view.top - view.offset + view.height + overscan;
  const start = Math.max(0, firstBelow(tops, heights, from));
  let end = start;
  while (end < keys.length && tops[end] <= to) end++;

  useLayoutEffect(() => {
    const el = scroller.current;
    const sync = () => {
      frame.current = 0;
      const el2 = scroller.current;
      if (!el2) return;
      const next = { top: el2.scrollTop, height: el2.clientHeight, offset: body.current ? body.current.offsetTop : 0 };
      setView((v) => (v.top === next.top && v.height === next.height && v.offset === next.offset ? v : next));
    };
    const onScroll = () => { if (!frame.current) frame.current = requestAnimationFrame(sync); };
    const box = new ResizeObserver(onScroll);
    box.observe(el);
    el.addEventListener('scroll', onScroll, { passive: true });
    sync();
    return () => { observer.current.disconnect(); box.disconnect(); el.removeEventListener('scroll', onScroll); cancelAnimationFrame(frame.current); };
  }, []);

  // forget the sizes of rows that left the list, so the map never grows without bound
  useEffect(() => {
    if (sizes.current.size > keys.length * 2 + 200) {
      const live = new Set(keys);
      for (const k of sizes.current.keys()) if (!live.has(k)) sizes.current.delete(k);
    }
  });

  useEffect(() => {
    if (onNearEnd && keys.length && end >= keys.length - 4) onNearEnd();
  }, [end, keys.length]);

  const rows = [];
  for (let i = start; i < end; i++) {
    rows.push(html`<${VRow} key=${keys[i]} vkey=${keys[i]} top=${tops[i]} observer=${observer.current}>${renderItem(items[i], i)}</${VRow}>`);
  }
  return html`<div class=${`scroll vscroll ${className}`} ref=${scroller} ...${rest}>
    ${before}
    <div class="vbody" ref=${body} style=${{ height: `${total}px` }}>${rows}</div>
    ${after}
  </div>`;
}

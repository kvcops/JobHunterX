// Country, city and work-authorization fields: editable dropdowns (type anything, or pick a suggestion).
// Country names come from the browser itself (Intl.DisplayNames), so there is no hand-made list to keep up to date.
// Cities are suggested while typing, from the server's /api/places (Open-Meteo geocoder).
import { html, useEffect, useRef, useState } from '../lib/preact.js';
import { api } from '../lib/api.js';
import { ChipsInput, ComboInput } from './ui.js';

export const DEFAULT_COUNTRY = 'India';
// Region codes that are not countries (EU, UN, "unknown", private-use ranges, a few logistics territories).
const NOT_COUNTRIES = new Set(['EU', 'EZ', 'UN', 'QO', 'XA', 'XB', 'ZZ', 'AC', 'CP', 'DG', 'EA', 'IC', 'TA', 'CQ']);
let cache = null;

/** Every country the browser knows, as [{ code, name }] sorted by name. */
export function countries() {
  if (cache) return cache;
  const byName = new Map();
  try {
    const dn = new Intl.DisplayNames(['en'], { type: 'region', fallback: 'none' });
    for (let a = 65; a <= 90; a += 1) {
      for (let b = 65; b <= 90; b += 1) {
        const code = String.fromCharCode(a, b);
        if (NOT_COUNTRIES.has(code)) continue;
        let name;
        try { name = dn.of(code); } catch { name = undefined; }
        if (name && name !== code && !byName.has(name)) byName.set(name, code);
      }
    }
  } catch { /* very old browser: free typing still works */ }
  if (!byName.size) byName.set(DEFAULT_COUNTRY, 'IN');
  cache = [...byName].map(([name, code]) => ({ code, name })).sort((x, y) => x.name.localeCompare(y.name));
  return cache;
}

export function countryCode(name) {
  const n = String(name || '').trim().toLowerCase();
  const hit = countries().find((c) => c.name.toLowerCase() === n);
  return hit ? hit.code : '';
}

/** Home country: a dropdown of every country you can also type into, India when empty. */
export function CountryInput({ id, value, onChange }) {
  return html`<${ComboInput} id=${id} label="Country" autocomplete="country-name" value=${value || DEFAULT_COUNTRY}
    options=${countries().map((c) => c.name)} onChange=${onChange}
    onBlur=${(e) => { if (!e.currentTarget.value.trim()) onChange(DEFAULT_COUNTRY); }} />`;
}

/** Cities matching what is typed (debounced; the newest answer wins). */
function useCitySearch(text, country) {
  const [places, setPlaces] = useState([]);
  const seq = useRef(0);
  useEffect(() => {
    const q = String(text || '').split(',')[0].trim();
    if (q.length < 2) { setPlaces([]); return undefined; }
    const mine = ++seq.current;
    const t = setTimeout(() => {
      api.places(q, countryCode(country)).then((r) => { if (mine === seq.current) setPlaces(r.places || []); }).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [text, country]);
  return places;
}

/** One place ("Hyderabad, Telangana, India"), with city suggestions while typing. */
export function CityInput({ id, value, onChange, country, placeholder, extra = [] }) {
  const places = useCitySearch(value, country);
  const options = [...new Set([...places.map((p) => p.label), ...extra.filter(Boolean)])];
  return html`<${ComboInput} id=${id} label="City" autocomplete="address-level2" value=${value || ''} placeholder=${placeholder}
    options=${options} onChange=${onChange} />`;
}

/** Several cities as chips; suggestions follow what is being typed. */
export function CityChips({ value, onChange, label, placeholder, country, extra = [] }) {
  const [typing, setTyping] = useState('');
  const places = useCitySearch(typing, country);
  const suggestions = typing.trim().length >= 2 ? places.map((p) => p.name) : extra;
  return html`<${ChipsInput} label=${label} value=${value} onChange=${(v) => { setTyping(''); onChange(v); }} placeholder=${placeholder}
    suggestions=${suggestions} onQuery=${setTyping} />`;
}

/** Work authorization: an editable dropdown — status in the home country first, then citizenship of any country. */
export function WorkAuthInput({ id, value, onChange, country }) {
  const home = (country || '').trim() || DEFAULT_COUNTRY;
  const options = [`Citizen of ${home}`, `Permanent resident of ${home}`, `Work visa / permit for ${home}`, `Student visa in ${home}`,
    'Need visa sponsorship', ...countries().filter((c) => c.name !== home).map((c) => `Citizen of ${c.name}`)];
  return html`<${ComboInput} id=${id} label="Work authorization" value=${value || ''} placeholder=${`e.g. Citizen of ${home}`}
    options=${options} onChange=${onChange} />`;
}

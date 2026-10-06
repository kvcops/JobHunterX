// Single import point for the vendored Preact runtime + htm tagged templates.
// htm escapes all interpolated values: never build markup from strings.
import { h, render, Fragment, createContext, Component } from '../../vendor/preact.module.js';
import htm from '../../vendor/htm.module.js';

export { h, render, Fragment, createContext };
export {
  useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback, useReducer, useId, useContext,
} from '../../vendor/hooks.module.js';

export const html = htm.bind(h);

const shallowEqual = (a, b) => {
  for (const k in a) if (a[k] !== b[k]) return false;
  for (const k in b) if (!(k in a)) return false;
  return true;
};

/** Like preact/compat's memo: the component re-renders only when a prop changes (its own hooks still update it). */
export function memo(fn, equal = shallowEqual) {
  class Memo extends Component {
    shouldComponentUpdate(next) { return !equal(this.props, next); }
    render(props) { return h(fn, props); }
  }
  Memo.displayName = `memo(${fn.displayName || fn.name})`;
  return Memo;
}

// Single import point for the vendored Preact runtime + htm tagged templates.
// htm escapes all interpolated values: never build markup from strings.
import { h, render, Fragment, createContext } from '../../vendor/preact.module.js';
import htm from '../../vendor/htm.module.js';

export { h, render, Fragment, createContext };
export {
  useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback, useReducer, useId, useContext,
} from '../../vendor/hooks.module.js';

export const html = htm.bind(h);

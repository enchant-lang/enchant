// Small native SVG vocabulary. Geometry stays independent of editor policy.
const paths = {
  plus: 'M12 5v14M5 12h14', minus: 'M5 12h14', close: 'm6 6 12 12M18 6 6 18',
  check: 'm5 12 4 4L19 6', 'check-square': 'M9 11l3 3 8-8M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10',
  text: 'M4 6h16M12 6v14M8 20h8', heading: 'M5 4v16M19 4v16M5 12h14',
  bold: 'M6 4h7a4 4 0 0 1 0 8H6m0 0h8a4 4 0 0 1 0 8H6V4',
  italic: 'M10 4h10M4 20h10M15 4 9 20', underline: 'M6 3v7a6 6 0 0 0 12 0V3M4 21h16',
  strike: 'M18 5c-2-2-9-3-11 1-2 4 3 5 5 6s7 2 5 6-9 3-11 1M3 12h18',
  highlighter: 'm9 11 7-7 4 4-7 7-4-4Zm0 0-3 3 4 4 3-3M4 20l3-3',
  link: 'm10 13 4-4m-6 6-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m0 2 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0',
  code: 'm8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  'list-ordered': 'M9 6h12M9 12h12M9 18h12M3 4h1v5M3 14c3-2 4 1 1 3l-1 2h3',
  quote: 'M3 5h7v8H7c0 3-1 5-4 6m11-14h7v8h-3c0 3-1 5-4 6',
  lightbulb: 'M9 18h6M10 21h4M8 14a6 6 0 1 1 8 0l-1 3H9l-1-3Z',
  sparkles: 'm12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Zm7 0v4m-2-2h4',
  leaf: 'M20 3C5 2 1 10 7 17s15 0 13-14ZM5 21 16 9',
  sun: 'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  moon: 'M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z',
  heart: 'M20 5c-3-3-7-1-8 1-1-2-5-4-8-1-4 4 0 8 8 15 8-7 12-11 8-15Z',
  bookmark: 'M6 3h12v18l-6-4-6 4V3Z', flag: 'M5 22V3m0 1c5-4 9 4 14 0v9c-5 4-9-4-14 0',
  image: 'M3 3h18v18H3V3Zm0 13 6-6 12 11m-6-6 3-3 3 3M16 7h.01',
  grip: 'M8 5h.01M16 5h.01M8 12h.01M16 12h.01M8 19h.01M16 19h.01',
  undo: 'M3 10h10a7 7 0 0 1 0 14M3 10l5-5m-5 5 5 5',
  redo: 'M21 10H11a7 7 0 0 0 0 14m10-14-5-5m5 5-5 5',
  copy: 'M8 8h13v13H8V8ZM16 8V3H3v13h5',
  trash: 'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7',
  indent: 'M11 5h10M11 12h10M11 19h10M3 8l4 4-4 4',
  outdent: 'M11 5h10M11 12h10M11 19h10M7 8l-4 4 4 4',
  'arrow-up': 'M12 20V4m-6 6 6-6 6 6', 'arrow-down': 'M12 4v16m-6-6 6 6 6-6',
  'chevron-down': 'm6 9 6 6 6-6', 'chevron-right': 'm9 6 6 6-6 6',
  search: 'M20 20l-5-5m2-6a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z',
  download: 'M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  function: 'M17 3h-3c-2 0-3 2-3 4l-2 10c0 2-1 4-3 4H4m2-12h12',
  case: 'm3 19 6-14 6 14M5 15h8m5-6h4m0 0v10m0-5c-7-3-7 7 0 4',
  circle: 'M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
};
export const iconNames = ['sparkles','lightbulb','leaf','sun','moon','heart','bookmark','flag','code','quote','check-square','circle'];
export function icon(name, className = '') {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key,value] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.65','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false',class:'ed-icon '+className})) svg.setAttribute(key,value);
  const path = document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[name] || paths.function);svg.append(path);return svg;
}
export function hydrateIcons(root) {
  for (const el of root.querySelectorAll('[data-icon]')) if (!el.firstElementChild) el.append(icon(el.dataset.icon));
}

/* Lucide icons (ISC), vendored in icons.svg. See LICENSE.icons.txt. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
function icon(name) {
  return `<svg class="icon" aria-hidden="true" focusable="false"><use href="./icons.svg#${name}"></use></svg>`;
}
function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(element => {
    element.innerHTML = icon(element.dataset.icon);
  });
}

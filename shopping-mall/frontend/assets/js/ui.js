export const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = value => Number.isSafeInteger(Number(value)) ? `${new Intl.NumberFormat('ko-KR').format(Number(value))}원` : '금액 확인 필요';
export const date = value => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', dateStyle: 'medium' }).format(new Date(value));
export const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const assets = { '000000000001': ['shirt', '가벼운 일상 · 패브릭'], '000000000002': ['bag', '어디에나 함께 · 패브릭'], '000000000003': ['mug', '잠깐의 여유 · 드링크웨어'], '000000000004': ['bottle', '나의 페이스대로 · 드링크웨어'], '000000000005': ['notebook', '생각을 담는 시간 · 스테이셔너리'] };
export function meta(product) { return assets[String(product.id).slice(-12)] || ['mug', '일상을 위한 오브젝트']; }
export function imageUrl(product) {
  if (product.image_url) {
    try { const u = new URL(product.image_url, location.origin); if (u.protocol === 'https:' || u.origin === location.origin && u.protocol === location.protocol) return u.href; } catch { /* use local artwork */ }
  }
  return `/assets/images/${meta(product)[0]}.svg`;
}
export function productImage(product, className = '') { return `<img class="${h(className)}" src="${h(imageUrl(product))}" alt="${h(product.name)} 상품 이미지" loading="lazy" data-product-image>`; }
export function safeNext(value) {
  try {
    let decoded = value || '/';
    for (let i = 0; i < 4; i++) decoded = decodeURIComponent(decoded);
    if (/[\\\x00-\x1f\x7f]/.test(decoded) || decoded.startsWith('//')) return '/';
    const url = new URL(decoded, location.origin);
    if (url.origin !== location.origin || url.hash || !/^\/(?:|cart|checkout|mypage(?:\/edit|\/orders(?:\/[0-9a-f-]{36})?)?|products\/[0-9a-f-]{36})$/i.test(url.pathname)) return '/';
    return value || '/';
  } catch { return '/'; }
}
export function storageGet(key) { try { return JSON.parse(sessionStorage.getItem(`orbit.${key}`)); } catch { return null; } }
export function storageSet(key, value) { sessionStorage.setItem(`orbit.${key}`, JSON.stringify(value)); }
export function storageRemove(key) { sessionStorage.removeItem(`orbit.${key}`); }
export function flash(message) { try { storageSet('flash', message); } catch { /* navigation remains usable */ } }
let noticeTimer;
export function notify(message) {
  const node = document.querySelector('#notice');
  node.textContent = message; node.hidden = false;
  clearTimeout(noticeTimer); noticeTimer = setTimeout(() => { node.hidden = true; }, 6500);
}
export function showError(error, target = document.querySelector('#page-error')) {
  if (!target) return notify(error.message || '다시 시도해 주세요.');
  target.textContent = error.message || '요청을 처리할 수 없습니다.';
  if (error.details?.length) target.textContent += ` ${error.details.map(d => d.message).join(' ')}`;
  target.hidden = false; target.tabIndex = -1; target.focus();
}
export async function busy(button, action, onError = showError) {
  if (button.disabled) return;
  const original = button.textContent;
  const focused = document.activeElement;
  document.querySelector('#page-error')?.setAttribute('hidden', '');
  button.disabled = true; button.textContent = '처리 중…'; button.setAttribute('aria-busy', 'true');
  try { await action(); } catch (error) { onError(error); }
  finally { button.disabled = false; button.textContent = original; button.removeAttribute('aria-busy'); if (focused === button && button.isConnected && document.activeElement === document.body) button.focus(); }
}
export function quantity(value = 1, max = 999, id = 'quantity') {
  return `<div class="quantity"><button type="button" data-quantity="-1" aria-label="수량 줄이기">−</button><input id="${h(id)}" name="quantity" type="number" min="1" max="${max}" step="1" value="${value}" inputmode="numeric" aria-label="상품 수량"><button type="button" data-quantity="1" aria-label="수량 늘리기">+</button></div>`;
}
export function bindQuantities(root = document, change = () => {}) {
  root.querySelectorAll('.quantity').forEach(group => {
    const input = group.querySelector('input');
    const update = (emit = true) => {
      group.querySelector('[data-quantity="-1"]').disabled = Number(input.value) <= 1;
      group.querySelector('[data-quantity="1"]').disabled = Number(input.value) >= Number(input.max);
      if (emit) change(input);
    };
    group.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      input.value = Math.max(1, Math.min(Number(input.max), Number(input.value || 1) + Number(button.dataset.quantity)));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }));
    input.addEventListener('change', () => update()); update(false);
  });
}
export function errorRegion() { return '<p id="page-error" class="error" role="alert" hidden></p>'; }
export function empty(title, description, link = '/', label = '상품 둘러보기') { return `<section class="empty"><span class="empty-symbol" aria-hidden="true">◌</span><h2>${h(title)}</h2><p>${h(description)}</p><a class="btn primary" href="${h(link)}">${h(label)}</a></section>`; }
export function intro(kicker, title, description = '') { return `<header class="page-intro"><p class="eyebrow">${h(kicker)}</p><h1>${h(title)}</h1>${description ? `<p class="muted">${h(description)}</p>` : ''}</header>`; }
export function newId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16)); bytes[6] = bytes[6] & 15 | 64; bytes[8] = bytes[8] & 63 | 128;
  const hex = [...bytes].map(n => n.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

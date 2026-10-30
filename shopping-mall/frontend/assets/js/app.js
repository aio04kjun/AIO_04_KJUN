import { api, ApiError } from './api.js';
import { h, money, date, uuidPattern, meta, productImage, safeNext, storageGet, storageSet, storageRemove, flash, notify, showError, busy, quantity, bindQuantities, errorRegion, empty, intro, newId } from './ui.js';

const main = document.querySelector('#main');
const params = new URLSearchParams(location.search);
const path = location.pathname;
const state = { user: null, config: {}, authKnown: false };
const currentPath = () => location.pathname + location.search;
const loginUrl = next => `/login?${new URLSearchParams({ next: safeNext(next) })}`;
const statusLabel = status => ({ paid: '결제 완료', pending: '결제 대기', cancelled: '취소 완료' }[status] || status);
const badge = status => `<span class="badge ${h(status)}">${h(statusLabel(status))}</span>`;

function mount(html, title) { main.innerHTML = html; main.setAttribute('aria-busy', 'false'); document.title = `${title} — ORBIT`; }
function page(html, title) { mount(`<div class="container page">${html}</div>`, title); }
function clearCheckout() { for (const key of ['checkout', 'pending-order', 'intent']) storageRemove(key); }
function actionError(error) {
  if (error.status === 401) { location.assign(loginUrl(currentPath())); return; }
  showError(error);
}
async function loadUser() {
  try { state.user = (await api('/users/me')).data; state.authKnown = true; return state.user; }
  catch (error) { if (error.status === 401) { state.user = null; state.authKnown = true; return null; } throw error; }
}
async function requireUser(next = currentPath(), intent = null) {
  const user = state.authKnown ? state.user : await loadUser();
  if (!user) {
    if (intent) storageSet('intent', { ...intent, at: Date.now() });
    location.assign(loginUrl(next)); return false;
  }
  return true;
}
async function updateCount() {
  const count = document.querySelector('#cart-count');
  if (!state.user) { count.hidden = true; return; }
  try {
    const result = (await api('/cart')).data;
    const total = result.items.reduce((n, row) => n + row.quantity, 0);
    count.textContent = total > 99 ? '99+' : total; count.hidden = total === 0;
  } catch { count.hidden = true; }
}
function updateNav() {
  document.querySelector('#auth-link').hidden = Boolean(state.user);
  document.querySelector('#auth-link').href = loginUrl(path === '/login' || path === '/signup' ? params.get('next') || '/' : currentPath());
  document.querySelector('#logout').hidden = !state.user;
  document.querySelector(`[data-nav="${path.startsWith('/mypage') ? 'mypage' : path === '/cart' || path === '/checkout' ? 'cart' : 'products'}"]`)?.classList.add('active-link');
}

async function home() {
  mount(`<div class="container"><section class="hero"><div class="hero-copy"><p class="eyebrow">A LITTLE SPACE FOR YOUR EVERYDAY</p><h1>일상에<br><span>새로운 궤도를.</span></h1><p>매일 사용하는 물건에, 조금 다른 시선.<br>가볍게 고르고 오래 곁에 두세요.</p><div class="hero-actions"><a class="btn primary" href="#collection">컬렉션 둘러보기 <span aria-hidden="true">↘</span></a><span class="hero-note">작은 물건이 만드는 새로운 일상</span></div></div><div class="hero-art" aria-hidden="true"><img src="/assets/images/hero.svg" alt="" fetchpriority="high"></div></section><div class="benefits"><span>원화 기준의 투명한 가격</span><span>주문 당시 가격 보존</span><span>차분하게 둘러보는 일상</span></div><section id="collection" class="collection"><div class="section-head"><div><p class="eyebrow">THE EVERYDAY COLLECTION</p><h2>당신의 일상에 놓일 것들</h2></div><div class="catalog-tools"><span id="product-count" class="muted">불러오는 중</span><label>정렬 <select id="sort"><option value="default">기본순</option><option value="low">낮은 가격순</option><option value="high">높은 가격순</option></select></label></div></div>${errorRegion()}<div id="products" class="product-grid" aria-live="polite"><p class="muted">상품을 불러오고 있습니다.</p></div><div class="collection-end"><button id="more" class="btn ghost" type="button" hidden>상품 더 보기</button></div></section><section class="editorial"><div><p class="eyebrow">LESS, BUT THOUGHTFUL</p><h2 class="spaced">조용히, 오래.<br>당신의 일상과 함께.</h2></div><p>편안한 티셔츠부터 따뜻한 한 잔을 담는 머그컵까지. 특별한 순간만큼 평범한 하루도 소중하니까요. 오늘의 궤도에 어울리는 물건을 찾아보세요.</p></section></div>`, '일상에 새로운 궤도를');
  let products = [], nextPage = 1;
  const draw = () => {
    const sort = document.querySelector('#sort').value;
    const sorted = [...products].sort((a, b) => sort === 'low' ? a.price - b.price : sort === 'high' ? b.price - a.price : a.id.localeCompare(b.id));
    document.querySelector('#product-count').textContent = `상품 ${products.length}개`;
    document.querySelector('#products').innerHTML = sorted.length ? sorted.map(product => `<article class="product-card"><a href="/products/${h(product.id)}"><div class="product-image">${productImage(product)}${product.stock === 0 ? '<span class="soldout">품절</span>' : ''}</div><h3>${h(product.name)}</h3></a><p class="meta">${h(meta(product)[1])}</p><p class="price">${money(product.price)}</p></article>`).join('') : '<p class="muted">등록된 상품이 없습니다.</p>';
  };
  const load = async () => {
    const response = await api(`/products?page=${nextPage}&page_size=12`, { refreshSession: false });
    products.push(...response.data); nextPage++; draw();
    document.querySelector('#more').hidden = !response.pagination.has_more;
  };
  document.querySelector('#sort').addEventListener('change', draw);
  document.querySelector('#more').addEventListener('click', e => busy(e.currentTarget, load));
  try { await load(); } catch (error) { document.querySelector('#products').innerHTML = ''; showError(error); document.querySelector('#more').hidden = false; document.querySelector('#more').textContent = '다시 불러오기'; }
}

async function productDetail(id) {
  const product = (await api(`/products/${id}`, { refreshSession: false })).data;
  const requested = Number(params.get('quantity') || 1);
  const initial = Number.isInteger(requested) && requested > 0 ? Math.min(requested, product.stock || 1) : 1;
  page(`<div class="breadcrumb"><a href="/#collection">전체 상품</a> / ${h(product.name)}</div><div class="detail-grid"><div><div class="detail-image">${productImage(product)}</div><p class="fineprint">기본 이미지는 상품 이해를 돕기 위한 일러스트입니다.</p></div><section class="detail-info"><p class="eyebrow">${h(meta(product)[1])}</p><h1>${h(product.name)}</h1><p class="detail-price">${money(product.price)}</p><p class="description">${h(product.description)}</p><div class="detail-controls"><div class="line-between"><label for="quantity">수량</label>${product.stock ? quantity(initial, product.stock) : '<span class="badge cancelled">품절</span>'}</div><p class="fineprint">${product.stock ? `현재 구매 가능 ${product.stock}개 · 배송비 무료` : '현재 재고가 없습니다. 다른 상품을 둘러보세요.'}</p><div class="line-between spaced"><span>총 상품 금액</span><strong id="detail-total">${money(product.price * initial)}</strong></div>${errorRegion()}<div class="detail-actions"><button id="add-cart" type="button" class="btn ghost" ${product.stock ? '' : 'disabled'}>장바구니 담기</button><button id="buy-now" type="button" class="btn primary" ${product.stock ? '' : 'disabled'}>바로 구매</button></div><p class="fineprint">구매에는 로그인이 필요합니다. 주문 화면에서 최종 금액과 배송정보를 확인합니다.</p><a id="cart-added" class="text-link" href="/cart" hidden>장바구니로 이동 →</a></div></section></div>`, product.name);
  bindQuantities(main, input => { if (input.checkValidity()) document.querySelector('#detail-total').textContent = money(product.price * Number(input.value)); });
  const count = () => {
    const input = document.querySelector('#quantity');
    if (!input?.reportValidity()) return null;
    return Number(input.value);
  };
  const add = async amount => {
    await api('/cart/items', { method: 'POST', body: { product_id: id, quantity: amount } });
    notify('장바구니에 담았습니다.'); document.querySelector('#cart-added').hidden = false; await updateCount();
  };
  document.querySelector('#add-cart').addEventListener('click', event => busy(event.currentTarget, async () => {
    const amount = count(); if (!amount) return;
    const next = `/products/${id}?quantity=${amount}`;
    if (!await requireUser(next, { kind: 'cart', product_id: id, quantity: amount })) return;
    try { await add(amount); } catch (error) {
      if (error.status === 401) { storageSet('intent', { kind: 'cart', product_id: id, quantity: amount, at: Date.now() }); location.assign(loginUrl(next)); return; }
      throw error;
    }
  }, actionError));
  document.querySelector('#buy-now').addEventListener('click', event => busy(event.currentTarget, async () => {
    const amount = count(); if (!amount) return;
    const next = `/checkout?product_id=${id}&quantity=${amount}`;
    if (await requireUser(next)) location.assign(next);
  }, actionError));
  const intent = storageGet('intent');
  if (state.user && intent?.kind === 'cart' && intent.product_id === id && Number(params.get('quantity')) === intent.quantity && Date.now() - intent.at < 900000) {
    storageRemove('intent');
    await busy(document.querySelector('#add-cart'), () => add(intent.quantity), actionError);
  }
}

async function authPage(signup = false) {
  const next = safeNext(params.get('next') || '/');
  if (state.user) { location.replace(next); return; }
  if (location.hash) { history.replaceState(null, '', currentPath()); notify('이메일 인증 후 계정 비밀번호로 로그인해 주세요.'); }
  const title = signup ? '나의 궤도 만들기' : '다시 만나 반가워요';
  mount(`<section class="form-page container"><p class="eyebrow">${signup ? 'START YOUR ORBIT' : 'WELCOME BACK'}</p><h1>${title}</h1><p class="muted">${signup ? '일상을 위한 작은 발견, 함께 시작해요.' : next !== '/' ? '로그인하면 선택했던 화면으로 돌아갑니다.' : '로그인하고 당신의 일상을 이어가세요.'}</p><div class="panel"><form id="auth-form" method="post" action="/api/v1/auth/${signup ? 'signup' : 'login'}">${signup ? '<div class="field"><label for="name">이름</label><input id="name" name="name" required maxlength="100" autocomplete="name" placeholder="이름을 입력해 주세요"></div>' : ''}<div class="field"><label for="email">이메일</label><input id="email" name="email" type="email" required maxlength="254" autocomplete="email" placeholder="you@example.com"></div><div class="field"><label for="password">비밀번호</label><input id="password" name="password" type="password" required ${signup ? 'minlength="8"' : ''} maxlength="128" autocomplete="${signup ? 'new-password' : 'current-password'}" placeholder="${signup ? '8자 이상 입력해 주세요' : '비밀번호를 입력해 주세요'}"></div>${signup ? '<div class="field"><label for="confirm">비밀번호 확인</label><input id="confirm" type="password" required maxlength="128" autocomplete="new-password" placeholder="비밀번호를 한 번 더 입력해 주세요"></div>' : ''}${errorRegion()}<button type="submit" class="btn primary full">${signup ? '회원가입' : '로그인'}</button></form><p class="form-end">${signup ? '이미 계정이 있나요?' : '처음 오셨나요?'} <a href="/${signup ? 'login' : 'signup'}?${new URLSearchParams({ next })}">${signup ? '로그인' : '회원가입'}</a></p></div>${state.config.demo_mode ? '<aside class="demo-help"><strong>로컬 체험 계정</strong><br><code>demo@orbit.local</code> / <code>Orbit1234!</code><br><button type="button" id="fill-demo" class="btn small ghost spaced">체험 계정 입력</button></aside>' : ''}</section>`, signup ? '회원가입' : '로그인');
  const form = document.querySelector('#auth-form');
  document.querySelector('#fill-demo')?.addEventListener('click', () => {
    form.elements.email.value = 'demo@orbit.local'; form.elements.password.value = 'Orbit1234!';
    if (signup) { form.elements.name.value = '체험 회원'; document.querySelector('#confirm').value = 'Orbit1234!'; }
    form.elements.email.focus();
  });
  if (signup) document.querySelector('#confirm').addEventListener('input', event => event.target.setCustomValidity(''));
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (signup && document.querySelector('#confirm').value !== form.elements.password.value) {
      document.querySelector('#confirm').setCustomValidity('비밀번호가 일치하지 않습니다.'); document.querySelector('#confirm').reportValidity(); return;
    }
    if (!form.reportValidity()) return;
    const body = { email: form.elements.email.value, password: form.elements.password.value, ...(signup ? { name: form.elements.name.value } : { next }) };
    busy(form.querySelector('[type=submit]'), async () => {
      const result = (await api(`/auth/${signup ? 'signup' : 'login'}`, { method: 'POST', body, refreshSession: false })).data;
      form.elements.password.value = '';
      if (!signup || result.signed_in) { flash(signup ? '가입을 환영합니다.' : '로그인했습니다.'); location.replace(signup ? next : safeNext(result.next)); }
      else { form.innerHTML = `<p class="success" role="status">${h(result.message)}</p><a class="btn primary full spaced" href="${h(loginUrl(next))}">로그인으로 이동</a>`; }
    });
  });
}

async function cartPage() {
  if (!await requireUser()) return;
  let rows = (await api('/cart')).data.items;
  if (!rows.length) { page(`${intro('YOUR BAG', '장바구니')}${empty('아직 담은 상품이 없어요', '마음에 드는 물건을 찾아 나의 궤도에 담아 보세요.')}`, '장바구니'); return; }
  page(`${intro('YOUR BAG', '장바구니', '담아 둔 물건을 확인하고, 원하는 상품만 선택하세요.')}${errorRegion()}<div class="split"><section><div class="cart-toolbar"><label class="check"><input id="select-all" type="checkbox" checked>구매 가능한 상품 전체 선택</label><button id="clear-cart" type="button" class="remove">전체 비우기</button></div><div id="cart-rows" class="cart-list">${rows.map(row => {
    const product = row.product || { id: row.product_id, name: '판매 중지 상품' };
    return `<article class="cart-row" data-id="${h(row.id)}"><input type="checkbox" class="select-item" aria-label="${h(product.name)} 선택" ${row.available ? 'checked' : 'disabled'}><a class="cart-thumb" href="/products/${h(row.product_id)}">${productImage(product)}</a><div><a href="/products/${h(row.product_id)}"><h3>${h(product.name)}</h3></a><p class="price">${row.product ? money(row.product.price) : '구매 불가'}</p>${row.product?.stock ? quantity(row.quantity, row.product.stock, `qty-${row.id}`) : ''}<p class="unavailable" ${row.available ? 'hidden' : ''}>재고가 부족하거나 판매가 중지되었습니다.</p></div><div class="row-price"><strong data-subtotal>${money(row.subtotal)}</strong><br><button class="remove remove-item" type="button" aria-label="${h(product.name)} 삭제">삭제</button></div></article>`;
  }).join('')}</div></section><aside class="summary panel"><h2>주문 예상 금액</h2><div class="line-between"><span class="muted">선택 상품</span><span id="selected-count"></span></div><div class="line-between"><span class="muted">배송비</span><span>무료</span></div><div class="line-between total"><span>합계</span><strong id="selected-total"></strong></div><button id="go-checkout" type="button" class="btn primary full spaced">선택 상품 주문하기</button><p class="fineprint">주문 화면에서 최종 금액을 확인합니다. 결제 후에도 장바구니 항목은 유지됩니다.</p></aside></div>`, '장바구니');
  let pendingSaves = 0;
  const selected = () => rows.filter(row => document.querySelector(`[data-id="${row.id}"] .select-item`)?.checked && row.available);
  function recalculate() {
    const chosen = selected();
    document.querySelector('#selected-total').textContent = money(chosen.reduce((n, r) => n + r.product.price * r.quantity, 0));
    document.querySelector('#selected-count').textContent = `${chosen.reduce((n, r) => n + r.quantity, 0)}개`;
    document.querySelector('#go-checkout').disabled = chosen.length === 0 || pendingSaves > 0;
    document.querySelector('#clear-cart').disabled = pendingSaves > 0;
    const available = rows.filter(r => r.available).length;
    document.querySelector('#select-all').checked = available > 0 && chosen.length === available;
    document.querySelector('#select-all').indeterminate = chosen.length > 0 && chosen.length !== available;
  }
  main.querySelectorAll('.select-item').forEach(input => input.addEventListener('change', recalculate));
  document.querySelector('#select-all').addEventListener('change', event => { main.querySelectorAll('.select-item:not(:disabled)').forEach(input => { input.checked = event.target.checked; }); recalculate(); });
  bindQuantities(main, async input => {
    const article = input.closest('[data-id]'); const row = rows.find(r => r.id === article.dataset.id);
    if (!input.reportValidity()) { input.value = row.quantity; input.closest('.quantity').querySelector('[data-quantity="-1"]').disabled = row.quantity <= 1; input.closest('.quantity').querySelector('[data-quantity="1"]').disabled = row.quantity >= Number(input.max); return; }
    const value = Number(input.value);
    if (value === row.quantity) return;
    const group = input.closest('.quantity');
    const focused = document.activeElement;
    pendingSaves++; recalculate(); group.setAttribute('aria-busy', 'true');
    article.querySelector('.remove-item').disabled = true;
    group.querySelectorAll('button,input').forEach(control => { control.disabled = true; });
    try {
      await api(`/cart/items/${row.id}`, { method: 'PATCH', body: { quantity: value } });
      row.quantity = value; row.available = value <= row.product.stock;
      article.querySelector('[data-subtotal]').textContent = money(row.product.price * value);
      article.querySelector('.select-item').disabled = !row.available;
      article.querySelector('.unavailable').hidden = row.available;
      recalculate(); await updateCount();
    } catch (error) { input.value = row.quantity; actionError(error); }
    finally {
      pendingSaves--; group.removeAttribute('aria-busy');
      article.querySelector('.remove-item').disabled = false;
      input.disabled = false;
      group.querySelector('[data-quantity="-1"]').disabled = Number(input.value) <= 1;
      group.querySelector('[data-quantity="1"]').disabled = Number(input.value) >= Number(input.max);
      recalculate();
      if (group.contains(focused) && document.activeElement === document.body) (focused.disabled ? input : focused).focus();
    }
  });
  main.querySelectorAll('.remove-item').forEach(button => button.addEventListener('click', () => busy(button, async () => {
    const article = button.closest('[data-id]'); await api(`/cart/items/${article.dataset.id}`, { method: 'DELETE' });
    rows = rows.filter(r => r.id !== article.dataset.id); article.remove(); await updateCount();
    if (!rows.length) { await cartPage(); main.querySelector('h2')?.setAttribute('tabindex', '-1'); main.querySelector('h2')?.focus(); }
    else { recalculate(); document.querySelector('#select-all').focus(); }
    notify('장바구니에서 삭제했습니다.');
  }, actionError)));
  document.querySelector('#clear-cart').addEventListener('click', event => busy(event.currentTarget, async () => {
    if (!confirm('장바구니의 모든 상품을 삭제할까요?')) return;
    await api('/cart', { method: 'DELETE' }); await cartPage(); await updateCount(); notify('장바구니를 비웠습니다.');
  }, actionError));
  document.querySelector('#go-checkout').addEventListener('click', () => {
    storageSet('checkout', { owner: state.user.id, at: Date.now(), items: selected().map(r => ({ product_id: r.product_id, quantity: r.quantity })) });
    location.assign('/checkout');
  });
  recalculate();
}

function itemSignature(items) { return JSON.stringify(items.map(i => ({ product_id: i.product_id, quantity: i.quantity })).sort((a, b) => a.product_id.localeCompare(b.product_id))); }
async function checkoutPage() {
  if (!await requireUser()) return;
  let body = null, previews = [], items = [], knownOrder = null;
  const saved = storageGet('pending-order');
  if (params.has('order_id')) {
    if (!uuidPattern.test(params.get('order_id'))) throw new Error('주문 주소가 올바르지 않습니다.');
    knownOrder = (await api(`/orders/${params.get('order_id')}`)).data;
    if (knownOrder.status !== 'pending') { location.replace(`/mypage/orders/${knownOrder.id}`); return; }
    items = knownOrder.items.map(i => ({ product_id: i.product_id, quantity: i.quantity }));
  } else if (params.has('product_id')) {
    const productId = params.get('product_id'); const amount = Number(params.get('quantity') || 1);
    if (!uuidPattern.test(productId) || !Number.isInteger(amount) || amount < 1) throw new Error('선택한 상품과 수량을 확인해 주세요.');
    items = [{ product_id: productId, quantity: amount }];
  } else {
    const selection = storageGet('checkout');
    if (selection?.owner === state.user.id && Date.now() - selection.at < 86400000) items = selection.items;
    else if (saved?.owner === state.user.id && Date.now() - saved.at < 86400000) items = saved.body.items;
  }
  if (!items.length) { page(`${intro('CHECKOUT', '주문 · 결제')}${empty('선택된 상품이 없어요', '장바구니 또는 상품 상세에서 구매할 상품을 선택해 주세요.', '/cart', '장바구니로 이동')}`, '주문 · 결제'); return; }
  if (!knownOrder && saved?.owner === state.user.id && Date.now() - saved.at < 86400000 && itemSignature(saved.body.items) === itemSignature(items)) {
    body = saved.body; previews = saved.previews;
    try { knownOrder = (await api(`/orders/${body.order_id}`)).data; }
    catch (error) { if (error.status !== 404) throw error; }
    if (knownOrder && knownOrder.status !== 'pending') { location.replace(`/mypage/orders/${knownOrder.id}`); return; }
  }
  if (knownOrder) {
    body = { order_id: knownOrder.id, items, recipient_name: knownOrder.recipient_name, recipient_phone: knownOrder.recipient_phone, shipping_address: knownOrder.shipping_address, expected_total: knownOrder.total_amount };
    previews = knownOrder.items.map(i => ({ name: i.product_name, unit_price: i.unit_price, quantity: i.quantity }));
  } else if (!body) {
    previews = await Promise.all(items.map(async item => {
      const product = (await api(`/products/${item.product_id}`, { refreshSession: false })).data;
      if (product.stock < item.quantity) throw new Error(`${product.name}: 구매 가능한 재고가 부족합니다.`);
      return { name: product.name, unit_price: product.price, quantity: item.quantity };
    }));
  }
  const total = body ? body.expected_total : previews.reduce((n, i) => n + i.unit_price * i.quantity, 0);
  if (!Number.isSafeInteger(total)) throw new Error('금액 표시 범위를 초과했습니다. 상품 수량을 줄여 주세요.');
  page(`${intro('YOUR NEXT ORBIT', '주문 · 결제', '배송정보와 최종 금액을 확인해 주세요. 실제 금액이 청구되지 않는 모의 결제입니다.')}<p class="checkout-step">상품 선택 <span aria-hidden="true">→</span> <strong>배송정보 · 결제</strong> <span aria-hidden="true">→</span> 상품 목록</p><form id="checkout-form" method="post" action="/api/v1/orders"><div class="split"><section class="panel"><h2>배송정보</h2><div class="spaced"><div class="field"><label for="recipient_name">수령인</label><input id="recipient_name" name="recipient_name" maxlength="100" autocomplete="name" required value="${h(body?.recipient_name ?? state.user.name)}"></div><div class="field"><label for="recipient_phone">연락처</label><input id="recipient_phone" name="recipient_phone" type="tel" maxlength="30" autocomplete="tel" required placeholder="010-0000-0000" value="${h(body?.recipient_phone ?? state.user.phone ?? '')}"></div><div class="field"><label for="shipping_address">배송 주소</label><textarea id="shipping_address" name="shipping_address" maxlength="1000" autocomplete="street-address" required placeholder="우편번호, 기본 주소, 상세 주소를 모두 입력해 주세요">${h(body?.shipping_address ?? '')}</textarea></div><p id="locked-note" class="fineprint" ${body ? '' : 'hidden'}>이미 생성했거나 처리 중인 주문입니다. 재시도 시 같은 주문과 배송정보를 사용합니다. 내용을 바꾸려면 구매 내역에서 미결제 주문을 취소하고 새로 주문해 주세요.</p></div></section><aside class="panel summary"><h2>주문 상품</h2><div class="checkout-items">${previews.map(item => `<div class="checkout-item"><div><p>${h(item.name)}</p><p>${money(item.unit_price)} × ${item.quantity}개</p></div><strong>${money(item.unit_price * item.quantity)}</strong></div>`).join('')}</div><div class="line-between"><span class="muted">배송비</span><span>무료</span></div><div class="line-between total"><span>최종 결제금액</span><strong>${money(total)}</strong></div><label class="check spaced"><input id="payment-consent" type="checkbox" required><span>주문 내용과 배송정보를 확인했으며, 실제 청구 없는 모의 결제에 동의합니다.</span></label>${errorRegion()}<button id="pay" class="btn primary full spaced" type="submit" ${state.config.mock_payments_enabled ? '' : 'disabled'}>${money(total)} 모의 결제</button>${!state.config.mock_payments_enabled ? '<p class="error">현재 모의 결제가 비활성화되어 있습니다.</p>' : ''}<button id="reload-price" class="btn ghost full spaced" type="button" hidden>최신 금액 다시 불러오기</button><a class="text-link fineprint" href="/mypage/orders?status=pending">결제 대기 주문 확인</a></aside></div></form>`, '주문 · 결제');
  const form = document.querySelector('#checkout-form');
  const lock = value => { ['recipient_name', 'recipient_phone', 'shipping_address'].forEach(name => { form.elements[name].readOnly = value; }); document.querySelector('#locked-note').hidden = !value; };
  lock(Boolean(body));
  document.querySelector('#reload-price').addEventListener('click', () => location.reload());
  let priceChanged = false;
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!form.reportValidity() || priceChanged) return;
    for (const name of ['recipient_name', 'recipient_phone', 'shipping_address']) {
      if (!form.elements[name].value.trim()) { showError(new Error('배송정보에는 공백만 입력할 수 없습니다.')); form.elements[name].focus(); return; }
    }
    const button = document.querySelector('#pay');
    await busy(button, async () => {
      if (!body) body = { order_id: newId(), items, recipient_name: form.elements.recipient_name.value.trim(), recipient_phone: form.elements.recipient_phone.value.trim(), shipping_address: form.elements.shipping_address.value.trim(), expected_total: total };
      storageSet('pending-order', { owner: state.user.id, at: Date.now(), body, previews }); lock(true);
      await api('/orders', { method: 'POST', body });
      const result = (await api(`/orders/${body.order_id}/pay`, { method: 'POST' })).data;
      if (result.payment?.status !== 'succeeded' || result.order?.status !== 'paid') throw new ApiError(409, result.failure_code || 'PAYMENT_FAILED', result.failure_code === 'INSUFFICIENT_STOCK' ? '결제 시점에 재고가 부족해졌습니다. 결제되지 않았습니다. 주문을 취소하고 수량을 확인해 주세요.' : '결제되지 않았습니다. 주문 상태를 확인한 뒤 다시 시도해 주세요.');
      clearCheckout(); flash(`${money(result.payment.amount)} 모의 결제가 완료되었습니다.`); location.replace('/');
    }, error => {
      if (error.code === 'PRICE_CHANGED') { storageRemove('pending-order'); body = null; lock(false); priceChanged = true; document.querySelector('#reload-price').hidden = false; }
      actionError(error);
    });
    if (priceChanged) button.disabled = true;
  });
}

async function mypage(edit = false) {
  if (!await requireUser()) return;
  const user = state.user;
  if (!edit) {
    page(`${intro('MY ORBIT', `${user.name}님의 궤도`, '회원정보와 구매 내역을 한곳에서 확인하세요.')}<div class="profile-grid"><section class="panel"><h2>회원정보</h2><dl class="info-list"><div><dt>이름</dt><dd>${h(user.name)}</dd></div><div><dt>이메일</dt><dd>${h(user.email)}</dd></div><div><dt>연락처</dt><dd>${h(user.phone || '등록되지 않음')}</dd></div></dl><a class="btn ghost" href="/mypage/edit">회원정보 수정</a></section><section class="panel"><h2>나의 쇼핑</h2><div class="profile-links"><a href="/mypage/orders"><span>구매 내역</span><span aria-hidden="true">↗</span></a><a href="/mypage/orders?status=pending"><span>결제 대기 주문</span><span aria-hidden="true">↗</span></a><a href="/cart"><span>장바구니</span><span aria-hidden="true">↗</span></a></div></section></div>`, '마이페이지'); return;
  }
  page(`<div class="narrow"><div class="breadcrumb"><a href="/mypage">마이페이지</a> / 회원정보 수정</div>${intro('YOUR PROFILE', '회원정보 수정')}<form id="profile-form" class="panel" method="post" action="/api/v1/users/me"><div class="field"><label for="name">이름</label><input id="name" name="name" maxlength="100" required autocomplete="name" value="${h(user.name)}"></div><div class="field"><label for="phone">연락처</label><input id="phone" name="phone" type="tel" autocomplete="tel" maxlength="30" value="${h(user.phone || '')}"></div><p class="fineprint">이메일: ${h(user.email)} · 이 화면에서는 이름과 연락처를 수정합니다.</p>${errorRegion()}<p id="save-status" class="success spaced" role="status" hidden></p><button class="btn primary spaced" type="submit">변경사항 저장</button></form><details class="danger-zone"><summary>회원 탈퇴</summary><p>회원정보와 장바구니가 삭제됩니다. 주문·결제 기록은 보존되며 회원 연결은 해제됩니다. 계속하려면 현재 비밀번호를 입력해 주세요.</p><form id="withdraw-form" method="post" action="/api/v1/users/me"><div class="field"><label for="withdraw-password">현재 비밀번호</label><input id="withdraw-password" name="password" type="password" required maxlength="128" autocomplete="current-password"></div><label class="check"><input type="checkbox" required><span>탈퇴 안내를 확인했으며 회원 탈퇴에 동의합니다.</span></label><p id="withdraw-error" class="error" role="alert" hidden></p><button class="btn danger spaced" type="submit">회원 탈퇴하기</button></form></details></div>`, '회원정보 수정');
  const form = document.querySelector('#profile-form');
  form.addEventListener('submit', event => { event.preventDefault(); if (!form.reportValidity()) return; busy(form.querySelector('[type=submit]'), async () => {
    const result = await api('/users/me', { method: 'PATCH', body: { name: form.elements.name.value.trim(), phone: form.elements.phone.value.trim() || null } });
    state.user = result.data; document.querySelector('#save-status').textContent = '회원정보를 저장했습니다.'; document.querySelector('#save-status').hidden = false;
  }, actionError); });
  const withdraw = document.querySelector('#withdraw-form');
  withdraw.addEventListener('submit', event => { event.preventDefault(); if (!withdraw.reportValidity() || !confirm('회원 탈퇴를 진행할까요? 회원정보와 장바구니가 삭제됩니다.')) return; busy(withdraw.querySelector('[type=submit]'), async () => {
    await api('/users/me', { method: 'DELETE', body: { password: withdraw.elements.password.value } });
    withdraw.elements.password.value = ''; clearCheckout(); flash('회원 탈퇴를 완료했습니다.'); location.replace('/');
  }, error => { if (error.status === 401 && error.code !== 'INVALID_PASSWORD') actionError(error); else showError(error, document.querySelector('#withdraw-error')); }); });
}

async function orderHistory() {
  if (!await requireUser()) return;
  const selectedStatus = ['paid', 'pending', 'cancelled'].includes(params.get('status')) ? params.get('status') : 'paid';
  const pageNumber = Math.max(1, Number(params.get('page')) || 1);
  const response = await api(`/orders?${new URLSearchParams({ status: selectedStatus, page: pageNumber, page_size: 10 })}`);
  page(`${intro('ORDER HISTORY', '나의 주문 내역', '구매한 상품과 결제 대기 주문을 확인하세요.')}<nav class="tabs" aria-label="주문 상태">${['paid', 'pending', 'cancelled'].map(s => `<a href="/mypage/orders?status=${s}" ${selectedStatus === s ? 'aria-current="page"' : ''}>${statusLabel(s)}</a>`).join('')}</nav>${response.data.length ? `<div class="order-list">${response.data.map(order => `<article class="panel order-card"><div class="order-card-top"><div><p>${date(order.created_at)}</p><p class="order-id">주문 ${h(order.id)}</p></div>${badge(order.status)}</div><div class="order-card-bottom"><strong>${money(order.total_amount)}</strong><a class="btn small ghost" href="/mypage/orders/${h(order.id)}">주문 상세 보기 →</a></div></article>`).join('')}</div>` : empty('해당 주문 내역이 없어요', selectedStatus === 'paid' ? '첫 번째 일상의 발견을 시작해 보세요.' : '주문 상태가 바뀌면 이곳에서 확인할 수 있어요.')}<nav class="pager" aria-label="주문 페이지">${pageNumber > 1 ? `<a class="btn small" href="?status=${selectedStatus}&page=${pageNumber - 1}">이전</a>` : ''}${response.pagination.has_more ? `<a class="btn small" href="?status=${selectedStatus}&page=${pageNumber + 1}">다음</a>` : ''}</nav>`, '주문 내역');
}

async function orderDetail(id) {
  if (!await requireUser()) return;
  const order = (await api(`/orders/${id}`)).data;
  page(`<div class="breadcrumb"><a href="/mypage/orders">주문 내역</a> / 주문 상세</div>${intro('ORDER DETAIL', '주문 상세', `${date(order.created_at)} 주문`)}<div class="split"><section class="stack"><div class="panel"><div class="line-between"><h2>주문 상품</h2>${badge(order.status)}</div><p class="order-id spaced">${h(order.id)}</p><div class="order-items">${order.items.map(item => `<div class="order-item"><div><h3>${h(item.product_name)}</h3><p class="fineprint">구매 당시 ${money(item.unit_price)} · ${item.quantity}개</p></div><strong>${money(item.unit_price * item.quantity)}</strong></div>`).join('')}</div></div><div class="panel"><h2>배송정보</h2><dl class="info-list spaced"><div><dt>수령인</dt><dd>${h(order.recipient_name)}</dd></div><div><dt>연락처</dt><dd>${h(order.recipient_phone)}</dd></div><div><dt>주소</dt><dd>${h(order.shipping_address)}</dd></div></dl></div></section><aside class="panel summary"><h2>결제정보</h2><div class="line-between"><span class="muted">주문 상태</span><span>${h(statusLabel(order.status))}</span></div><div class="line-between total"><span>총액</span><strong>${money(order.total_amount)}</strong></div><p class="fineprint">${order.payment?.status === 'succeeded' ? `모의 결제 완료 · ${date(order.payment.paid_at)}` : order.payment?.status === 'failed' ? '마지막 결제 시도가 실패했습니다.' : '아직 완료된 결제가 없습니다.'}</p>${errorRegion()}${order.status === 'pending' ? `<a class="btn primary full spaced" href="/checkout?order_id=${h(id)}">이 주문 결제하기</a><button id="cancel-order" type="button" class="btn ghost full spaced">미결제 주문 취소</button>` : ''}<a class="btn ghost full spaced" href="/mypage/orders">주문 내역으로</a></aside></div>`, '주문 상세');
  document.querySelector('#cancel-order')?.addEventListener('click', event => busy(event.currentTarget, async () => {
    if (!confirm('이 미결제 주문을 취소할까요?')) return;
    await api(`/orders/${id}/cancel`, { method: 'POST' });
    if (storageGet('pending-order')?.body.order_id === id) storageRemove('pending-order');
    await orderDetail(id); notify('주문을 취소했습니다.');
  }, actionError));
}

document.querySelector('#logout').addEventListener('click', event => busy(event.currentTarget, async () => {
  await api('/auth/logout', { method: 'POST', refreshSession: false }); clearCheckout(); flash('로그아웃했습니다.'); location.assign('/');
}));
document.addEventListener('error', event => {
  const image = event.target;
  if (image instanceof HTMLImageElement && image.hasAttribute('data-product-image') && !image.dataset.fallback) { image.dataset.fallback = 'true'; image.src = '/assets/images/mug.svg'; }
}, true);
window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });

async function boot() {
  state.config = (await api('/config', { refreshSession: false })).data;
  document.querySelector('#demo-banner').hidden = !state.config.demo_mode;
  try { await loadUser(); } catch { notify('회원 상태를 확인하지 못했습니다. 구매 시 다시 확인합니다.'); }
  updateNav();
  const message = storageGet('flash'); if (message) { storageRemove('flash'); notify(message); }
  if (path === '/') await home();
  else if (path.startsWith('/products/')) await productDetail(path.split('/').pop());
  else if (path === '/login' || path === '/signup') await authPage(path === '/signup');
  else if (path === '/cart') await cartPage();
  else if (path === '/checkout') await checkoutPage();
  else if (path === '/mypage' || path === '/mypage/edit') await mypage(path.endsWith('/edit'));
  else if (path === '/mypage/orders') await orderHistory();
  else if (path.startsWith('/mypage/orders/')) await orderDetail(path.split('/').pop());
  else throw new Error('요청한 화면을 찾을 수 없습니다.');
  await updateCount();
}
boot().catch(error => {
  if (error.status === 401) { location.replace(loginUrl(currentPath())); return; }
  page(`<section class="load-error">${intro('PLEASE TRY AGAIN', '화면을 불러오지 못했어요')}<p class="error" role="alert">${h(error.message)}</p><button id="retry-page" type="button" class="btn primary">다시 불러오기</button> <a href="/" class="btn ghost">상품 목록으로</a></section>`, '연결 확인');
  document.querySelector('#retry-page').addEventListener('click', () => location.reload());
});

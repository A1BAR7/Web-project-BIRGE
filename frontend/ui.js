/* Presentation helpers only. API calls and business decisions live in script.js. */
function setNavOpen(open) {
  document.body.classList.toggle('nav-open', open);
  $('#mobileMenu').setAttribute('aria-expanded', String(open));
  $('#navScrim').hidden = !open;
  if (open) $('.nav-link.active').focus();
}
$('#mobileMenu').addEventListener('click', () => setNavOpen(!document.body.classList.contains('nav-open')));
$('#navScrim').addEventListener('click', () => setNavOpen(false));
const mobileLayout = matchMedia('(max-width: 760px)');
mobileLayout.addEventListener('change', () => setNavOpen(false));
document.addEventListener('keydown', event => {
  if (!document.body.classList.contains('nav-open')) return;
  if (event.key === 'Escape') {
    setNavOpen(false);
    $('#mobileMenu').focus();
  }
  if (event.key === 'Tab') {
    const nodes = $$('a[href], button', $('#sidebar'));
    if (event.shiftKey && document.activeElement === nodes[0]) {
      event.preventDefault(); nodes.at(-1).focus();
    } else if (!event.shiftKey && document.activeElement === nodes.at(-1)) {
      event.preventDefault(); nodes[0].focus();
    }
  }
});

function presentAction({title, description = '', field = null, choices}) {
  const dialog = $('#actionDialog');
  if (dialog.open) return Promise.resolve(null);
  const previousFocus = document.activeElement;
  dialog.returnValue = '';
  $('#actionTitle').textContent = title;
  const fields = $('#actionFields');
  fields.replaceChildren();
  if (description) {
    const paragraph = document.createElement('p');
    paragraph.textContent = description;
    fields.append(paragraph);
  }
  let input;
  if (field) {
    const group = document.createElement('div');
    group.className = 'form-field';
    const label = document.createElement('label');
    label.htmlFor = 'actionInput';
    label.textContent = field.label;
    input = document.createElement('textarea');
    input.id = 'actionInput';
    input.value = field.value || '';
    input.required = true;
    input.minLength = field.minLength || 3;
    input.maxLength = field.maxLength || 300;
    group.append(label, input);
    fields.append(group);
  }
  const actions = $('#actionButtons');
  actions.replaceChildren();
  actions.classList.toggle('choice-actions', choices.length > 2 && !field);
  choices.forEach(choice => {
    const button = document.createElement('button');
    button.type = choice.id === 'submit' ? 'submit' : 'button';
    button.className = choice.primary ? 'primary-button' : 'outline-button';
    if (choice.danger) button.classList.add('danger-button');
    button.textContent = choice.label;
    if (button.type === 'button') button.onclick = () => dialog.close(choice.id);
    actions.append(button);
  });
  $('#actionForm').onsubmit = event => {
    event.preventDefault();
    if (input && input.value.trim().length < input.minLength) {
      input.setCustomValidity(`Кемінде ${input.minLength} таңба енгізіңіз`);
      input.reportValidity();
      return;
    }
    dialog.close('submit');
  };
  if (input) input.oninput = () => input.setCustomValidity('');
  $('#closeAction').onclick = () => dialog.close('cancel');
  dialog.showModal();
  (input || actions.querySelector('button')).focus();
  return new Promise(resolve => dialog.addEventListener('close', () => {
    const result = dialog.returnValue;
    if (previousFocus?.isConnected) previousFocus.focus();
    resolve(result === 'submit' && input ? input.value.trim() : result || 'cancel');
  }, {once: true}));
}

async function askConfirm(title, label = 'Растау', danger = false) {
  return await presentAction({title, choices: [
    {id: 'cancel', label: 'Болдырмау'},
    {id: 'confirm', label, primary: true, danger}
  ]}) === 'confirm';
}

async function askText(title, value) {
  const result = await presentAction({title, field: {label: 'Хабарлама', value, minLength: 3, maxLength: 300}, choices: [
    {id: 'cancel', label: 'Болдырмау'}, {id: 'submit', label: 'Жіберу', primary: true}
  ]});
  return result === 'cancel' || result === null ? null : result;
}

async function choosePublication() {
  const type = await presentAction({title: 'Қай бөлімге жариялайсыз?', choices: [
    {id: 'lost', label: 'Lost & Found — зат жариялау'},
    {id: 'skill', label: 'SkillQos — дағды ұсыну'},
    {id: 'confess', label: 'Ishimде — анонимді жазба'}
  ]});
  if (type === 'lost' || type === 'skill') openModal(type);
  else if (type === 'confess') { navigate('confess'); $('#confessInput').focus(); }
}

function renderHomeMenu() {
  const target = $('#heroMenu');
  if (!homeFoodItems.length) {
    target.innerHTML = `<p class="board-loading">${foodError ? 'Мәзірді Däm бөлімінде қайта жүктеңіз' : 'Мәзір жүктелуде…'}</p>`;
    return;
  }
  const candidates = [...homeFoodItems].sort((a, b) => Number(b.image_kind !== 'placeholder') - Number(a.image_kind !== 'placeholder'));
  const [featured, ...others] = candidates;
  target.innerHTML = `<button type="button" class="board-feature" data-hero-food="${featured.id}"><span class="board-photo"><img src="${escapeHtml(assetUrl(featured.image_url))}" alt="${escapeHtml(featured.image_alt)}"><small>${foodPhotoLabel(featured.image_kind)}</small></span><span class="board-item-copy"><span><strong>${escapeHtml(featured.name)}</strong><small>${escapeHtml(featured.canteen)}</small></span><b>${formatPrice(featured.price)}</b></span></button>${others.slice(0, 2).map(item => `<button type="button" class="board-row" data-hero-food="${item.id}"><span>${escapeHtml(item.name)}</span><b>${formatPrice(item.price)}</b></button>`).join('')}`;
  imageFallbacks(target);
}
$('#heroMenu').addEventListener('click', event => {
  const item = event.target.closest('[data-hero-food]');
  if (item) showFoodDetail(Number(item.dataset.heroFood));
});

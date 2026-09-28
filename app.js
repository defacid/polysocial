const $ = selector => document.querySelector(selector);
const text = $('#postText');
const count = $('#characterCount');
const toast = $('#toast');
const preview = $('#mediaPreview');
const form = $('#postForm');
const selectors = ['facebook', 'instagram', 'threads', 'bluesky'];
const platform = {
  facebook: ['facebook-f', 'fb'],
  instagram: ['instagram', 'ig'],
  threads: ['threads', 'th'],
  bluesky: ['bluesky', 'bs'],
};

function splitForBluesky(source, limit = 300) {
  const parts = [];
  let remaining = source.trim();
  while (remaining.length > limit) {
    let cut = Math.max(
      remaining.lastIndexOf('\n', limit),
      remaining.lastIndexOf('. ', limit) + 1,
      remaining.lastIndexOf('! ', limit) + 1,
      remaining.lastIndexOf('? ', limit) + 1,
      remaining.lastIndexOf(' ', limit),
    );
    if (cut < Math.floor(limit * 0.55)) cut = limit;
    parts.push(remaining.slice(0, cut).trim());
    remaining = remaining.slice(cut).trim();
  }
  if (remaining) parts.push(remaining);
  return parts;
}

function updateCount() {
  const value = text.value.trim();
  const hasMedia = preview.children.length > 0;
  const details = {
    facebook: ['facebook-f', 'post', 0],
    instagram: ['instagram', 'post', 0],
    threads: ['threads', 'thread', 500],
    bluesky: ['bluesky', 'skeet', 300],
  };
  const selected = selectors.filter(id => $(`#${id}`).value !== 'none');
  count.innerHTML = selected.map(id => {
    const [icon, unit, limit] = details[id];
    const amount = (!value && !hasMedia) || (id === 'instagram' && !hasMedia)
      ? 0
      : limit && value ? splitForBluesky(value, limit).length : 1;
    return `<i class="fa-brands fa-${icon}" aria-hidden="true"></i> ${amount} <span class="count-word">${unit}${amount === 1 ? '' : 's'}</span>`;
  }).join(' &nbsp; ');
  if (!selected.length) count.textContent = 'No destinations selected';
  const total = count.nextElementSibling;
  total.hidden = false;
  total.innerHTML = `${text.value.length} <span class="character-word">characters</span>`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 4500);
}

function makeLocalSettings() {
  const button = $('#userMenu');
  if (button.dataset.localSettings) return;
  button.dataset.localSettings = 'true';
  button.innerHTML = '<i class="fa-solid fa-gear" aria-hidden="true"></i><span>Settings</span>';
  button.style.cssText = 'font-size:14px;padding:9px 13px;background:#17438f;border:1px solid #7299ef;border-radius:8px';
  button.setAttribute('aria-label', 'Open local settings');
  button.removeAttribute('aria-controls');
  const media = document.querySelector('.icon-action[for="mediaInput"]');
  media.innerHTML = '<i class="fa-solid fa-image" aria-hidden="true"></i><span>Media</span>';
  media.style.cssText = 'width:auto;padding:0 11px;gap:7px;display:inline-flex;align-items:center;font:800 11px Manrope';
  $('#emojiButton')?.remove();
  const publish = document.querySelector('.primary-button');
  publish.querySelector('span:last-child')?.remove();
  publish.style.cssText = 'background:#26a96e;color:#fff;box-shadow:0 4px 14px #26a96e59';
  const dialog = $('#settingsDialog');
  dialog.querySelector('h2').textContent = 'Local settings';
  dialog.querySelector('p').textContent = 'Polysocial runs on this machine. Connections, drafts, media, and schedules stay here—there is no Polysocial user account.';
  dialog.querySelector('.delivery-rule').innerHTML = '<strong>Local delivery & privacy</strong><p>Connected-account tokens are encrypted on this machine. Scheduled posts run only while the local Polysocial service is running.</p>';
  button.addEventListener('click', event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    $('#accountMenu').hidden = true;
    dialog.showModal();
  }, true);
}

function updateSummary() {
  makeLocalSettings();
  const brand = $('.brand');
  if (!brand.dataset.logo) {
    brand.innerHTML = '<img src="./polysocial-brand.svg" alt="DEFACID Polysocial">';
    brand.dataset.logo = 'true';
    brand.style.cssText = 'display:block;width:172px;height:46px';
    brand.querySelector('img').style.cssText = 'display:block;width:172px;height:46px';
  }
  const box = $('#destinationSummary');
  box.replaceChildren();
  for (const id of selectors) {
    const [iconName, kind] = platform[id];
    const icon = document.createElement('span');
    icon.className = `status-icon ${kind} ${$(`#${id}`).value === 'none' ? 'none' : ''}`;
    icon.innerHTML = `<i class="fa-brands fa-${iconName}" aria-hidden="true"></i>`;
    icon.title = `${id}: ${$(`#${id}`).selectedOptions[0].text}`;
    box.append(icon);
  }
}

function updateSafetyNote() {
  if (!$('#accessibility-tweaks')) {
    document.head.insertAdjacentHTML('beforeend', `<style id="accessibility-tweaks">
      .account-select{font-size:13px!important}.composer-meta,.scheduled-copy span,.setting-line small{font-size:12px!important}
      .text-button{font-size:12px!important}.scheduled-copy strong,.destination-row>label{font-size:13px!important}
      .destination-summary .status-icon::after{color:#fff!important}.schedule-control{position:relative}
      .schedule-control input{inset:0!important;width:100%!important;height:100%!important;cursor:pointer}
      @media(max-width:600px){.destination-row .account-select{grid-column:1/-1!important;width:100%!important}.schedule-label{display:inline!important}.composer-meta .count-word,.composer-meta .character-word{display:none}.composer-meta{font-size:12px!important}.user-menu{font-size:14px!important}}
    </style>`);
  }
}

function ensureMediaViewer() {
  if ($('#mediaViewer')) return;
  document.head.insertAdjacentHTML('beforeend', `<style id="media-viewer-style">
    .media-card{position:relative;display:inline-block;flex:0 0 104px;padding:0;border:0;background:none;cursor:zoom-in}
    .media-card img,.media-card video{display:block;height:78px;width:104px;object-fit:cover;border-radius:8px;border:1px solid var(--line)}
    .media-card.dragging{opacity:.45}.media-order{position:absolute;left:0;bottom:0;min-width:23px;height:22px;padding:0 6px;display:grid;place-items:center;background:#fff;color:#173f91;border-radius:0 7px 0 7px;font:800 11px Manrope,sans-serif;pointer-events:none}
    .remove-media{position:absolute;right:3px;top:3px;width:22px;height:22px;border:2px solid #0b2860;border-radius:50%;background:#fff;color:#173f91;font-weight:800;line-height:1;padding:0;display:grid;place-items:center;cursor:pointer;z-index:1}
    .alt-media{position:absolute;left:3px;top:3px;z-index:1;border:0;border-radius:4px;padding:3px 5px;background:#fff;color:#173f91;font:800 9px Manrope,sans-serif;cursor:pointer}.alt-media.complete{background:#39d99b;color:#071943}
    .media-viewer{max-width:min(92vw,920px);width:auto;padding:12px;background:#071943;border:1px solid #ffffff55}.media-viewer::backdrop{background:#000c}
    .media-viewer img,.media-viewer video{display:block;max-width:86vw;max-height:78vh;object-fit:contain}.media-viewer button{position:absolute;right:7px;top:5px;width:30px;height:30px;border:0;border-radius:50%;background:#fff;color:#071943;font-size:20px;cursor:pointer}
  </style>`);
  document.body.insertAdjacentHTML('beforeend', '<dialog class="media-viewer" id="mediaViewer"><button type="button" aria-label="Close media preview">×</button><div></div></dialog>');
  $('#mediaViewer button').addEventListener('click', () => $('#mediaViewer').close());
  $('#mediaViewer').addEventListener('click', event => {
    if (event.target === $('#mediaViewer')) $('#mediaViewer').close();
  });
}

function showMedia(item) {
  ensureMediaViewer();
  const viewer = $('#mediaViewer');
  const large = item.cloneNode(true);
  if (large.tagName === 'VIDEO') large.controls = true;
  viewer.querySelector('div').replaceChildren(large);
  viewer.showModal();
}

function updateMediaOrder() {
  [...preview.children].forEach((card, index) => {
    card.querySelector('.media-order').textContent = index + 1;
  });
}

function placeDraggedCard(event, card) {
  event.preventDefault();
  const dragging = preview.querySelector('.dragging');
  if (!dragging || dragging === card) return;
  const bounds = card.getBoundingClientRect();
  preview.insertBefore(dragging, event.clientX > bounds.left + bounds.width / 2 ? card.nextSibling : card);
  updateMediaOrder();
}

$('#mediaInput').addEventListener('change', event => {
  ensureMediaViewer();
  const files = [...event.target.files];
  for (const file of files) {
    const item = document.createElement(file.type.startsWith('video/') ? 'video' : 'img');
    const card = document.createElement('div');
    const remove = document.createElement('button');
    const alt = document.createElement('button');
    const order = document.createElement('span');
    item.src = URL.createObjectURL(file);
    item.alt = file.name;
    if (item.tagName === 'VIDEO') item.muted = true;
    card.className = 'media-card';
    card._file = file;
    card._alt = '';
    card.draggable = true;
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Preview ${file.name}; drag to reorder`);
    remove.className = 'remove-media';
    remove.type = 'button';
    remove.setAttribute('aria-label', `Remove ${file.name}`);
    remove.textContent = '×';
    alt.className = 'alt-media';
    alt.type = 'button';
    alt.textContent = 'ALT';
    alt.setAttribute('aria-label', `Add alt text for ${file.name}`);
    alt.addEventListener('click', click => {
      click.stopPropagation();
      const value = prompt('Describe this image for people using screen readers:', card._alt || '');
      if (value !== null) {
        card._alt = value.trim();
        alt.classList.toggle('complete', Boolean(card._alt));
        alt.setAttribute('aria-label', `${card._alt ? 'Edit' : 'Add'} alt text for ${file.name}`);
      }
    });
    order.className = 'media-order';
    remove.addEventListener('click', click => {
      click.stopPropagation();
      URL.revokeObjectURL(item.src);
      card.remove();
      updateMediaOrder();
      updateCount();
    });
    card.addEventListener('dragstart', drag => {
      card.classList.add('dragging');
      drag.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      updateMediaOrder();
    });
    card.addEventListener('dragover', drag => placeDraggedCard(drag, card));
    card.addEventListener('click', () => showMedia(item));
    card.addEventListener('keydown', key => {
      if (key.key === 'Enter' || key.key === ' ') {
        key.preventDefault();
        showMedia(item);
      }
    });
    card.append(item, remove, alt, order);
    preview.append(card);
  }
  updateMediaOrder();
  updateCount();
  event.target.value = '';
  if (files.length) showToast(`${files.length} media item${files.length === 1 ? '' : 's'} attached.`);
});

document.querySelector('.schedule-control').addEventListener('click', event => {
  event.preventDefault();
  const input = $('#scheduleTime');
  try { input.showPicker(); } catch { input.focus(); }
});

text.addEventListener('input', updateCount);
for (const id of selectors) {
  $(`#${id}`).addEventListener('change', () => {
    updateCount();
    updateSafetyNote();
    updateSummary();
  });
}

$('#settingsDialog .dialog-close').addEventListener('click', () => $('#settingsDialog').close());
document.querySelectorAll('.fb,.ig,.th,.bs').forEach(icon => {
  const kind = [...icon.classList].find(name => ['fb', 'ig', 'th', 'bs'].includes(name));
  const item = Object.values(platform).find(value => value[1] === kind);
  if (item) icon.innerHTML = `<i class="fa-brands fa-${item[0]}" aria-hidden="true"></i>`;
});

$('#composer-title')?.remove();
$('.composer').setAttribute('aria-label', 'Post composer');
updateCount();
updateSafetyNote();
updateSummary();

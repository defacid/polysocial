window.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#postForm');
  const preview = document.querySelector('#mediaPreview');
  const text = document.querySelector('#postText');
  const destinations = document.querySelector('#destinations');
  const postLabel = form.querySelector('label[for="postText"]');
  const publish = form.querySelector('.primary-button');
  const mediaInput = document.querySelector('#mediaInput');
  mediaInput.accept = 'image/jpeg,image/png,image/webp,video/mp4';
  document.querySelector('label[for="mediaInput"]')?.setAttribute('title', 'Attach images or one MP4 video');
  const queue = document.querySelector('.scheduled');
  const scheduledList = queue.querySelector('.scheduled-list');
  const historyList = queue.querySelector('.history-list');
  const platforms = ['facebook', 'instagram', 'threads', 'bluesky'];
  const icons = {facebook: 'facebook-f', instagram: 'instagram', threads: 'threads', bluesky: 'bluesky'};
  const colors = {facebook: 'fb', instagram: 'ig', threads: 'th', bluesky: 'bs'};
  let posts = [];
  let deliveries = [];
  let editingId = null;
  let calendarMonth = new Date();
  let initialization;
  let publicConfig = {};

  document.head.insertAdjacentHTML('beforeend', `<style id="local-queue-style">
    #calendarDialog .calendar-close{color:#10295c!important}
    .calendar-grid .calendar-post{display:flex!important;flex-direction:column;justify-content:center;gap:3px!important}
    .calendar-grid .calendar-post b,.calendar-grid .calendar-post small{line-height:.9}
    .editing-banner{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px;padding:11px 13px;border:1px solid #7299ef;border-radius:10px;background:#17438f;color:#fff}
    .editing-banner span{font:800 13px Manrope,sans-serif}.editing-banner strong{font:500 12px "DM Mono",monospace;color:#dce7ff}
    .editing-banner button{border:0;background:transparent;color:#fff;text-decoration:underline;font:700 12px Manrope;cursor:pointer}
    .new-post-banner{background:transparent;border-color:transparent;padding:0 0 8px;font-size:13px}
    .scheduled{border-top:0}
    .post-section{border:1px solid #7299ef66;border-radius:12px;background:#071c4659;overflow:hidden}.post-section+.post-section{margin-top:2px}
    .post-section>summary{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:17px 18px;color:#fff;cursor:pointer;list-style:none;font:800 25px Manrope,sans-serif}
    .post-section>summary::-webkit-details-marker{display:none}.section-summary-actions{display:flex;align-items:center;gap:15px;margin-left:auto}.section-chevron{width:12px;height:12px;border-right:3px solid #b8caff;border-bottom:3px solid #b8caff;transform:rotate(45deg);transition:transform .18s ease;margin:0 5px 7px 0}.post-section:not([open]) .section-chevron{transform:rotate(-45deg);margin-bottom:0}.calendar-button{border:1px solid #7299ef;background:#17438f;border-radius:8px;padding:8px 11px;color:#fff;white-space:nowrap}
    .post-section-content{padding:0 10px 10px}
    .scheduled-list,.history-list{display:grid;gap:2px}.empty-post-list{margin:0;padding:20px;border:1px dashed #7299ef77;border-radius:10px;color:#b8caff;text-align:center;font:600 13px Manrope,sans-serif}
    #destinations{margin-top:12px;margin-bottom:8px}
    .inline-delete{background:#6d2233!important;border:1px solid #dc667c!important;position:relative;overflow:hidden;min-width:116px}
    .inline-delete span{position:relative;z-index:1}
    .post-id{display:block;margin-top:5px;color:#b8caff;font:500 12px "DM Mono",monospace}
    .scheduled-post{grid-template-columns:64px minmax(0,1fr);gap:15px;padding:0 15px 0 0;min-height:82px;overflow:hidden}
    .scheduled-post+.scheduled-post{margin-top:2px}
    .scheduled-leading{position:relative;align-self:stretch;width:64px;min-height:82px}
    .scheduled-leading .date-block{width:100%;height:100%;min-height:82px;border-radius:11px 0 0 11px}
    .scheduled-media{position:relative;width:100%;height:100%;min-height:82px}
    .scheduled-media img,.scheduled-media video{position:absolute;width:52px;height:70px;object-fit:cover;border:1px solid #ffffff55;background:#071943}
    .scheduled-media .media-back{left:9px;top:10px;border-radius:8px;opacity:.82}
    .scheduled-media .media-front{left:3px;top:4px;width:52px;height:72px;border-radius:8px;z-index:1}
    .scheduled-media.single .media-front{left:3px;top:3px;width:58px;height:76px;min-height:0;border:1px solid #ffffff55;border-radius:8px}
    .media-total{position:absolute;z-index:2;left:37px;top:50%;transform:translate(-50%,-50%);width:25px;height:25px;border-radius:50%;display:grid;place-items:center;background:#fff;color:#071943;font:800 11px Manrope,sans-serif;box-shadow:0 2px 8px #0008}
    .scheduled-copy{min-width:0;padding:13px 0;display:flex;flex-direction:column;justify-content:space-between}
    .scheduled-meta{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:7px;color:#b8caff;font:500 11px "DM Mono",monospace}
    .scheduled-meta .post-id{display:inline;margin:0;color:#fff;font:600 11px "DM Mono",monospace}
    .scheduled-meta .post-time{color:inherit;font:inherit;margin:0;text-align:right}
    .scheduled-body{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;min-width:0}
    .scheduled-copy .post-title{display:-webkit-box;min-width:0;overflow:hidden;text-overflow:ellipsis;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;line-height:1.35;max-height:2.7em}
    .scheduled-controls{display:flex;align-items:center;justify-content:flex-end;gap:12px;flex:0 0 auto}
    .destination-icons{display:flex;gap:5px}
    .queue-status{width:23px;height:23px;position:relative;display:grid;place-items:center;border-radius:7px;color:#fff;font-size:12px;font-weight:800}
    .scheduled-copy .queue-status{color:#fff}
    .queue-status>i{display:grid;width:100%;height:100%;place-items:center;color:#fff!important;font-size:12px;line-height:1;text-align:center}
    .queue-status::after{position:absolute;right:-4px;bottom:-4px;width:11px;height:11px;border-radius:50%;display:grid;place-items:center;font-size:8px;background:#39d99b;color:#fff;content:"✓";box-shadow:0 0 0 2px #0b2860}
    .queue-status.delivery-queued::after,.queue-status.delivery-publishing::after{content:"…";background:#f0ad3d;color:#071943}
    .queue-status.delivery-retry::after,.queue-status.delivery-failed::after{content:"!";background:#e85b5b;color:#fff}
    .queue-status.delivery-cancelled::after{content:"–";background:#7184ad;color:#fff}
    .queue-status.delivery-not_implemented::after{content:"–";background:#7184ad;color:#fff}
    .queue-status.none::after{content:"⛔";background:#e85b5b;font-size:7px}
    .history-card{border:1px solid #7299ef66;border-radius:12px;background:#0b2860;overflow:hidden}.history-card>summary{list-style:none;cursor:pointer}.history-card>summary::-webkit-details-marker{display:none}.history-card .scheduled-post{border:0;border-radius:0;margin:0;width:100%}.history-card .queue-status:not(.delivery-delivered)::after{content:"×";background:#e85b5b;color:#fff}.history-expand{width:24px;height:24px;display:grid;place-items:center;color:#b8caff}.history-expand::before{content:"";width:7px;height:7px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg);transition:transform .18s ease}.history-card[open] .history-expand::before{transform:rotate(225deg)}
    .history-deliveries{display:grid;gap:1px;padding:7px 12px 12px 79px;border-top:1px solid #7299ef44}.history-delivery{display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:10px;min-height:39px;padding:4px 0;color:#dce7ff;font:600 12px Manrope,sans-serif}.history-delivery+.history-delivery{border-top:1px solid #7299ef2e}.history-delivery .queue-status{width:25px;height:25px}.history-delivery a{color:#fff;font-weight:800;text-underline-offset:3px}.history-result{color:#b8caff;text-transform:capitalize}.history-result.failed{color:#ff9dac}
    .delivery-action,.post-action{border:1px solid #7299ef;border-radius:6px;padding:5px 7px;background:#17438f;color:#fff;font:800 10px Manrope,sans-serif;cursor:pointer}.post-action{font-size:9px}.connection-health{margin-left:8px;color:#637bac;font-size:10px}.connection-health.expiring,.connection-health.expired{color:#a5233e}
    .attempt-list{grid-column:2/-1;margin:3px 0 7px;padding:7px 9px;border-radius:7px;background:#071943;color:#dce7ff;font:10px "DM Mono",monospace}.attempt-list div+div{margin-top:5px}.attempt-list strong{color:#fff}.queue-control{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px;padding:12px;border-radius:9px;background:#edf3ff;color:#274d9d}.queue-control button{border:0;border-radius:7px;padding:8px 10px;background:#2459c8;color:#fff;font:800 10px Manrope;cursor:pointer}
    .setting-line{justify-content:flex-start;gap:7px}.setting-line>span:first-child{margin-right:auto}.setting-test{border:0;background:#edf3ff;color:#31589d;border-radius:6px;padding:7px 8px;font:700 10px Manrope;cursor:pointer}
    .calendar-dialog{border:0;border-radius:16px;padding:25px;max-width:420px;width:calc(100vw - 32px);color:#10295c}
    .calendar-dialog::backdrop{background:#000b}
    .calendar-close{position:absolute;right:11px;top:7px;border:0;background:none;font-size:24px;cursor:pointer}
    .calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;margin-top:18px;text-align:center}
    .calendar-grid span{height:34px;display:grid;place-items:center;font-size:12px}
    .calendar-grid .day{font-weight:800;color:#6d80ad;font-size:10px}
    .calendar-grid .calendar-post{margin:auto;width:34px;height:34px;border-radius:50%;background:#2864ed;color:#fff;font-weight:800}
    .calendar-grid .calendar-post small{font-size:9px;font-weight:500;color:#dce7ff}
    .connection-dialog{width:min(92vw,480px);color:#10295c}.connection-form{display:grid;gap:12px}.connection-form label{display:grid;gap:5px;font:700 12px Manrope,sans-serif}.connection-form input{width:100%;padding:10px;border:1px solid #9eb6ea;border-radius:8px;font:14px Manrope,sans-serif}.connection-state{padding:10px;border-radius:8px;background:#edf3ff;color:#274d9d;font-size:12px;line-height:1.5}.connection-actions{display:flex;justify-content:flex-end;gap:8px}.connection-actions button{border:0;border-radius:8px;padding:10px 13px;font:800 12px Manrope,sans-serif;cursor:pointer}.connection-save{background:#26a96e;color:#fff}.connection-disconnect{background:#ffe5ea;color:#9f233b}.delivery-toggle{display:flex!important;grid-template-columns:auto 1fr!important;align-items:center;gap:9px!important}.delivery-toggle input{width:18px;height:18px}
    .meta-intro{margin:0 0 12px;color:#536eaa;font-size:12px;line-height:1.5}.meta-accounts{display:grid;gap:8px;margin-bottom:12px}.meta-account{display:grid;grid-template-columns:34px 1fr auto;align-items:center;gap:10px;padding:10px;border:1px solid #d7e2fa;border-radius:10px;background:#f7f9ff}.meta-account-icon{width:34px;height:34px;border-radius:9px;display:grid;place-items:center;color:#fff;font-size:18px}.meta-account strong,.meta-account small{display:block}.meta-account strong{font-size:12px}.meta-account small{margin-top:2px;color:#637bac;font-size:10px}.meta-account-status{border-radius:999px;padding:4px 7px;background:#e9eef9;color:#63718f;font:800 9px Manrope,sans-serif}.meta-account-status.connected{background:#d9f7e9;color:#137249}.meta-help{margin:0;color:#637bac;font-size:10px;line-height:1.45}.meta-advanced{border:1px solid #d7e2fa;border-radius:9px;padding:0 10px;background:#f8faff}.meta-advanced>summary{padding:10px 0;cursor:pointer;color:#31589d;font:800 11px Manrope,sans-serif}.meta-advanced-content{display:grid;gap:11px;padding:0 0 11px}.meta-token-block{display:grid;gap:9px;padding-top:10px;border-top:1px solid #d7e2fa}.meta-token-block .connection-actions{justify-content:flex-start}.meta-callback{overflow-wrap:anywhere;margin:0;color:#637bac;font-size:10px;line-height:1.45}
    @media(max-width:600px){.post-section>summary{font-size:20px}.scheduled-actions{margin:-47px 0 12px;padding-right:27px}.history-deliveries{padding-left:68px;padding-right:9px}.history-delivery{grid-template-columns:28px minmax(0,1fr);gap:8px}.history-delivery a,.history-result{grid-column:2}.scheduled-post{grid-template-columns:58px minmax(0,1fr);gap:10px;padding-right:8px;min-height:64px}.scheduled-leading{width:58px;min-height:64px}.scheduled-leading .date-block{min-height:64px}.scheduled-media{min-height:64px}.scheduled-media .media-front{left:3px;top:3px;width:48px;height:56px;border-radius:8px}.scheduled-media .media-back{left:9px;top:8px;width:48px;height:54px;border-radius:8px}.scheduled-media.single .media-front{left:2px;top:3px;width:54px;height:58px;min-height:0;border:1px solid #ffffff55;border-radius:8px}.scheduled-media .media-total{left:29px}.scheduled-copy{align-self:stretch;justify-content:flex-start;padding:5px 0}.scheduled-meta{font-size:9px;gap:7px;white-space:nowrap;margin-bottom:1px}.scheduled-meta .post-id{font-size:10px}.scheduled-meta .post-time{font-size:9px}.scheduled-copy .post-title{height:2.7em;min-height:2.7em;margin-top:0}.scheduled-body{flex:0;align-items:flex-end;gap:8px}.scheduled-post .destination-icons{display:flex;gap:5px}.scheduled-controls{align-self:flex-end;gap:6px;margin-left:auto}.scheduled-copy .queue-status{width:26px;height:26px;border-radius:8px}.queue-status>i{font-size:14px}.scheduled-post .more{width:30px;height:26px;padding:0;display:grid;place-items:center;font-size:17px;line-height:1}.editing-banner{flex-wrap:nowrap}}
    @media(max-width:600px){.post-section>summary{padding:14px 12px}.section-summary-actions{gap:11px}.calendar-button{padding:7px 9px}}
  </style>`);

  async function api(path, options = {}) {
    const response = await fetch(path, {cache: 'no-store', ...options});
    if (!response.ok) {
      let message = `Request failed: ${response.status}`;
      try { message = (await response.json()).error || message; } catch {}
      throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
  }

  const readPosts = () => api('/api/posts');
  const readDeliveries = () => api('/api/deliveries');
  const readPost = id => api(`/api/posts/${encodeURIComponent(id)}`);
  const writePost = post => api(`/api/posts/${encodeURIComponent(post.id)}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(post)});
  const deletePost = id => api(`/api/posts/${encodeURIComponent(id)}`, {method: 'DELETE'});
  const deliveryAction = (postId, platform, action) => api(`/api/deliveries/${encodeURIComponent(postId)}/${platform}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action})});

  function fileData(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(',')[1]);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  async function serializeMedia(file, alt = '') {
    if (file.type.startsWith('video/') || file.type === 'image/jpeg') {
      return {name: file.name, type: file.type, data: await fileData(file), alt};
    }
    // Instagram's publishing API accepts JPEG images only. Keep previews in
    // their original format, then normalize the stored copy once on save.
    try {
      const bitmap = await createImageBitmap(file);
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const context = canvas.getContext('2d');
      context.fillStyle = '#fff';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(bitmap, 0, 0);
      bitmap.close();
      const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Image conversion failed')), 'image/jpeg', 0.92));
      const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
      return {name, type: 'image/jpeg', data: await fileData(blob), alt};
    } catch (error) {
      console.warn('Could not normalize image for Instagram', error);
      return {name: file.name, type: file.type, data: await fileData(file), alt};
    }
  }

  function storedFile(item) {
    const binary = atob(item.data);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index);
    return new File([bytes], item.name, {type: item.type});
  }

  function clearMedia() {
    for (const card of preview.children) {
      const media = card.querySelector('img,video');
      if (media?.src?.startsWith('blob:')) URL.revokeObjectURL(media.src);
    }
    preview.replaceChildren();
  }

  function setBanner(post) {
    let banner = document.querySelector('#editingBanner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'editingBanner';
      form.insertBefore(banner, postLabel);
    }
    banner.className = `editing-banner${post ? '' : ' new-post-banner'}`;
    banner.replaceChildren();
    const label = document.createElement('span');
    label.textContent = post ? 'Editing scheduled post' : "What's on your mind?";
    banner.append(label);
    if (post) {
      const id = document.createElement('strong');
      id.textContent = post.id;
      const cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.textContent = 'Cancel';
      cancel.addEventListener('click', () => resetComposer());
      banner.append(id, cancel);
    }
  }

  function resetComposer() {
    editingId = null;
    delete form.dataset.editing;
    form.reset();
    clearMedia();
    document.querySelector('#inlineDelete')?.remove();
    document.querySelector('#clearButton').hidden = false;
    publish.querySelector('span').textContent = 'Publish';
    publish.setAttribute('aria-label', 'Publish post');
    setBanner(null);
    updateCount();
    updateSafetyNote();
    updateSummary();
  }

  function addDeleteButton() {
    let button = document.querySelector('#inlineDelete');
    if (button) return;
    button = document.createElement('button');
    button.id = 'inlineDelete';
    button.className = 'primary-button inline-delete';
    button.type = 'button';
    button.innerHTML = '<span>Delete (hold 2s)</span>';
    publish.insertAdjacentElement('afterend', button);
    let timer, frame;
    const reset = () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
      button.style.removeProperty('background');
      button.querySelector('span').textContent = 'Delete (hold 2s)';
    };
    const start = () => {
      if (timer || !editingId) return;
      const started = performance.now();
      const paint = now => {
        const percent = Math.min(100, (now - started) / 2000 * 100);
        button.style.setProperty('background', `linear-gradient(90deg,#dc667c ${percent}%,#6d2233 ${percent}%)`, 'important');
        button.querySelector('span').textContent = `Delete (${Math.max(0, Math.ceil((2000 - (now - started)) / 1000))}s)`;
        if (percent < 100) frame = requestAnimationFrame(paint);
      };
      frame = requestAnimationFrame(paint);
      timer = setTimeout(async () => {
        const id = editingId;
        timer = null;
        try {
          await deletePost(id);
          posts = await readPosts();
          renderQueue();
          resetComposer();
          showToast(`Post ${id} deleted.`);
        } catch (error) { showToast('Could not delete the post locally.'); reset(); }
      }, 2000);
    };
    button.addEventListener('pointerdown', start);
    for (const event of ['pointerup', 'pointerleave', 'pointercancel']) button.addEventListener(event, reset);
    button.addEventListener('keydown', event => { if (event.key === ' ' || event.key === 'Enter') { event.preventDefault(); start(); } });
    button.addEventListener('keyup', event => { if (event.key === ' ' || event.key === 'Enter') reset(); });
    button.addEventListener('blur', reset);
  }

  async function openQueuedPost(id) {
    if (!id) return;
    try {
      await initialization;
      const post = await readPost(id);
      if (!post) { showToast('That post is no longer in the queue.'); return; }
      resetComposer();
      editingId = id;
      form.dataset.editing = id;
      text.value = post.text;
      for (const platform of platforms) {
        const saved = post.destinations[platform] || 'none';
        document.querySelector(`#${platform}`).value = saved === 'none' ? 'none' : 'connected';
      }
      document.querySelector('#scheduleTime').value = post.scheduledFor || '';
      if (post.media?.length) {
        const transfer = new DataTransfer();
        for (const item of post.media) transfer.items.add(storedFile(item));
        const input = document.querySelector('#mediaInput');
        input.files = transfer.files;
        input.dispatchEvent(new Event('change', {bubbles: true}));
        [...preview.children].forEach((card, index) => {
          card._alt = post.media[index]?.alt || '';
          card.querySelector('.alt-media')?.classList.toggle('complete', Boolean(card._alt));
        });
      }
      setBanner(post);
      publish.querySelector('span').textContent = 'Save';
      publish.setAttribute('aria-label', 'Save scheduled post');
      addDeleteButton();
      document.querySelector('#clearButton').hidden = true;
      destinations.open = false;
      updateCount();
      updateSafetyNote();
      updateSummary();
      window.scrollTo({top: 0, behavior: 'instant'});
      text.focus({preventScroll: true});
    } catch (error) { console.error(error); showToast('Could not open this post.'); }
  }
  window.openQueuedPost = openQueuedPost;

  function postDate(post) { return new Date(post.scheduledFor || post.createdAt); }

  function postPreview(post) {
    const value = post.text.trim().replace(/\s+/g, ' ');
    if (!value) return `${post.media?.length || 0} media item${post.media?.length === 1 ? '' : 's'}`;
    const limit = window.matchMedia('(max-width: 600px)').matches ? 32 : 64;
    return value.length > limit ? `${value.slice(0, limit).trimEnd()}…` : value;
  }

  function mediaSource(item) {
    return item?.data && item?.type ? `data:${item.type};base64,${item.data}` : '';
  }

  function scheduledLeading(post, date) {
    const leading = document.createElement('div');
    leading.className = 'scheduled-leading';
    const media = post.media || [];
    if (!media.length) {
      const block = document.createElement('div');
      block.className = 'date-block';
      const day = document.createElement('strong');
      day.textContent = String(date.getDate());
      const month = document.createElement('span');
      month.textContent = date.toLocaleDateString(undefined, {month: 'short'}).toUpperCase();
      block.append(day, month);
      leading.append(block);
      return leading;
    }
    const stack = document.createElement('div');
    stack.className = `scheduled-media${media.length === 1 ? ' single' : ''}`;
    const addPreview = (item, className) => {
      const element = document.createElement(item.type?.startsWith('video/') ? 'video' : 'img');
      element.className = className;
      element.src = mediaSource(item);
      if (element.tagName === 'IMG') element.alt = '';
      element.setAttribute('aria-hidden', 'true');
      stack.append(element);
    };
    if (media.length > 1) addPreview(media[1], 'media-back');
    addPreview(media[0], 'media-front');
    if (media.length > 1) {
      const total = document.createElement('span');
      total.className = 'media-total';
      total.textContent = String(media.length);
      total.setAttribute('aria-label', `${media.length} media items`);
      stack.append(total);
    }
    leading.append(stack);
    return leading;
  }

  function postDeliveries(post) {
    return platforms
      .filter(platform => post.destinations[platform] && post.destinations[platform] !== 'none')
      .map(platform => deliveries.find(item => item.post_id === post.id && item.platform === platform) || {post_id: post.id, platform, status: 'queued'});
  }

  function isHistoryPost(post) {
    const results = postDeliveries(post);
    return results.length > 0 && results.every(delivery => ['delivered', 'failed', 'cancelled', 'not_implemented', 'skipped'].includes(delivery.status));
  }

  function makePostCard(post, history = false) {
      const card = document.createElement('article');
      card.className = 'scheduled-post';
      card.dataset.postId = post.id;
      const date = postDate(post);
      const leading = scheduledLeading(post, date);
      const copy = document.createElement('div');
      copy.className = 'scheduled-copy';
      const metadata = document.createElement('div');
      metadata.className = 'scheduled-meta';
      const id = document.createElement('small');
      id.className = 'post-id';
      id.textContent = post.id;
      const timing = document.createElement('span');
      timing.className = 'post-time';
      const dateLabel = date.toLocaleDateString(undefined, {month: '2-digit', day: '2-digit', year: '2-digit'});
      const weekday = date.toLocaleDateString(undefined, {weekday: 'long'});
      const time = date.toLocaleTimeString(undefined, {hour: 'numeric', minute: '2-digit'});
      timing.textContent = window.matchMedia('(max-width: 600px)').matches ? `${dateLabel} ${weekday} ${time}` : `${dateLabel} · ${weekday} · ${time}`;
      metadata.append(id, timing);
      const title = document.createElement('strong');
      title.className = 'post-title';
      title.textContent = postPreview(post);
      title.title = post.text.trim();
      const body = document.createElement('div');
      body.className = 'scheduled-body';
      const status = document.createElement('div');
      status.className = 'destination-icons';
      const selectedPlatforms = platforms.filter(platform => post.destinations[platform] && post.destinations[platform] !== 'none');
      status.setAttribute('aria-label', selectedPlatforms.length ? selectedPlatforms.map(platform => `${platform} selected`).join(', ') : 'No destinations selected');
      for (const platform of selectedPlatforms) {
        const delivery = deliveries.find(item => item.post_id === post.id && item.platform === platform);
        const icon = document.createElement('span');
        icon.className = `queue-status ${colors[platform]} delivery-${delivery?.status || 'queued'}`;
        icon.innerHTML = `<i class="fa-brands fa-${icons[platform]}" aria-hidden="true"></i>`;
        icon.title = `${platform}: ${(delivery?.status || 'queued').replaceAll('_', ' ')}`;
        status.append(icon);
      }
      const controls = document.createElement('div');
      controls.className = 'scheduled-controls';
      controls.append(status);
      if (history) {
        const expand = document.createElement('span');
        expand.className = 'history-expand';
        expand.setAttribute('aria-hidden', 'true');
        controls.append(expand);
      } else {
        const publishNow = document.createElement('button');
        publishNow.type = 'button';
        publishNow.className = 'post-action';
        publishNow.textContent = 'Now';
        publishNow.title = 'Publish this scheduled post now';
        publishNow.addEventListener('click', async event => {
          event.stopPropagation();
          try {
            await api(`/api/posts/${encodeURIComponent(post.id)}/publish-now`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: '{}'});
            [posts, deliveries] = await Promise.all([readPosts(), readDeliveries()]);
            renderQueue();
            showToast(`${post.id} is ready to publish now.`);
          } catch (error) { showToast(error.message); }
        });
        controls.append(publishNow);
        const more = document.createElement('button');
        more.type = 'button';
        more.className = 'more';
        more.textContent = '•••';
        more.setAttribute('aria-label', `Edit post ${post.id}`);
        controls.append(more);
      }
      body.append(title, controls);
      copy.append(metadata, body);
      card.append(leading, copy);
      return card;
  }

  function makeHistoryCard(post) {
    const details = document.createElement('details');
    details.className = 'history-card';
    const summary = document.createElement('summary');
    summary.setAttribute('aria-label', `Show delivery details for ${post.id}`);
    summary.append(makePostCard(post, true));
    const list = document.createElement('div');
    list.className = 'history-deliveries';
    for (const delivery of postDeliveries(post)) {
      const row = document.createElement('div');
      row.className = 'history-delivery';
      const icon = document.createElement('span');
      icon.className = `queue-status ${colors[delivery.platform]} delivery-${delivery.status}`;
      icon.innerHTML = `<i class="fa-brands fa-${icons[delivery.platform]}" aria-hidden="true"></i>`;
      const name = document.createElement('span');
      name.textContent = delivery.platform[0].toUpperCase() + delivery.platform.slice(1);
      row.append(icon, name);
      if (delivery.status === 'delivered' && delivery.remote_url) {
        const link = document.createElement('a');
        link.href = delivery.remote_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'View post';
        link.setAttribute('aria-label', `View ${delivery.platform} post in a new tab`);
        row.append(link);
      } else {
        const result = document.createElement('span');
        result.className = `history-result${delivery.status === 'failed' ? ' failed' : ''}`;
        result.textContent = delivery.status === 'delivered' ? 'Sent' : delivery.status.replaceAll('_', ' ');
        if (delivery.error) result.title = delivery.error;
        row.append(result);
      }
      if (['failed', 'retry', 'cancelled'].includes(delivery.status)) {
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'delivery-action';
        retry.textContent = 'Retry';
        retry.addEventListener('click', async () => {
          if (!confirm(`Retry only ${delivery.platform}? Check the platform first to avoid a duplicate post.`)) return;
          try {
            await deliveryAction(post.id, delivery.platform, 'retry');
            deliveries = await readDeliveries();
            renderQueue();
            showToast(`${delivery.platform} delivery queued.`);
          } catch (error) { showToast(error.message); }
        });
        row.append(retry);
      } else if (['queued', 'retry'].includes(delivery.status)) {
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'delivery-action';
        cancel.textContent = 'Cancel';
        cancel.addEventListener('click', async () => {
          try { await deliveryAction(post.id, delivery.platform, 'cancel'); deliveries = await readDeliveries(); renderQueue(); }
          catch (error) { showToast(error.message); }
        });
        row.append(cancel);
      }
      if (delivery.attempts > 0) {
        const detailsButton = document.createElement('button');
        detailsButton.type = 'button';
        detailsButton.className = 'delivery-action';
        detailsButton.textContent = 'Attempts';
        detailsButton.addEventListener('click', async () => {
          let list = row.querySelector('.attempt-list');
          if (list) { list.remove(); return; }
          try {
            const attempts = await api(`/api/deliveries/${encodeURIComponent(post.id)}/${delivery.platform}/attempts`);
            list = document.createElement('div');
            list.className = 'attempt-list';
            if (!attempts.length) list.textContent = 'No attempt details were recorded for this older delivery.';
            for (const attempt of attempts) {
              const item = document.createElement('div');
              const heading = document.createElement('strong');
              heading.textContent = `#${attempt.attempt} · ${attempt.stage} · ${attempt.status}`;
              item.append(heading, document.createTextNode(` · ${new Date(attempt.started_at).toLocaleString()}${attempt.error ? ` · ${attempt.error}` : ''}`));
              list.append(item);
            }
            row.append(list);
          } catch (error) { showToast(error.message); }
        });
        row.append(detailsButton);
      }
      list.append(row);
    }
    details.append(summary, list);
    return details;
  }

  function addEmptyState(container, message) {
    const empty = document.createElement('p');
    empty.className = 'empty-post-list';
    empty.textContent = message;
    container.append(empty);
  }

  function renderQueue() {
    scheduledList.replaceChildren();
    historyList.replaceChildren();
    const scheduledPosts = posts.filter(post => !isHistoryPost(post)).sort((a, b) => postDate(a) - postDate(b));
    const historyPosts = posts.filter(isHistoryPost).sort((a, b) => postDate(b) - postDate(a));
    for (const post of scheduledPosts) scheduledList.append(makePostCard(post));
    for (const post of historyPosts) historyList.append(makeHistoryCard(post));
    if (!scheduledPosts.length) addEmptyState(scheduledList, 'No posts are currently scheduled or awaiting delivery.');
    if (!historyPosts.length) addEmptyState(historyList, 'Delivered and completed posts will appear here.');
  }

  async function saveComposer() {
    if (!text.value.trim() && !preview.children.length) { showToast('Write a post or attach media before saving.'); text.focus(); return; }
    const selections = Object.fromEntries(platforms.map(platform => [platform, document.querySelector(`#${platform}`).value]));
    if (Object.values(selections).every(value => value === 'none')) { showToast('Choose at least one destination.'); return; }
    try {
      const scheduledFor = document.querySelector('#scheduleTime').value;
      const oldPost = editingId ? await readPost(editingId) : null;
      const id = editingId || `PS-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      const media = await Promise.all([...preview.children].map(async card => {
        const file = card._file;
        return file ? await serializeMedia(file, card._alt || '') : null;
      }));
      const post = {id, text: text.value, destinations: selections, scheduledFor, createdAt: oldPost?.createdAt || new Date().toISOString(), media: media.filter(Boolean)};
      await writePost(post);
      [posts, deliveries] = await Promise.all([readPosts(), readDeliveries()]);
      renderQueue();
      resetComposer();
      showToast(`${oldPost ? 'Saved' : 'Queued'} post ${id} locally.`);
    } catch (error) { console.error(error); showToast(error.message || 'Could not save this post locally.'); }
  }

  function showQueueCalendar(kind = 'scheduled') {
    let dialog = document.querySelector('#calendarDialog');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'calendarDialog';
      dialog.className = 'calendar-dialog';
      document.body.append(dialog);
    }
    dialog.replaceChildren();
    const close = document.createElement('button');
    close.className = 'calendar-close';
    close.type = 'button';
    close.setAttribute('aria-label', 'Close calendar');
    close.textContent = '×';
    close.addEventListener('click', () => dialog.close());
    const heading = document.createElement('h2');
    const calendarPosts = posts.filter(post => kind === 'history' ? isHistoryPost(post) : !isHistoryPost(post));
    heading.textContent = `${kind === 'history' ? 'Post History' : 'Scheduled Posts'} · ${calendarMonth.toLocaleDateString(undefined, {month: 'long', year: 'numeric'})}`;
    const grid = document.createElement('div');
    grid.className = 'calendar-grid';
    for (const label of ['S', 'M', 'T', 'W', 'T', 'F', 'S']) {
      const weekday = document.createElement('span');
      weekday.className = 'day';
      weekday.textContent = label;
      grid.append(weekday);
    }
    const year = calendarMonth.getFullYear(), month = calendarMonth.getMonth();
    for (let blank = 0; blank < new Date(year, month, 1).getDay(); blank++) grid.append(document.createElement('span'));
    const days = new Date(year, month + 1, 0).getDate();
    for (let day = 1; day <= days; day++) {
      const cell = document.createElement('span');
      const amount = calendarPosts.filter(post => { const date = postDate(post); return date.getFullYear() === year && date.getMonth() === month && date.getDate() === day; }).length;
      if (amount) {
        cell.className = 'calendar-post';
        const number = document.createElement('b');
        number.textContent = String(day);
        const count = document.createElement('small');
        count.textContent = String(amount);
        cell.append(number, count);
        cell.setAttribute('aria-label', `${day}: ${amount} post${amount === 1 ? '' : 's'}`);
      } else cell.textContent = String(day);
      grid.append(cell);
    }
    dialog.append(close, heading, grid);
    dialog.showModal();
  }

  document.addEventListener('submit', event => {
    if (event.target !== form) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    saveComposer();
  }, true);

  document.addEventListener('click', event => {
    if (event.target.closest('#clearButton')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      resetComposer();
      showToast('Draft cleared.');
    } else if (event.target.closest('.calendar-button')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      showQueueCalendar(event.target.closest('.calendar-button').dataset.calendar);
    } else if (event.target.closest('.more')) {
      const card = event.target.closest('.scheduled-post');
      if (card?.dataset.postId) openQueuedPost(card.dataset.postId);
    }
  }, true);

  function connectionDialog() {
    let dialog = document.querySelector('#blueskyConnectionDialog');
    if (dialog) return dialog;
    dialog = document.createElement('dialog');
    dialog.id = 'blueskyConnectionDialog';
    dialog.className = 'connection-dialog';
    dialog.innerHTML = `<button class="dialog-close" type="button" aria-label="Close Bluesky connection">×</button><h2>Bluesky connection</h2><p class="connection-state" role="status">Not connected</p><form class="connection-form"><label>Handle<input name="handle" autocomplete="username" placeholder="your-handle.bsky.social" required></label><button class="connection-save bluesky-oauth" type="button">Continue with Bluesky OAuth</button><small class="meta-help">You'll approve Polysocial in Bluesky. No app password is needed.</small><details class="meta-advanced"><summary>Use an app password instead</summary><div class="meta-advanced-content"><label>Bluesky app password<input name="password" type="password" autocomplete="current-password"></label><label class="auth-factor" hidden>Email sign-in code<input name="authFactorToken" inputmode="numeric" autocomplete="one-time-code"></label><button class="connection-save" type="submit">Save app-password connection</button></div></details><label class="delivery-toggle"><input name="delivery" type="checkbox"><span>Enable scheduled delivery</span></label><div class="connection-actions"><button class="connection-disconnect" type="button" hidden>Disconnect</button></div></form>`;
    document.body.append(dialog);
    dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
    dialog.querySelector('.connection-disconnect').addEventListener('click', async () => {
      if (!confirm('Disconnect Bluesky and disable delivery?')) return;
      const response = await fetch('/api/connections/bluesky', {method: 'DELETE'});
      if (!response.ok) return showToast('Could not disconnect Bluesky.');
      dialog.querySelector('[name=password]').value = '';
      await refreshConnections(dialog);
      showToast('Bluesky disconnected.');
    });
    dialog.querySelector('.bluesky-oauth').addEventListener('click', () => {
      const handle = dialog.querySelector('[name=handle]').value.trim();
      if (!handle) {
        dialog.querySelector('.connection-state').textContent = 'Enter your Bluesky handle first.';
        return;
      }
      window.location.assign(`/api/oauth/bluesky/start?handle=${encodeURIComponent(handle)}`);
    });
    dialog.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const state = dialog.querySelector('.connection-state');
      state.textContent = 'Testing connection…';
      const response = await fetch('/api/connections/bluesky', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({handle: data.get('handle'), password: data.get('password'), authFactorToken: data.get('authFactorToken'), service: 'https://bsky.social'})});
      const result = await response.json();
      if (!response.ok) {
        const needsCode = String(result.error).includes('AuthFactorTokenRequired');
        dialog.querySelector('.auth-factor').hidden = !needsCode;
        state.textContent = needsCode ? 'Bluesky emailed you a sign-in code. Enter it below and save again.' : (result.error || 'Connection failed.');
        if (needsCode) dialog.querySelector('[name=authFactorToken]').focus();
        return;
      }
      dialog.querySelector('[name=password]').value = '';
      dialog.querySelector('[name=authFactorToken]').value = '';
      dialog.querySelector('.auth-factor').hidden = true;
      const enabled = Boolean(data.get('delivery'));
      await fetch('/api/settings/delivery', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})});
      await refreshConnections(dialog);
      showToast(`Bluesky connected as ${result.displayName}.`);
    });
    return dialog;
  }

  function metaConnectionDialog() {
    let dialog = document.querySelector('#metaConnectionDialog');
    if (dialog) return dialog;
    dialog = document.createElement('dialog');
    dialog.id = 'metaConnectionDialog';
    dialog.className = 'connection-dialog';
    dialog.innerHTML = `<button class="dialog-close" type="button" aria-label="Close Meta connection">×</button><h2>Facebook &amp; Instagram</h2><p class="meta-intro">One Facebook sign-in connects a Page and the professional Instagram account linked to it.</p><div class="meta-accounts"><div class="meta-account" data-meta-account="facebook"><span class="meta-account-icon fb"><i class="fa-brands fa-facebook-f" aria-hidden="true"></i></span><span><strong>Facebook Page</strong><small>Choose after authorization</small></span><span class="meta-account-status">Not connected</span></div><div class="meta-account" data-meta-account="instagram"><span class="meta-account-icon ig"><i class="fa-brands fa-instagram" aria-hidden="true"></i></span><span><strong>Instagram</strong><small>Linked professional account</small></span><span class="meta-account-status">Not connected</span></div></div><p class="connection-state" role="status">Sign in with the personal Facebook profile that manages the Page you want to use.</p><form class="connection-form meta-config"><label>Meta App ID<input name="appIdDisplay" inputmode="numeric" autocomplete="off" required></label><label>Facebook Login for Business Configuration ID<input name="configIdDisplay" inputmode="numeric" autocomplete="off" required><small class="meta-help">Create this configuration in your own Meta developer app.</small></label><label>Meta App Secret<input name="appSecret" type="password" autocomplete="off" required><small class="meta-help">Stored encrypted on this computer and never returned to the browser.</small></label><p class="meta-callback">OAuth callback:<br><strong class="meta-redirect"></strong></p><div class="connection-actions"><button class="connection-disconnect" type="button" hidden>Disconnect accounts</button><button class="connection-save" type="submit">Authorize Meta accounts</button></div><details class="meta-advanced"><summary>Development-token fallback</summary><div class="meta-advanced-content"><label>Facebook user access token<input name="accessToken" type="password" autocomplete="off"><small class="meta-help">The token needs Page list, read, and publish permissions.</small></label><div class="connection-actions"><button class="connection-save meta-token-save" type="button">Validate access token</button></div></div></details></form><form class="connection-form meta-select" hidden><p class="meta-help">Choose the managed Facebook Page to use. A linked professional Instagram account will be connected automatically.</p><label>Managed Facebook Page<select name="pageId" class="account-select" required></select></label><div class="connection-actions"><button class="connection-save" type="submit">Use selected accounts</button></div></form>`;
    document.body.append(dialog);
    dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
    dialog.querySelector('.meta-redirect').textContent = `${publicConfig.publicOrigin || location.origin}/api/oauth/meta/callback`;
    dialog.querySelector('[name=appIdDisplay]').value = publicConfig.metaAppId || '';
    dialog.querySelector('[name=configIdDisplay]').value = publicConfig.metaConfigId || '';
    dialog.querySelector('.meta-config').addEventListener('submit', async event => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const appId = String(data.get('appIdDisplay')).trim();
      const configId = String(data.get('configIdDisplay')).trim();
      const response = await fetch('/api/connections/meta/config', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({appId, configId, appSecret: data.get('appSecret')})});
      const result = await response.json();
      if (!response.ok) { dialog.querySelector('.connection-state').textContent = result.error || 'Could not save the Meta app configuration.'; return; }
      location.assign(result.authorizationUrl);
    });
    dialog.querySelector('.meta-token-save').addEventListener('click', async () => {
      const form = dialog.querySelector('.meta-config');
      const data = new FormData(form);
      const state = dialog.querySelector('.connection-state');
      state.textContent = 'Validating token and finding managed Pages…';
      const appId = String(data.get('appIdDisplay')).trim();
      const response = await fetch('/api/connections/meta/token', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({appId, appSecret: data.get('appSecret'), accessToken: data.get('accessToken')})});
      const result = await response.json();
      if (!response.ok) { state.textContent = result.error || 'Meta could not validate that access token.'; return; }
      form.querySelector('[name=accessToken]').value = '';
      await loadMetaPages(dialog);
    });
    dialog.querySelector('.connection-disconnect').addEventListener('click', async () => {
      if (!confirm('Disconnect both Facebook and Instagram and remove their locally stored credentials?')) return;
      const response = await fetch('/api/connections/meta', {method: 'DELETE'});
      if (!response.ok) return showToast('Could not disconnect Facebook and Instagram.');
      await refreshConnections();
      showToast('Facebook and Instagram disconnected.');
    });
    dialog.querySelector('.meta-select').addEventListener('submit', async event => {
      event.preventDefault();
      const pageId = new FormData(event.currentTarget).get('pageId');
      const response = await fetch('/api/connections/meta/select', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pageId})});
      const result = await response.json();
      if (!response.ok) { dialog.querySelector('.connection-state').textContent = result.error || 'Could not connect the selected Page.'; return; }
      history.replaceState({}, '', '/');
      await refreshConnections();
      dialog.close();
      showToast(`Connected Facebook as ${result.facebook}${result.instagram?.username ? ` and Instagram as @${result.instagram.username}` : '. No linked professional Instagram account was found.'}`);
    });
    return dialog;
  }

  async function loadMetaPages(dialog) {
    const response = await fetch('/api/connections/meta/pending', {cache: 'no-store'});
    if (!response.ok) return false;
    const result = await response.json();
    if (!result.pages.length) {
      dialog.querySelector('.connection-state').textContent = 'Meta returned no Pages. Confirm that this account manages the Page and granted all requested permissions.';
      return false;
    }
    const select = dialog.querySelector('[name=pageId]');
    select.replaceChildren(...result.pages.map(page => {
      const option = document.createElement('option');
      option.value = page.id;
      option.textContent = `${page.name}${page.instagram?.username ? ` · @${page.instagram.username}` : ' · no linked Instagram'}`;
      return option;
    }));
    dialog.querySelector('.meta-config').hidden = true;
    dialog.querySelector('.meta-select').hidden = false;
    dialog.querySelector('.connection-state').textContent = 'Authorization succeeded. Choose the Facebook Page Polysocial should publish to.';
    return true;
  }

  function threadsConnectionDialog() {
    let dialog = document.querySelector('#threadsConnectionDialog');
    if (dialog) return dialog;
    dialog = document.createElement('dialog');
    dialog.id = 'threadsConnectionDialog';
    dialog.className = 'connection-dialog';
    dialog.innerHTML = `<button class="dialog-close" type="button" aria-label="Close Threads connection">×</button><h2>Threads connection</h2><p class="connection-state" role="status">Connect your own Threads API app with OAuth.</p><form class="connection-form"><label>Threads App ID<input name="appId" inputmode="numeric" autocomplete="off" required><small>This is the Threads App ID, not a Facebook configuration ID.</small></label><label>Threads App Secret<input name="appSecret" type="password" autocomplete="off" required></label><p>Threads OAuth callback:<br><strong class="threads-redirect"></strong></p><div class="connection-actions"><button class="connection-save" type="submit">Continue with Threads OAuth</button></div><div class="connection-state">Development-token fallback</div><label>Threads access token<input name="accessToken" type="password" autocomplete="off"><small>It is validated and encrypted locally.</small></label><div class="connection-actions"><button class="connection-disconnect" type="button" hidden>Disconnect</button><button class="connection-save threads-token-save" type="button">Connect access token</button></div></form>`;
    document.body.append(dialog);
    dialog.querySelector('.threads-redirect').textContent = `${publicConfig.publicOrigin || location.origin}/api/oauth/threads/callback`;
    dialog.querySelector('[name=appId]').value = publicConfig.threadsAppId || '';
    dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
    dialog.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const response = await fetch('/api/connections/threads/config', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({appId: data.get('appId'), appSecret: data.get('appSecret')})});
      const result = await response.json();
      if (!response.ok) { dialog.querySelector('.connection-state').textContent = result.error || 'Could not save the Threads app configuration.'; return; }
      location.assign(result.authorizationUrl);
    });
    dialog.querySelector('.threads-token-save').addEventListener('click', async () => {
      const form = dialog.querySelector('form');
      const data = new FormData(form);
      const state = dialog.querySelector('.connection-state');
      state.textContent = 'Validating Threads access token…';
      const response = await fetch('/api/connections/threads/token', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({appId: data.get('appId'), appSecret: data.get('appSecret'), accessToken: data.get('accessToken')})});
      const result = await response.json();
      if (!response.ok) { state.textContent = result.error || 'Threads could not validate that access token.'; return; }
      form.querySelector('[name=appSecret]').value = '';
      form.querySelector('[name=accessToken]').value = '';
      await refreshConnections();
      showToast(`Threads connected as ${result.displayName}.`);
    });
    dialog.querySelector('.connection-disconnect').addEventListener('click', async () => {
      if (!confirm('Disconnect Threads and remove its locally stored credentials?')) return;
      const response = await fetch('/api/connections/threads', {method: 'DELETE'});
      if (!response.ok) return showToast('Could not disconnect Threads.');
      await refreshConnections();
      showToast('Threads disconnected.');
    });
    return dialog;
  }

  async function refreshConnections(dialog = null) {
    const response = await fetch('/api/connections', {cache: 'no-store'});
    if (!response.ok) return;
    const result = await response.json();
    const queueControl = document.querySelector('#queueControl');
    if (queueControl) {
      queueControl.querySelector('strong').textContent = result.deliveryEnabled ? 'Delivery queue running' : 'Delivery queue paused';
      queueControl.querySelector('button').textContent = result.deliveryEnabled ? 'Pause queue' : 'Resume queue';
      queueControl.dataset.enabled = String(Boolean(result.deliveryEnabled));
    }
    for (const connection of result.connections) {
      const row = document.querySelector(`.setting-edit[data-platform="${connection.platform}"]`)?.closest('.setting-line');
      if (!row) continue;
      let health = row.querySelector('.connection-health');
      if (!health) {
        health = document.createElement('span');
        health.className = 'connection-health';
        row.querySelector('span').append(health);
      }
      health.className = `connection-health ${connection.health || ''}`;
      health.textContent = connection.health === 'expired' ? 'Token expired' : connection.health === 'expiring' ? 'Token expires soon' : connection.last_checked_at ? 'Connection verified' : '';
    }
    const bluesky = result.connections.find(connection => connection.platform === 'bluesky');
    for (const platform of ['facebook', 'instagram', 'threads']) {
      const connection = result.connections.find(item => item.platform === platform);
      const row = document.querySelector(`.setting-edit[data-platform="${platform}"]`)?.closest('.setting-line');
      if (row) row.querySelector('small').textContent = connection?.display_name || 'Not connected';
      const option = document.querySelector(`#${platform} option[value="connected"]`);
      if (option) option.textContent = connection?.display_name || 'Connect in Settings';
    }
    const row = document.querySelector('.setting-edit[data-platform="bluesky"]')?.closest('.setting-line');
    if (row) row.querySelector('small').textContent = bluesky?.display_name || 'Not connected';
    const option = document.querySelector('#bluesky option[value="connected"]');
    if (option) option.textContent = bluesky?.display_name || 'Connect in Settings';
    if (dialog) {
      dialog.querySelector('.connection-state').textContent = bluesky ? `Connected as ${bluesky.display_name}. Credentials are protected by Windows DPAPI.` : (result.vaultAvailable ? 'Not connected. Use a Bluesky app password.' : 'Secure credential storage is unavailable.');
      dialog.querySelector('[name=handle]').value = (bluesky?.display_name || '').replace(/^@/, '');
      dialog.querySelector('[name=delivery]').checked = Boolean(result.deliveryEnabled);
      dialog.querySelector('.connection-disconnect').hidden = !bluesky;
      dialog.querySelector('.connection-save').disabled = !result.vaultAvailable;
    }
    const threadsDialog = document.querySelector('#threadsConnectionDialog');
    if (threadsDialog) {
      const threads = result.connections.find(connection => connection.platform === 'threads');
      threadsDialog.querySelector('.connection-state').textContent = threads ? `Connected as ${threads.display_name}. Token and app credentials are protected by Windows DPAPI.` : 'Not connected. Threads uses its own App ID, App Secret, and OAuth callback.';
      threadsDialog.querySelector('.connection-disconnect').hidden = !threads;
      threadsDialog.querySelector('.connection-save').disabled = !result.vaultAvailable;
    }
    const metaDialog = document.querySelector('#metaConnectionDialog');
    if (metaDialog) {
      const facebook = result.connections.find(connection => connection.platform === 'facebook');
      const instagram = result.connections.find(connection => connection.platform === 'instagram');
      for (const [platform, connection] of [['facebook', facebook], ['instagram', instagram]]) {
        const account = metaDialog.querySelector(`[data-meta-account="${platform}"]`);
        const status = account?.querySelector('.meta-account-status');
        if (status) {
          status.textContent = connection ? 'Connected' : 'Not connected';
          status.classList.toggle('connected', Boolean(connection));
        }
        if (connection && account) account.querySelector('small').textContent = connection.display_name;
      }
      metaDialog.querySelector('.connection-state').textContent = facebook ? `Connected to ${facebook.display_name}${instagram ? ` and ${instagram.display_name}` : '. Meta did not return a linked Instagram account.'}` : 'Sign in to Meta so Polysocial can find and confirm these accounts.';
      metaDialog.querySelector('.connection-disconnect').hidden = !facebook && !instagram;
      metaDialog.querySelector('.connection-save').disabled = !result.vaultAvailable;
    }
  }

  document.querySelectorAll('.setting-edit[data-platform]').forEach(button => button.addEventListener('click', async () => {
    const platform = button.dataset.platform;
    document.querySelector('#settingsDialog')?.close();
    if (platform === 'facebook' || platform === 'instagram') {
      const dialog = metaConnectionDialog();
      dialog.querySelector('.meta-config').hidden = false;
      dialog.querySelector('.meta-select').hidden = true;
      await refreshConnections();
      dialog.showModal();
      return;
    }
    if (platform === 'threads') {
      const dialog = threadsConnectionDialog();
      await refreshConnections();
      dialog.showModal();
      return;
    }
    const dialog = connectionDialog();
    await refreshConnections(dialog);
    dialog.showModal();
  }));

  document.querySelectorAll('.setting-line').forEach(row => {
    const edit = row.querySelector('.setting-edit[data-platform]');
    if (!edit) return;
    const test = document.createElement('button');
    test.type = 'button';
    test.className = 'setting-test';
    test.textContent = 'Test';
    test.addEventListener('click', async () => {
      test.disabled = true;
      try { await api(`/api/connections/${edit.dataset.platform}/test`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: '{}'}); showToast(`${edit.dataset.platform} connection is healthy.`); await refreshConnections(); }
      catch (error) { showToast(error.message); }
      finally { test.disabled = false; }
    });
    row.insertBefore(test, edit);
  });

  const settingsDialog = document.querySelector('#settingsDialog');
  if (settingsDialog && !document.querySelector('#queueControl')) {
    const control = document.createElement('div');
    control.id = 'queueControl';
    control.className = 'queue-control';
    const label = document.createElement('strong');
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.addEventListener('click', async () => {
      const enabled = control.dataset.enabled !== 'true';
      try {
        await api('/api/settings/delivery', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})});
        await refreshConnections();
        showToast(enabled ? 'Delivery queue resumed.' : 'Delivery queue paused.');
      } catch (error) { showToast(error.message); }
    });
    control.append(label, toggle);
    settingsDialog.append(control);
  }

  async function initialize() {
    try {
      [posts, deliveries, publicConfig] = await Promise.all([readPosts(), readDeliveries(), api('/api/config')]);
      renderQueue();
      await refreshConnections();
      const parameters = new URLSearchParams(location.search);
      if (parameters.get('meta') === 'select') {
        const dialog = metaConnectionDialog();
        await loadMetaPages(dialog);
        dialog.showModal();
      } else if (parameters.get('meta_error')) {
        showToast(`Meta connection failed: ${parameters.get('meta_error')}`);
        history.replaceState({}, '', '/');
      } else if (parameters.get('threads') === 'connected') {
        showToast('Threads connected successfully.');
        history.replaceState({}, '', '/');
      } else if (parameters.get('threads_error')) {
        showToast(`Threads connection failed: ${parameters.get('threads_error')}`);
        history.replaceState({}, '', '/');
      }
    } catch (error) { console.error(error); showToast('Local queue storage is unavailable.'); }
  }
  scheduledList.replaceChildren();
  historyList.replaceChildren();
  setBanner(null);
  publish.setAttribute('aria-label', 'Publish post');
  initialization = initialize();
  setInterval(async () => {
    try { deliveries = await readDeliveries(); renderQueue(); } catch {}
  }, 10000);
});

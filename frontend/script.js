const store = {
  get(key, fallback){ try{return JSON.parse(localStorage.getItem('birge_'+key)) ?? fallback}catch{return fallback} },
  set(key, value){localStorage.setItem('birge_'+key, JSON.stringify(value))}
};

let foodItems = [], homeFoodItems = [];
let foodLoading = true, foodError = '', foodRequest = 0, foodFiltersReady = false;
// The FastAPI server is the source of truth for all three interactive sections.
let lostItems = [], skills = [], confessions = [];
const ACTOR_ID = 101; // Demo identity only; not secure authentication.
// Local previews connect to FastAPI; the served website uses its own origin.
const localPreview = location.protocol === 'file:' || (
  ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname) &&
  location.port !== '8000' && !/^\/(app|static)(\/|$)/.test(location.pathname)
);
const API = localPreview ? 'http://127.0.0.1:8000' : '';
const fieldLabels = {
  name: 'Атауы', place: 'Орны', desc: 'Сипаттамасы', person: 'Есіміңіз',
  detail: 'Сипаттамасы', exchange: 'Алмасу дағдысы', text: 'Хабарлама'
};
async function api(path, options={}) {
  let response;
  try {
    response = await fetch(API+path, { ...options, headers: {...(options.body instanceof FormData ? {} : {'Content-Type':'application/json'}),...(options.headers||{})} });
  } catch {
    throw new Error('Серверге қосылу мүмкін емес. FastAPI іске қосылғанын тексеріңіз.');
  }
  if (response.status===204) return null;
  const result = await response.json().catch(()=>null);
  if (!response.ok) {
    const detail = result?.detail;
    const message = Array.isArray(detail)
      ? detail.map(error => `${fieldLabels[error.loc?.at(-1)] || error.loc?.at(-1) || 'Өріс'}: ${error.msg}`).join('; ')
      : typeof detail === 'string' ? detail : 'Қате: ' + response.status;
    throw new Error(message);
  }
  if (result === null) {
    throw new Error('API жауабы дұрыс емес. Сайтты FastAPI арқылы ашыңыз: http://127.0.0.1:8000/app/');
  }
  return result;
}
async function loadBackend(){
    const [lost, skillList, posts] = await Promise.all([api('/lost-items'),api('/skills'),api('/confessions')]);
    lostItems = lost.map(x=>({...x,date:'Жарияланды'}));
    skills = skillList.map(x=>({...x,initial:x.person?.[0]?.toUpperCase()||'?',tag:'COMMUNITY'}));
    confessions = posts.map(x=>({...x,time:'Жарияланды'})).reverse();
    refresh();
}
function showError(err){toast(err.message||'Сұрау орындалмады')}

let lostFilter='all', skillFilter='all';

let toastTimer;
function toast(msg){const t=$('#toast');clearTimeout(toastTimer);t.textContent=msg;t.classList.add('show');toastTimer=setTimeout(()=>t.classList.remove('show'),5000)}
function navigate(page){
 $$('.page').forEach(p=>p.classList.toggle('active',p.id===`page-${page}`));
 $$('.nav-link').forEach(button=>{const active=button.dataset.page===page;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current')});
 setNavOpen(false);
 const labels={home:'Басты бет',food:'Däm',lost:'Lost & Found',skills:'SkillQos',confess:'Ishimде'};
 $('#crumbCurrent').textContent=labels[page]||'BIRGE';
 document.title=`${labels[page]||'Басты бет'} · BIRGE — SDU кампус қауымдастығы`;
 const heading=$('h1',$('#page-'+page));
 if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true})}
 window.scrollTo({top:0,behavior:'instant'});
}
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page)));
$$('[data-go]').forEach(el=>el.addEventListener('click',()=>navigate(el.dataset.go)));

$('#themeToggle').addEventListener('click',()=>{document.body.classList.toggle('dark');store.set('dark',document.body.classList.contains('dark'))});
if(store.get('dark',false))document.body.classList.add('dark');
$('#todayDate').textContent=new Intl.DateTimeFormat('kk-KZ',{day:'numeric',month:'long'}).format(new Date())+' · SDU';

function renderFood(){
 const grid=$('#foodGrid');
 grid.setAttribute('aria-busy',String(foodLoading));
 renderHomeMenu();
 if(foodLoading){grid.innerHTML=Array.from({length:6},()=>'<div class="food-card skeleton" aria-label="Жүктелуде…"></div>').join('');return}
 if(foodError){grid.innerHTML=`<div class="empty-state" role="alert">${escapeHtml(foodError)}<p><button class="primary-button" id="retryFood">Қайта көру</button></p></div>`;$('#retryFood').onclick=()=>loadFood();return}
 const sort=$('#foodSort').value;
 const items=[...foodItems].sort((a,b)=>sort==='asc'?a.price-b.price:sort==='desc'?b.price-a.price:0);
 grid.innerHTML=items.length?items.map(x=>`<article class="food-card"><div class="food-cover"><img src="${escapeHtml(assetUrl(x.image_url))}" alt="${escapeHtml(x.image_alt)}" loading="lazy"><span>${foodPhotoLabel(x.image_kind)}</span></div><div class="food-body"><h3>${escapeHtml(x.name)}</h3>${x.description?`<p>${escapeHtml(x.description)}</p>`:''}<div class="food-meta"><span>${escapeHtml(x.canteen)}</span><b>${formatPrice(x.price)}</b></div><div class="food-meta"><span>${escapeHtml(x.category)}</span><span class="availability ${x.available?'':'unavailable'}">${x.available?'Қолда бар':'Қазір жоқ'}</span></div><button class="outline-button full" data-food-detail="${x.id}">Толығырақ ${icon('arrow-up-right')}</button></div></article>`).join(''):'<div class="empty-state">Тағам табылмады. Сүзгілерді тазалап көріңіз.</div>';
 $$('[data-food-detail]').forEach(button=>button.onclick=()=>showFoodDetail(Number(button.dataset.foodDetail)));
 imageFallbacks(grid);
}
const formatPrice=value=>new Intl.NumberFormat('kk-KZ').format(value)+' ₸';
function foodPhotoLabel(kind, detail=false){return kind==='placeholder'?'Фото жоқ':kind==='authentic'?'Мәзір фотосы':detail?'Үлгі фото · Асхананың нақты фотосы емес':'Үлгі фото'}
function assetUrl(url){return API+url}
function imageFallbacks(root){$$('img',root).forEach(img=>img.onerror=()=>{img.onerror=null;img.src=assetUrl('/static/images/food/placeholder.svg');img.alt='Фото қолжетімсіз';const cover=img.closest('.food-cover, .board-photo');const label=cover?.querySelector('span, small');if(label)label.textContent='Фото қолжетімсіз'})}
async function loadFood(initial=false){
 const request=++foodRequest;
 foodLoading=true;foodError='';renderFood();
 const params=new URLSearchParams();
 for(const [key,id] of [['search','foodSearch'],['canteen','foodCanteen'],['category','foodCategory']]){const value=$('#'+id).value.trim();if(value)params.set(key,value)}
 try{
  const items=await api('/food?'+params);
  if(request!==foodRequest)return;
  foodItems=items;
  if(initial||!homeFoodItems.length)homeFoodItems=items;
  if(initial||!foodFiltersReady){
   for(const [field,id] of [['canteen','foodCanteen'],['category','foodCategory']]){
    const select=$('#'+id), selected=select.value;
    select.innerHTML='<option value="">Барлығы</option>'+[...new Set(items.map(x=>x[field]))].map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');select.value=selected;
   }
   $('#foodCount').textContent=items.length;
   foodFiltersReady=true;
  }
 }catch(error){if(request===foodRequest)foodError=error.message}
 finally{if(request===foodRequest){foodLoading=false;renderFood()}}
}
let foodTimer;
$('#foodSearch').addEventListener('input',()=>{clearTimeout(foodTimer);foodRequest++;foodLoading=true;renderFood();foodTimer=setTimeout(()=>loadFood(),250)});
for(const id of ['foodCanteen','foodCategory'])$('#'+id).addEventListener('change',()=>loadFood());
$('#foodSort').addEventListener('change',renderFood);
$('#clearFoodFilters').onclick=()=>{clearTimeout(foodTimer);for(const id of ['foodSearch','foodCanteen','foodCategory','foodSort'])$('#'+id).value='';loadFood(true)};
async function showFoodDetail(id){
 try{const x=await api(`/food/${id}`);openDetail(`<h2 id="detailTitle">${escapeHtml(x.name)}</h2><div class="food-cover detail-cover"><img src="${escapeHtml(assetUrl(x.image_url))}" alt="${escapeHtml(x.image_alt)}"><span>${foodPhotoLabel(x.image_kind,true)}</span></div><p>${escapeHtml(x.description)}</p><p>${escapeHtml(x.canteen)} · ${escapeHtml(x.category)}</p><p><b>${formatPrice(x.price)}</b> · ${x.available?'Қолда бар':'Қазір жоқ'}</p>${x.image_credit?`<p class="demo-note">${escapeHtml(x.image_credit)} · <a href="/static/images/food/ATTRIBUTION.md" target="_blank" rel="noopener">Дереккөз және лицензия</a></p>`:''}`)}catch(error){showError(error)}
}

function renderLost(){
 const q=$('#lostSearch').value.toLowerCase();
 const items=lostItems.filter(x=>(lostFilter==='all'||x.status===lostFilter)&&(x.name+' '+x.place+' '+x.desc).toLowerCase().includes(q));
 $('#lostGrid').innerHTML=items.length?items.map(x=>`<article class="listing-card"><div class="listing-cover">${x.images?.length?`<img src="${escapeHtml(assetUrl(x.images[0].url))}" alt="${escapeHtml(x.name)}" loading="lazy">`:'<small class="photo-placeholder">Фото жоқ</small>'}<span class="status-label ${x.status}">${x.resolved?'Аяқталды':x.status==='lost'?'Жоғалған':'Табылған'}</span></div><div class="listing-body"><h3>${escapeHtml(x.name)}</h3><p>${escapeHtml(x.desc)}</p><button class="outline-button full" data-lost-detail="${x.id}">Толығырақ · ${x.images?.length||0} фото</button><div class="listing-foot"><small>${icon('map-pin')} ${escapeHtml(x.place)} · ${escapeHtml(x.date)}</small><button class="outline-button" data-contact="${x.id}">Аяқталды деп белгілеу</button></div></div></article>`).join(''):'<div class="empty-state">Бұл бөлімде әзірге жарияланым жоқ.</div>';
 $$('[data-lost-detail]').forEach(button=>button.onclick=()=>showLostDetail(Number(button.dataset.lostDetail)));
 imageFallbacks($('#lostGrid'));
 $$('[data-contact]').forEach(b=>b.addEventListener('click',async()=>{
  const item=lostItems.find(x=>x.id===Number(b.dataset.contact));
  if(!item)return;
  if(item.owner_id!==ACTOR_ID){toast('Бұл хабарландыруды тек иесі аяқтай алады.');return}
  if(!await askConfirm('Зат табылды / қайтарылды деп белгілеу керек пе?', 'Аяқталды деп белгілеу'))return;
  try{await api(`/lost-items/${item.id}/resolve?actor_id=${ACTOR_ID}`,{method:'POST'});await loadBackend();toast('Хабарландыру аяқталды')}catch(err){showError(err)}
}));
}
$('#lostSearch').addEventListener('input',renderLost);
$$('#lostFilters button').forEach(b=>b.addEventListener('click',()=>{lostFilter=b.dataset.filter;$$('#lostFilters button').forEach(x=>x.classList.toggle('active',x===b));renderLost()}));

function renderSkills(){
 const q=$('#skillSearch').value.toLowerCase();
 const items=skills.filter(x=>(skillFilter==='all'||x.kind===skillFilter)&&(x.name+' '+x.person+' '+x.detail+' '+x.tag).toLowerCase().includes(q));
 $('#skillGrid').innerHTML=items.length?items.map(x=>`<article class="skill-card"><div class="skill-body"><div class="skill-head"><div class="skill-avatar">${escapeHtml(x.initial)}</div><div><b >${escapeHtml(x.person)}</b><small>SDU студенті</small></div></div><span class="skill-type">${x.kind==='teach'?'Үйретемін':'Үйренемін'}</span><h3>${escapeHtml(x.name)}</h3><p>${escapeHtml(x.detail)}</p><div class="skill-bottom"><span>${icon('repeat-2')} ${escapeHtml(x.exchange)}</span><button class="outline-button" data-skill="${x.id}">${x.owner_id===ACTOR_ID?'Өтінімдерді көру':'Ұсыныс жіберу'}</button></div></div></article>`).join(''):'<div class="empty-state">Сұранысқа сай дағды табылмады.</div>';
 $$('[data-skill]').forEach(b=>b.addEventListener('click',async()=>{
  const id=Number(b.dataset.skill), item=skills.find(x=>x.id===id);
  if(!item)return;
  if(item.owner_id===ACTOR_ID){
    try{
      const requests=await api(`/skills/${id}/requests?actor_id=${ACTOR_ID}`);
      if(!requests.length){toast('Әзірге өтінім жоқ');return}
      const pending=requests.filter(x=>x.status==='pending');
      if(!pending.length){toast('Барлық өтінімдер қаралды');return}
      const request=pending[0];
      const decision=await presentAction({title:`Өтінім #${request.id}`,description:request.message,choices:[{id:'cancel',label:'Кейінірек'},{id:'rejected',label:'Бас тарту'},{id:'accepted',label:'Қабылдау',primary:true}]});
      if(!['accepted','rejected'].includes(decision))return;
      const accepted=decision==='accepted';
      await api(`/skills/${id}/requests/${request.id}?actor_id=${ACTOR_ID}&decision=${accepted?'accepted':'rejected'}`,{method:'PATCH'});
      toast(accepted?'Өтінім қабылданды':'Өтінім қабылданбады');
    }catch(err){showError(err)}
  }else{
    const message=await askText('Өтінімге хабарлама жазыңыз','Бірге үйренгім келеді');
    if(message===null)return;
    try{await api(`/skills/${id}/requests`,{method:'POST',body:JSON.stringify({applicant_id:ACTOR_ID,message})});toast('Өтінім жіберілді')}catch(err){showError(err)}
  }
}));
}
$('#skillSearch').addEventListener('input',renderSkills);
$$('#skillFilters button').forEach(b=>b.addEventListener('click',()=>{skillFilter=b.dataset.filter;$$('#skillFilters button').forEach(x=>x.classList.toggle('active',x===b));renderSkills()}));

function renderConfessions(){
 $('#confessFeed').innerHTML=confessions.length?confessions.map(x=>`<article class="confess-card"><div class="confess-top"><div class="anonymous-label"><span>${icon('message-circle')}</span> Анонимді студент</div><time>${escapeHtml(x.time)}</time></div><p>${escapeHtml(x.text)}</p><div class="confess-actions"><button class="reaction" data-like="${x.id}">${icon('heart')} <span>${x.likes}</span> Қолдау</button><button class="reaction" data-report="${x.id}">${icon('flag')} Шағымдану</button></div></article>`).join(''):'<div class="empty-state">Алғашқы ойыңызды бөлісіңіз.</div>';
 $$('[data-like]').forEach(b=>b.addEventListener('click',async()=>{
  const id=Number(b.dataset.like);
  try{await api(`/confessions/${id}/likes?user_id=${ACTOR_ID}`,{method:'POST'});await loadBackend();toast('Қолдауың үшін рақмет')}
  catch(err){if(err.message==='Already liked'){
    try{await api(`/confessions/${id}/likes?user_id=${ACTOR_ID}`,{method:'DELETE'});await loadBackend();toast('Лайк алынды')}catch(e){showError(e)}
  }else showError(err)}
}));
 $$('[data-report]').forEach(b=>b.addEventListener('click',()=>toast('Шағым жіберілмеді: модерация әзірге қолжетімсіз')));
}
$('#confessInput').addEventListener('input',e=>$('#charCount').textContent=`${e.target.value.length} / 280`);
$('#publishConfess').addEventListener('click',async()=>{
  const text=$('#confessInput').value.trim();
  if (text.length < 3) { toast('Хабарлама кемінде 3 таңбадан тұруы керек.'); return; }
  try{await api('/confessions',{method:'POST',body:JSON.stringify({text,author_id:ACTOR_ID})});$('#confessInput').value='';$('#charCount').textContent='0 / 280';await loadBackend();toast('Анонимді жазба жарияланды')}
  catch(err){showError(err)}
});

function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function openDetail(content){$('#detailContent').innerHTML=content;imageFallbacks($('#detailContent'));if(!$('#detailDialog').open)$('#detailDialog').showModal()}
$('#closeDetail').onclick=()=>$('#detailDialog').close();
$('#closeImage').onclick=()=>$('#imageDialog').close();
for(const id of ['detailDialog','imageDialog'])$('#'+id).addEventListener('click',event=>{if(event.target===event.currentTarget){const rect=event.currentTarget.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)event.currentTarget.close()}});
async function showLostDetail(id){
 try{
  const item=await api(`/lost-items/${id}`), owner=item.owner_id===ACTOR_ID;
  const images=item.images||[];
  openDetail(`<h2 id="detailTitle">${escapeHtml(item.name)}</h2><p>${escapeHtml(item.desc)}</p><p>${icon('map-pin')} ${escapeHtml(item.place)} · ${item.resolved?'Аяқталды':item.status==='lost'?'Жоғалған':'Табылған'}</p><div class="image-gallery">${images.length?images.map(image=>`<div><button type="button" class="gallery-image" data-enlarge="${escapeHtml(image.url)}" aria-label="Фотосуретті үлкейту"><img src="${escapeHtml(assetUrl(image.url))}" alt="${escapeHtml(item.name)}"></button>${owner?`<button type="button" class="outline-button" data-delete-image="${image.id}">Фотоны өшіру</button>`:''}</div>`).join(''):'<p class="photo-placeholder">Фото жоқ</p>'}</div>${owner?`<div id="detailUploader"></div><button type="button" class="primary-button full" id="saveLostImages">Фотоларды қосу</button><p id="detailUploadError" class="form-error" role="alert"></p><button type="button" class="outline-button full" id="deleteLostItem">Хабарландыруды өшіру</button>`:''}`);
  $$('[data-enlarge]').forEach(button=>button.onclick=()=>{$('#enlargedImage').src=assetUrl(button.dataset.enlarge);$('#enlargedImage').alt=item.name;$('#imageDialog').showModal()});
  if(owner){
   const uploader=setupUploader($('#detailUploader'),images.length);
   $('#saveLostImages').onclick=async event=>{if(!uploader.files.length){uploader.error('Алдымен фото таңдаңыз.');return}const button=event.currentTarget;button.disabled=true;button.textContent='Жүктелуде…';try{await sendImages(id,uploader.files);uploader.clear();await loadBackend();await showLostDetail(id);toast('Фотолар қосылды')}catch(error){uploader.error(error.message)}finally{button.disabled=false;button.textContent='Фотоларды қосу'}};
   $$('[data-delete-image]').forEach(button=>button.onclick=async()=>{if(!await askConfirm('Осы фотоны өшіру керек пе?', 'Фотоны өшіру', true))return;button.disabled=true;try{await api(`/lost-items/${id}/images/${button.dataset.deleteImage}?actor_id=${ACTOR_ID}`,{method:'DELETE'});await loadBackend();await showLostDetail(id);toast('Фото өшірілді')}catch(error){showError(error)}finally{button.disabled=false}});
   $('#deleteLostItem').onclick=async event=>{if(!await askConfirm('Хабарландыру мен оның фотоларын өшіру керек пе?', 'Өшіру', true))return;const button=event.currentTarget;button.disabled=true;try{await api(`/lost-items/${id}?actor_id=${ACTOR_ID}`,{method:'DELETE'});$('#detailDialog').close();await loadBackend();toast('Хабарландыру өшірілді')}catch(error){showError(error)}finally{button.disabled=false}};
   $('#detailDialog').addEventListener('close',()=>uploader.clear(),{once:true});
  }
 }catch(error){showError(error)}
}
async function sendImages(id,files){const body=new FormData();files.forEach(file=>body.append('files',file));return api(`/lost-items/${id}/images?actor_id=${ACTOR_ID}`,{method:'POST',body})}
function setupUploader(container,existing=0){
 const state={files:[],urls:[],error:message=>$('.upload-error',container).textContent=message,clear(){state.urls.forEach(URL.revokeObjectURL);state.urls=[];state.files=[];render()}};
 container.innerHTML=`<div class="upload-zone"><p>Фотоларды осы жерге апарыңыз</p><label class="outline-button upload-label">${icon('upload')} Фото таңдау<input class="file-picker" type="file" accept="image/jpeg,image/png,image/webp" multiple aria-label="Фото таңдау"></label><p class="demo-note">JPG, PNG, WebP · әр фото 5 МБ дейін · <span class="image-counter"></span></p></div><p class="upload-error form-error" role="alert"></p><div class="upload-previews"></div>`;
 const zone=$('.upload-zone',container), picker=$('.file-picker',container);
 function render(){
  $('.image-counter',container).textContent=`${existing+state.files.length}/5`;
  $('.upload-previews',container).innerHTML=state.files.map((file,index)=>`<div><img src="${state.urls[index]}" alt="${escapeHtml(file.name)}"><button type="button" class="remove-preview" data-remove="${index}" aria-label="${escapeHtml(file.name)} — алып тастау">${icon('x')}</button></div>`).join('');
  $$('[data-remove]',container).forEach(button=>button.onclick=()=>{const index=Number(button.dataset.remove);URL.revokeObjectURL(state.urls[index]);state.urls.splice(index,1);state.files.splice(index,1);state.error('');render()});
 }
 function add(files){
  state.error('');
  const incoming=[...files];
  if(existing+state.files.length+incoming.length>5){state.error('Барлығы 5 фотодан аспауы керек.');return}
  for(const file of incoming){if(!['image/jpeg','image/png','image/webp'].includes(file.type)||!/\.(jpe?g|png|webp)$/i.test(file.name)){state.error('Тек JPG, PNG және WebP қабылданады.');return}if(file.size>5*1024*1024){state.error('Әр фото 5 МБ аспауы керек.');return}}
  state.files.push(...incoming);state.urls.push(...incoming.map(file=>URL.createObjectURL(file)));render();
 }
 picker.onchange=()=>{add(picker.files);picker.value=''};
 zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('dragging')});
 zone.addEventListener('dragleave',()=>zone.classList.remove('dragging'));
 zone.addEventListener('drop',event=>{event.preventDefault();zone.classList.remove('dragging');add(event.dataTransfer.files)});
 render();return state;
}
let modalUploader=null, modalReturnFocus=null;

// Reusable add-item modal
const modalConfig={
 lost:{title:'Зат жариялау',desc:'Жоғалған немесе табылған зат туралы ақпарат бер.',fields:[['name','Заттың атауы','text','Мысалы: Қара құлаққап'],['status','Статусы','select',['Жоғалған','Табылған']],['place','Қай жерде?','text','Мысалы: Library, 2-қабат'],['desc','Сипаттамасы','textarea','Зат туралы қосымша ақпарат']],async submit(data){const item=await api('/lost-items',{method:'POST',body:JSON.stringify({name:data.name,status:data.status==='Жоғалған'?'lost':'found',place:data.place,desc:data.desc,owner_id:ACTOR_ID})});if(modalUploader?.files.length){try{await sendImages(item.id,modalUploader.files)}catch(error){try{await api(`/lost-items/${item.id}?actor_id=${ACTOR_ID}`,{method:'DELETE'})}catch{throw new Error(`Фото жүктелмеді. Хабарландыру #${item.id} сақталған болуы мүмкін; қайта жарияламас бұрын тізімді тексеріңіз.`)}throw error}}await loadBackend()}},
 skill:{title:'SkillQos ұсынысы',desc:'Қандай дағды үйретесің немесе үйренгің келеді?',fields:[['name','Дағды атауы','text','Мысалы: Python негіздері'],['kind','Бағыт','select',['Үйретемін','Үйренемін']],['person','Есімің','text','Мысалы: Аян'],['detail','Қысқаша сипаттама','textarea','Не ұсына аласың?'],['exchange','Қандай дағдыға қызығасың?','text','Мысалы: English speaking']],async submit(data){await api('/skills',{method:'POST',body:JSON.stringify({name:data.name,kind:data.kind==='Үйретемін'?'teach':'learn',person:data.person,detail:data.detail,exchange:data.exchange,owner_id:ACTOR_ID})});await loadBackend()}}
};
function openModal(type){
 modalReturnFocus=document.activeElement;
 $('#modalError').textContent='';document.body.classList.add('modal-open');$('.app-shell').inert=true;
 modalUploader?.clear();modalUploader=null;
 const cfg=modalConfig[type];$('#modalTitle').textContent=cfg.title;$('#modalDescription').textContent=cfg.desc;
 $('#modalFields').innerHTML=cfg.fields.map(([name,label,kind,placeholder])=>`<div class="form-field"><label>${label}</label>${kind==='select'?`<select name="${name}">${placeholder.map(v=>`<option>${v}</option>`).join('')}</select>`:kind==='textarea'?`<textarea name="${name}" required placeholder="${placeholder}"></textarea>`:`<input name="${name}" required placeholder="${placeholder}">`}</div>`).join('');
 if(type==='lost'){const container=document.createElement('div');$('#modalFields').append(container);modalUploader=setupUploader(container)}
 $$('.form-field', $('#modalFields')).forEach(field=>{const input=$('input,textarea,select',field),label=$('label',field);input.id='field-'+input.name;label.htmlFor=input.id;const bounds={name:[3,100],place:[2,120],desc:[5,500],person:[2,60],detail:[5,500],exchange:[2,120]}[input.name];if(bounds&&input.tagName!=='SELECT'){input.minLength=bounds[0];input.maxLength=bounds[1]}});
 $('#modalBackdrop').classList.add('show');$('#modalForm').dataset.type=type;$('#modalFields input, #modalFields select')?.focus();
}
function closeModal(){if($('#modalForm [type="submit"]').disabled)return;modalUploader?.clear();$('#modalBackdrop').classList.remove('show');document.body.classList.remove('modal-open');$('.app-shell').inert=false;modalReturnFocus?.focus()}
document.addEventListener('keydown',event=>{
 if(!$('#modalBackdrop').classList.contains('show')||$('#detailDialog').open||$('#imageDialog').open)return;
 if(event.key==='Escape'){event.preventDefault();closeModal()}
 if(event.key==='Tab'){const nodes=$$('button,input,textarea,select,a[href]', $('.modal')).filter(node=>!node.disabled),first=nodes[0],last=nodes.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
});
$('#addLost').addEventListener('click',()=>openModal('lost'));$('#addSkill').addEventListener('click',()=>openModal('skill'));
$('#quickAdd').addEventListener('click',choosePublication);
$('#modalClose').addEventListener('click',closeModal);$('#modalBackdrop').addEventListener('click',e=>{if(e.target.id==='modalBackdrop')closeModal()});
$('#modalForm').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.currentTarget;
  const type = form.dataset.type;
  const data = Object.fromEntries(
    [...new FormData(form).entries()].map(([key, value]) => [key, String(value).trim()])
  );
  if (Object.values(data).some(value => !value)) {
    toast('Барлық өрісті толтырыңыз.');
    return;
  }
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.textContent='Жүктелуде…';
  try {
    await modalConfig[type].submit(data);
    form.reset();
    button.disabled=false;closeModal();
    toast('Жарияланым қосылды');
  } catch (err) {
    $('#modalError').textContent=err.message;
    modalUploader?.error(err.message);
    showError(err);
  } finally {
    button.disabled = false;
    button.textContent='Жариялау';
  }
});
$('#notificationButton').addEventListener('click',()=>toast('Әзірге жаңа хабарлама жоқ'));
$('#profileButton').addEventListener('click',()=>toast('Сіз қонақ режиміндесіз. Аккаунтқа кіру әзірге қолжетімсіз'));
function renderHomeFeed(){const all=[...confessions].slice(0,2);$('#homeFeed').innerHTML=all.length?all.map(x=>`<div class="mini-feed-item"><div class="feed-dot">${icon('message-circle')}</div><div><b>Анонимді студент</b><p>${escapeHtml(x.text.slice(0,105))}${x.text.length>105?'…':''}</p></div></div>`).join(''):'<div class="empty-state">Әзірге жазба жоқ. Ishimде бөлімінде алғашқы ойыңызды бөлісіңіз.</div>';$('#postStat').textContent=String(confessions.length+lostItems.length+skills.length)}
function refresh(){renderFood();renderLost();renderSkills();renderConfessions();renderHomeFeed()}
refresh();
loadBackend().catch(showError);
loadFood(true);
$$('.feature-card').forEach(card=>{card.tabIndex=0;card.setAttribute('role','link');card.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();navigate(card.dataset.go)}})});
$$('.nav-link').forEach(button=>button.setAttribute('aria-label',button.textContent.trim()));
$('#confessInput').setAttribute('aria-label','Анонимді жазба');
hydrateIcons();
for(const group of ['lostFilters','skillFilters'])$('#'+group).addEventListener('click',()=>$$('button',$('#'+group)).forEach(button=>button.setAttribute('aria-pressed',String(button.classList.contains('active')))));
$('#themeToggle').setAttribute('aria-pressed',String(document.body.classList.contains('dark')));
$('#themeToggle').addEventListener('click',()=>$('#themeToggle').setAttribute('aria-pressed',String(document.body.classList.contains('dark'))));
$('#lostSearch').setAttribute('aria-label','Зат іздеу');
$('#skillSearch').setAttribute('aria-label','Дағды іздеу');

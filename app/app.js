/* Shared application state and small DOM helpers. Source files are concatenated by build.py. */
'use strict';
const SD={
  boot:JSON.parse(document.getElementById('bootData').textContent),
  state:{filter:'all',query:'',sort:'featured',limit:48},
  library:{format:'svgdrawer.library',schema_version:2,categories:[],symbols:[],favorites:[]},
  current:null,drafts:new Map(),thumbs:new Map(),thumbJobs:new Set(),managerTab:'categories',
  storageKey:'svgdrawer.gallery.v2',storageRaw:null,storageBlocked:false,engineStarted:false,libraryReady:false,libraryBusy:false,startupRaw:null,
  maxLibraryBytes:10000000,
};
const $=selector=>document.querySelector(selector);
const $$=selector=>Array.from(document.querySelectorAll(selector));
const clone=value=>JSON.parse(JSON.stringify(value));
const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const uid=prefix=>prefix+'-'+(globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10));
const clamp=(n,min,max)=>Math.max(min,Math.min(max,Number(n)));
const safeName=value=>(String(value||'symbol').replace(/[^\p{L}\p{N}._-]+/gu,'-').replace(/^[.\-]+|[.\-]+$/g,'').slice(0,90)||'symbol').toLowerCase();
const hex=value=>{let x=String(value).trim();if(x.toLowerCase()==='none')return 'none';x=x.replace(/^#/,'');if(/^[a-f\d]{3}$/i.test(x))x=x.split('').map(c=>c+c).join('');return /^[a-f\d]{6}$/i.test(x)?'#'+x.toUpperCase():null;};
const svgURL=svg=>'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
const DEFAULT_OUTPUT={width:512,height:512,padding:8,transparent:true,background:'#FFFFFF',preserve_aspect:true};
const ICONS={
  plus:'<path d="M12 5v14M5 12h14"/>',close:'<path d="m6 6 12 12M18 6 6 18"/>',
  collection:'<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
  heart:'<path d="M20.8 4.9a5.5 5.5 0 0 0-7.8 0L12 6l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.3a5.5 5.5 0 0 0 0-7.8Z"/>',
  chip:'<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx=".7"/><path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3"/>',
  file:'<path d="M5 3h10l4 4v14H5zM15 3v5h4M8 12h8m-8 4h8"/>',
  folder:'<path d="M3 19V5h7l2 3h9v11H3Zm0 0 3-9h15l-3 9"/>',
  network:'<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M5 16v-4h14v4"/>',
  wave:'<path d="M2 12h3V5h6v14h6V8h5"/>',
  shapes:'<rect x="3" y="3" width="8" height="8" rx="1"/><circle cx="17" cy="7" r="4"/><path d="m7 14 5 7H2Z"/><rect x="15" y="15" width="7" height="7" rx="3.5"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload:'<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  archive:'<path d="M4 8v13h16V8M9 12h6"/><rect x="3" y="3" width="18" height="5" rx="1"/>',
  search:'<circle cx="10.7" cy="10.7" r="6.7"/><path d="m16 16 5 5"/>',
  sort:'<path d="M4 6h16M4 12h11M4 18h6"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  sparkle:'<path d="m12 3 2.8 6.2L21 12l-6.2 2.8L12 21l-2.8-6.2L3 12l6.2-2.8Z"/>',
  sliders:'<path d="M4 7h4m5 0h7M4 17h9m5 0h2"/><circle cx="10.5" cy="7" r="2.5"/><circle cx="15.5" cy="17" r="2.5"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.4 1.4m11.2 11.2L19 19M5 19l1.4-1.4M17.6 6.4 19 5"/>',
  moon:'<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7Z"/>',
  checker:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
  undo:'<path d="M4 10h9a6 6 0 0 1 0 12M4 10l5-5M4 10l5 5" transform="translate(0 -3)"/>',
  redo:'<path d="M20 10h-9a6 6 0 0 0 0 12m9-12-5-5m5 5-5 5" transform="translate(0 -3)"/>',
  reset:'<path d="M3 11a9 9 0 1 1 2.5 7M3 4v7h7"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  edit:'<path d="m15 4 5 5M4 20l5-1L21 7a2.1 2.1 0 0 0-5-5L4 14Z"/>',
  code:'<path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  palette:'<circle cx="8" cy="8" r=".6"/><circle cx="14" cy="6" r=".6"/><circle cx="18" cy="11" r=".6"/><path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-3c-1-2 0-3 2-3h2a3 3 0 0 0 3-3 9 9 0 0 0-9-9Z"/>',
};
function icon(name){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.folder}</svg>`;}
function fillIcons(root=document){root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});}
function toast(message,error=false){
  const el=document.createElement('div');el.className='toast'+(error?' error':'');el.textContent=String(message);
  const modal=$$('dialog[open]').at(-1);let host=$('#toastRegion');
  if(modal){host=document.createElement('div');host.className='toast-in-dialog';host.setAttribute('role','status');modal.append(host);}
  host.append(el);setTimeout(()=>{el.remove();if(host.classList.contains('toast-in-dialog'))host.remove();},error?7500:3400);
}
function showDialog(id){const dialog=document.getElementById(id);if(!dialog.open)dialog.showModal();document.body.classList.add('modal-open');}
function closeDialog(id){document.getElementById(id).close();}
function downloadFile(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function downloadJSON(value,name){downloadFile(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),name);}
function allCategories(){return [...SD.boot.gallery.categories,...SD.library.categories];}
function categoryName(id){return allCategories().find(c=>c.id===id)?.name||'Uncategorized';}
function allSymbols(){return [...SD.boot.gallery.symbols,...SD.library.symbols];}
function findItem(id){return allSymbols().find(item=>item.id===id);}
function baseSpec(item){return SD.boot.gallery.symbols.find(s=>s.id===(item.asset?.type||item.id));}
function isCustomItem(id){return SD.library.symbols.some(item=>item.id===id);}
function persistentItem(id){return !!findItem(id);}
function persistLibrary(){
  if(SD.storageBlocked||!SD.libraryReady)return;
  try{localStorage.setItem(SD.storageKey,JSON.stringify(SD.library));}
  catch(error){$('#storageNoticeText').textContent='Browser storage is unavailable or full. New changes are only in memory: download a Gallery backup before closing.';$('#storageNotice').classList.remove('hidden');$('#recoverStorage').textContent='Download Gallery backup';SD.storageRaw=null;}
}
async function commitLibrary(candidate){
  if(SD.libraryBusy)throw Error('A library update is still in progress. Try again in a moment.');
  SD.libraryBusy=true;$('#managerPanel').setAttribute('aria-busy','true');
  try {
    const next=await SD.engine.request({action:'validate_library',library:candidate});
    SD.library=next;persistLibrary();SD.refreshGallery();return next;
  } finally {SD.libraryBusy=false;$('#managerPanel').setAttribute('aria-busy','false');}
}
function categoryOptions(selected){return allCategories().map(c=>`<option value="${esc(c.id)}" ${c.id===selected?'selected':''}>${esc(c.name)}</option>`).join('');}
function libraryError(error){toast(error.message||error,true);if($('#libraryDialog').open)SD.renderManager?.();console.error(error);}
SD.boot.gallery.symbols.forEach(e=>SD.thumbs.set(e.id,SD.boot.thumbnails[e.id]));
SD.engine=new PythonEngine(SD.boot,(text,mode)=>{const el=$('#engineStatus');el.className='engine-status '+mode;el.querySelector('span').textContent=text;SD.updateDownloadState?.();});

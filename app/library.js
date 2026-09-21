/* Persistent user categories and symbol presets. Built-in files stay immutable.
 * Backups are versioned JSON. Restore merges non-destructively and remaps colliding IDs.
 */
SD.openManager=function(tab='categories'){SD.managerTab=tab;SD.renderManager();showDialog('libraryDialog');};
SD.renderManager=function(){
  const tab=SD.managerTab;$$('[data-manager-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.managerTab===tab);b.setAttribute('aria-selected',b.dataset.managerTab===tab);b.tabIndex=b.dataset.managerTab===tab?0:-1;});
  let html='';
  if(tab==='categories'){
    html='<p class="manager-intro">Categories organize your Gallery. Built-in categories come from the project; your own categories can be added and renamed here.</p>';
    html+=allCategories().map(c=>{const custom=SD.library.categories.some(x=>x.id===c.id),count=allSymbols().filter(e=>e.category===c.id).length;return `<div class="manager-category"><span class="category-symbol">${icon(c.icon||'folder')}</span><span class="category-name">${custom?`<input value="${esc(c.name)}" data-rename-category="${esc(c.id)}" maxlength="60" aria-label="Category name">`:esc(c.name)}</span><small>${count} symbol${count===1?'':'s'}</small>${custom?`<button class="icon-button danger" data-delete-category="${esc(c.id)}" ${count?'disabled':''} title="${count?'Move its symbols before deleting':'Delete empty category'}" aria-label="Delete ${esc(c.name)}">${icon('trash')}</button>`:'<span class="builtin-badge">Built in</span>'}</div>`;}).join('');
    html+='<form class="add-category-form" id="addCategoryForm"><input id="newCategoryName" placeholder="Name your new category…" required maxlength="60" aria-label="New category name"><button class="button primary" type="submit">Add category</button></form><p class="storage-hint">Category IDs stay stable when you rename them, so saved symbols keep their category links.</p>';
  }else if(tab==='symbols'){
    html=`<p class="manager-intro">${SD.library.symbols.length} saved symbol${SD.library.symbols.length===1?'':'s'}. Rename them, move them to a category, or open one to customize a new version.</p>`;
    if(!SD.library.symbols.length)html+='<div class="empty-state"><h3>A collection of your own</h3><p>Customize a gallery symbol and choose Save to my Gallery, or import an SVG.</p><button class="button primary" data-manager-import>Add an symbol</button></div>';
    else html+=SD.library.symbols.map(item=>`<div class="manager-item"><span class="manager-thumb">${SD.thumbs.get(item.id)?`<img src="${svgURL(SD.thumbs.get(item.id))}" alt="">`:icon('shapes')}</span><input value="${esc(item.name)}" data-rename-item="${esc(item.id)}" maxlength="100" aria-label="Symbol name"><select data-move-item="${esc(item.id)}" aria-label="Category for ${esc(item.name)}">${categoryOptions(item.category)}</select><button class="icon-button" data-edit-item="${esc(item.id)}" title="Customize" aria-label="Customize ${esc(item.name)}">${icon('edit')}</button><button class="icon-button danger" data-remove-item="${esc(item.id)}" title="Delete symbol" aria-label="Delete ${esc(item.name)}">${icon('trash')}</button></div>`).join('');
  }else if(tab==='backup'){
    html=`<p class="manager-intro">Your personal Gallery is stored in this browser—not written into the project files. Make a backup before moving to another browser or updating the app.</p><div class="backup-card"><h3>Keep a portable copy</h3><p>${SD.library.symbols.length} custom symbols · ${SD.library.categories.length} custom categories · ${SD.library.favorites.length} favorites. The backup includes parameters, part overrides and imported SVG source.</p><button class="button primary" data-backup>${icon('download')}Download library JSON</button></div><div class="backup-card secondary"><h3>Bring another collection in</h3><p>Import a Gallery backup to merge it with this one. Identical entries are skipped. Conflicting IDs are renamed, so neither version is overwritten.</p><button class="button" data-restore-library>${icon('upload')}Import & merge backup</button></div>${SD.storageBlocked?'<div class="backup-card"><h3>Unreadable saved data</h3><p>Download the recovery backup before clearing it. It has not been overwritten.</p><button class="button" data-recover>Download recovery data</button> <button class="button" data-reset-storage>Reset unreadable storage</button></div>':''}<p class="storage-hint">Backups use schema version 2; version 1 backups are converted on import. Maximum: 1,000 custom symbols, 100 custom categories and 10 MB per backup. Browser storage may fill sooner; export a backup whenever a storage warning appears. Backups reference built-in symbol IDs, so keep the project definitions available.</p>`;
  }else{
    html='<p class="manager-intro">Gallery/ is the source of truth for both the command line and this browser. The index is <code>Gallery/catalog.json</code>. Each symbol has <code>symbol.json</code> and <code>render.py</code> under <code>Gallery/&lt;category&gt;/&lt;id&gt;/</code>. Add new shapes without changing interface code.</p><div class="code-block">python svgdrawer.py --list<br>python svgdrawer.py --describe chip --json<br>python svgdrawer.py --create chip --color-sets default<br>python svgdrawer.py --create chip --set pins=10 --output chip.svg</div><div class="guide-step"><span class="guide-number">1</span><div><h3>Add a category</h3><p><code>python svgdrawer.py --add-category instruments --name "Instruments"</code></p></div></div><div class="guide-step"><span class="guide-number">2</span><div><h3>Create and register Python geometry</h3><p><code>python svgdrawer.py --init-symbol sensor --category instruments</code></p><p>Edit the generated Python script and JSON controls in drafts/. Then register it:</p><p><code>python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json</code></p></div></div><div class="guide-step"><span class="guide-number">3</span><div><h3>Validate and publish</h3><p><code>python svgdrawer.py --validate</code><br><code>python svgdrawer.py --build</code></p><p>Restart the local server after changing source files. Keep the source project, not just the generated HTML.</p></div></div><div class="inline-note">'+icon('info')+'<span>Read AGENTS.md and docs/AGENT_GUIDE.md in the bundle. Python renderer scripts are trusted code, not sandboxed. Browser-only variants remain in your personal Gallery; back them up separately.</span></div>';

  }
  $('#managerPanel').innerHTML=html;
};
SD.addCategory=async function(name){
  const clean=name.trim();if(!clean)throw Error('Enter a category name.');if(allCategories().some(c=>c.name.toLowerCase()===clean.toLowerCase()))throw Error('A category with that name already exists.');
  const next=clone(SD.library);next.categories.push({id:uid('category'),name:clean,description:'Your custom collection.',icon:'folder',order:1000+next.categories.length});await commitLibrary(next);SD.renderManager();toast('Category added.');
};
SD.renameCategory=async function(id,name){const clean=name.trim();if(!clean)throw Error('Category names cannot be empty.');if(allCategories().some(c=>c.id!==id&&c.name.toLowerCase()===clean.toLowerCase()))throw Error('A category with that name already exists.');const next=clone(SD.library),c=next.categories.find(c=>c.id===id);if(!c)return;c.name=clean;await commitLibrary(next);SD.renderManager();toast('Category renamed. Its ID is unchanged.');};
SD.deleteCategory=async function(id){if(allSymbols().some(e=>e.category===id))throw Error('Move the category’s symbols before deleting it.');if(!confirm('Delete this empty category?'))return;const next=clone(SD.library);next.categories=next.categories.filter(c=>c.id!==id);await commitLibrary(next);if(SD.state.filter===id)SD.setFilter('all');SD.renderManager();toast('Category deleted.');};
SD.editItemMetadata=async function(id,key,value){const next=clone(SD.library),item=next.symbols.find(e=>e.id===id);if(!item)return;if(key==='name'){value=value.trim();if(!value)throw Error('Symbol names cannot be empty.');}item[key]=value;await commitLibrary(next);SD.renderManager();toast('Symbol updated.');};
SD.removeItem=async function(id){const item=findItem(id);if(!isCustomItem(id)||!confirm(`Delete “${item.name}” from your personal Gallery? Existing downloaded files will not change.`))return;const next=clone(SD.library);next.symbols=next.symbols.filter(e=>e.id!==id);next.favorites=next.favorites.filter(x=>x!==id);await commitLibrary(next);SD.thumbs.delete(id);SD.drafts.delete(id);SD.renderManager();toast('Symbol removed.');};
SD.openSave=function(){
  const c=SD.current;if(!c)return;SD.finishEdit();$('#saveName').value=c.item.asset?.type==='custom'?c.item.name:c.item.name+' · custom';
  $('#saveCategory').innerHTML=categoryOptions(c.item.category);$('#saveNewCategory').value='';$('#saveTags').value=(c.item.tags||[]).join(', ');$('#saveBlurb').value=c.item.description||'';showDialog('saveDialog');
};
SD.saveVariant=async function(){
  const c=SD.current;if(!c)return;const name=$('#saveName').value.trim();if(!name)throw Error('Enter an symbol name.');const next=clone(SD.library);let category=$('#saveCategory').value;
  const newName=$('#saveNewCategory').value.trim();if(newName){const existing=allCategories().find(c=>c.name.toLowerCase()===newName.toLowerCase());if(existing)category=existing.id;else{category=uid('category');next.categories.push({id:category,name:newName,description:'Your custom collection.'});}}
  const item={id:uid('symbol'),name,category,description:$('#saveBlurb').value.trim(),tags:$('#saveTags').value.split(',').map(t=>t.trim()).filter(Boolean),asset:clone(c.draft.asset),output:clone(c.draft.output),created_at:new Date().toISOString()};next.symbols.push(item);
  $('#confirmSave').disabled=true;try{await commitLibrary(next);closeDialog('saveDialog');toast(`“${name}” added to your personal Gallery.`);}finally{$('#confirmSave').disabled=false;}
};
SD.backupLibrary=function(){
  if(!SD.libraryReady||SD.storageBlocked){
    let raw=SD.storageRaw||SD.startupRaw;try{raw=raw||localStorage.getItem(SD.storageKey);}catch(_){}
    if(raw){downloadFile(new Blob([raw],{type:'application/json'}),'svgdrawer-recovery.json');toast('Original saved data downloaded without modification.');}
    else toast('Wait for your personal Gallery to finish loading, then back it up.');
    return;
  }
  downloadJSON(SD.library,'svgdrawer-library.json');toast('Library backup downloaded.');
};
SD.recoverStorage=function(){if(SD.storageRaw)downloadFile(new Blob([SD.storageRaw],{type:'application/json'}),'svgdrawer-recovery.json');else SD.backupLibrary();};
SD.mergeLibrary=async function(file){
  if(file.size>SD.maxLibraryBytes)throw Error('Library backups must be smaller than 10 MB.');
  const raw=JSON.parse(await file.text());const incoming=await SD.engine.request({action:'validate_library',library:raw});const next=clone(SD.library),catMap=new Map(),itemMap=new Map();let added=0;
  for(const c of incoming.categories){
    const byName=[...SD.boot.gallery.categories,...next.categories].find(x=>x.name.toLowerCase()===c.name.toLowerCase());
    if(byName){catMap.set(c.id,byName.id);continue;}
    const id=[...SD.boot.gallery.categories,...next.categories].some(x=>x.id===c.id)?uid('category'):c.id;catMap.set(c.id,id);next.categories.push({...c,id});
  }
  for(const input of incoming.symbols){
    const item={...input,category:catMap.get(input.category)||input.category};
    const signature=entry=>{const copy={...entry};delete copy.id;return JSON.stringify(copy);};
    const identical=next.symbols.find(x=>signature(x)===signature(item));
    if(identical){itemMap.set(input.id,identical.id);continue;}
    const collision=next.symbols.find(x=>x.id===item.id);
    if(collision&&JSON.stringify(collision)===JSON.stringify(item)){itemMap.set(input.id,collision.id);continue;}
    if(collision)item.id=uid('symbol');itemMap.set(input.id,item.id);next.symbols.push(item);added++;
  }
  next.favorites=Array.from(new Set([...next.favorites,...incoming.favorites.map(id=>itemMap.get(id)||id)]));
  await commitLibrary(next);SD.renderManager();toast(`Library merged: ${added} symbol${added===1?'':'s'} added. No existing symbols overwritten.`);
};
SD.importSVG=async function(file){
  if(file.size>400000)throw Error('SVG imports must be smaller than 400 KB.');
  const result=await SD.engine.request({action:'import_svg',source:await file.text()});
  const category=allCategories().some(c=>c.id===SD.state.filter)?SD.state.filter:'documents';
  const item={id:uid('draft'),name:file.name.replace(/\.svg$/i,''),category,description:'Your imported vector. Customize its individual shapes under Inner parts.',tags:['imported'],asset:result.asset,output:clone(DEFAULT_OUTPUT)};
  closeDialog('importDialog');SD.openAsset(item,'parts');toast('SVG imported. Customize it, then save it to your personal Gallery.');
};
SD.importRecipe=async function(file){
  if(file.size>1000000)throw Error('Symbol recipes must be smaller than 1 MB.');
  const recipe=await SD.engine.request({action:'validate_recipe',recipe:JSON.parse(await file.text())});const spec=SD.boot.gallery.symbols.find(s=>s.id===recipe.asset.type);
  const item={id:uid('draft'),name:recipe.name,category:spec?.category||'documents',description:spec?.description||'Restored from an editable symbol recipe.',tags:spec?.tags||[],asset:recipe.asset,output:recipe.output};
  closeDialog('importDialog');SD.openAsset(item);toast('Recipe opened. Save to your personal Gallery to keep it.');
};

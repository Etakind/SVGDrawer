/* Management publishes to the same Gallery used by the CLI. */
SD.reload=async function(){
  if(SD.refreshing)return;
  SD.refreshing=true;
  try{
    const gallery=await SD.engine.fetch('/api/gallery');
    if(JSON.stringify(gallery)===JSON.stringify(SD.boot.gallery))return;
    const pristine=SD.current&&JSON.stringify(SD.current.draft)===JSON.stringify(SD.current.original);
    SD.revision=(SD.revision||0)+1;
    SD.boot.gallery=gallery;SD.thumbs.clear();SD.drafts.clear();SD.refreshGallery();
    if(SD.current){const item=findItem(SD.current.item.id);if(!item&&!SD.current.item.asset)closeDialog('assetDialog');else if(item){SD.current.item=clone(item);SD.current.original=SD.makeDraft(item);if(pristine)SD.current.draft=clone(SD.current.original);$('#assetTitle').textContent=item.name;$('#assetDescription').textContent=item.description;$('#assetTags').innerHTML=(item.tags||[]).map(tag=>`<span>${esc(tag)}</span>`).join('');$('#assetCategory').textContent=categoryName(item.category)+' · '+item.style;SD.updateFavorite();SD.renderSettings();SD.schedulePreview();}}
    if($('#libraryDialog').open)await SD.renderManager();
  }finally{SD.refreshing=false;}
};
SD.manage=async function(payload){
  const response=await SD.engine.fetch('/api/manage',payload);
  if(!payload.dry_run){await SD.reload();if($('#libraryDialog').open)await SD.renderManager();}
  return response.data;
};
SD.openManager=async function(tab='symbols'){SD.managerTab=tab;showDialog('libraryDialog');await guarded(SD.renderManager);};
SD.renderManager=async function(){
  const tab=SD.managerTab;
  $$('[data-manager-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.managerTab===tab);b.setAttribute('aria-selected',b.dataset.managerTab===tab);});
  const panel=$('#managerPanel');
  if(tab==='symbols'){
    panel.innerHTML=`<p>All changes are shared with the CLI. Select symbols to move or trash them.</p><div class="manager-actions"><select id="batchCategory" aria-label="Destination category">${categoryOptions('uncategorized')}</select><button class="button" data-batch="move">Move selected</button><button class="button" data-batch="trash">Trash selected</button></div>${allSymbols().map(s=>`<div class="management-row"><label><input type="checkbox" data-select="${esc(s.id)}" ${SD.selection.has(s.id)?'checked':''}> ${esc(s.name)} <small>${esc(s.id)} · ${esc(categoryName(s.category))} · ${esc(s.style)} ${s.customizable?'· customizable':''}</small></label><button class="button small" data-edit-item="${esc(s.id)}">Edit metadata</button></div>`).join('')}`;
  }else if(tab==='categories'){
    panel.innerHTML=`<form id="addCategoryForm" class="manager-actions"><label>ID <input id="newCategoryId" required></label><label>Name <input id="newCategoryName" required></label><button class="button">Add category</button></form>${allCategories().map(c=>{const count=allSymbols().filter(s=>s.category===c.id).length;return `<div class="management-row"><span>${esc(c.name)} <small>${esc(c.id)} · ${count} symbols</small></span><button class="button small" data-edit-category="${esc(c.id)}">Edit</button>${c.id==='uncategorized'?'':`<button class="button small" data-delete-category="${esc(c.id)}">Delete</button>`}</div>`;}).join('')}`;
  }else if(tab==='trash'){
    const result=await SD.engine.fetch('/api/trash');if(SD.managerTab!==tab)return;
    const rows=result.entries||result.trash||[],entries=rows.filter(e=>e.kind!=='snapshot'),snapshots=rows.filter(e=>e.kind==='snapshot');
    panel.innerHTML=`<div class="manager-actions"><button class="button" data-batch="restore">Restore selected</button><button class="button" data-batch="purge">Permanently remove selected</button><button class="button" data-batch="empty">Empty trash</button></div><h3>Symbols and categories</h3>${entries.map(e=>`<div class="management-row"><label><input type="checkbox" data-trash-select="${esc(e.trash_id)}" ${SD.trashSelection.has(e.trash_id)?'checked':''}> ${esc(e.category?.name)} / ${esc(e.symbol?.name||e.category?.name)} <small>${esc(e.deleted_at)}</small></label></div>`).join('')||'<p>Trash is empty.</p>'}<h3>Gallery snapshots</h3><p>Restoring a snapshot replaces the active Gallery and retains it as another snapshot.</p>${snapshots.map(e=>`<div class="management-row"><label><input type="checkbox" data-trash-select="${esc(e.trash_id)}"> ${esc(e.name)} <small>${esc(e.deleted_at)}</small></label><button class="button" data-snapshot="${esc(e.trash_id)}">Preview restore</button></div>`).join('')||'<p>No snapshots.</p>'}`;
  }else if(tab==='backup'){
    panel.innerHTML='<h3>Back up the active Gallery</h3><p>The ZIP contains Gallery/ directly: active symbols, catalog, settings, palettes and helpers. Trash and history are excluded.</p><button class="button" data-backup>Download Gallery ZIP</button><h3>Import Gallery ZIP</h3><p>Python sources are executable code. Import only archives you trust. Preview additions and conflicts before importing.</p><label class="check-field"><span>Full sync: replace the active Gallery, retaining a trash snapshot</span><input id="forceSync" type="checkbox"></label><button class="button" data-restore-library>Choose ZIP and preview</button>';
  }else{
    panel.innerHTML='<h3>One Python application, one Gallery</h3><p>Activate the project Conda environment, then run python svgdrawer.py --help. The UI and CLI publish to Gallery/; no browser-owned collection exists.</p><pre>--add-symbol ID --script FILE.py --spec FILE.json\n--save-symbol ID --recipe FILE.asset.json\n--backup-gallery --output Gallery.zip</pre><p>Read docs/AGENT_GUIDE.md and docs/CLI_REFERENCE.md.</p>';
  }
};
SD.addCategory=async function(name,id){id=id||safeName(name);await SD.manage({action:'add-category',id,name});return id;};
SD.editCategory=async function(id){
  const category=allCategories().find(c=>c.id===id),name=prompt('Category name',category.name);if(name===null)return;
  const description=prompt('Description',category.description||'');if(description===null)return;
  await SD.manage({action:'update-category',id,name,description});
};
SD.deleteCategory=async function(id){
  const count=allSymbols().filter(s=>s.category===id).length;let contents;
  if(count){contents=prompt(`${count} symbols are in this category. Type uncategorized to move them, or trash to retain them in the trash bin.`,'uncategorized');if(contents===null)return;if(!['uncategorized','trash'].includes(contents))throw Error('Choose uncategorized or trash.');}
  if(confirm(`Delete category ${id}${count?` and ${contents==='trash'?'trash':'move'} its ${count} symbols`:''}?`))await SD.manage({action:'delete-category',id,...(contents?{contents}:{})});
};
SD.editMetadata=async function(id){
  const item=findItem(id),payload={action:'update-symbol',id};
  for(const key of ['name','description','style','tags']){const value=prompt(key,Array.isArray(item[key])?item[key].join(', '):item[key]||'');if(value===null)return;payload[key]=value;}
  await SD.manage(payload);
};
SD.batch=async function(action){
  if(action==='empty'){if(confirm('Permanently remove ALL trash, including snapshots? This cannot be undone.'))await SD.manage({action:'empty-trash',yes:true});return;}
  const ids=[...(action==='move'||action==='trash'?SD.selection:SD.trashSelection)];if(!ids.length)throw Error('Select at least one item.');
  if(action==='restore'&&ids.length===1){const trash=await SD.engine.fetch('/api/trash');if(trash.entries.find(e=>e.trash_id===ids[0])?.kind==='snapshot'){await SD.restoreSnapshot(ids[0]);return;}}
  const payload={action:({move:'move-symbol',trash:'delete-symbol',restore:'restore',purge:'purge'})[action],ids};
  if(action==='move')payload.category=$('#batchCategory').value;
  if(action==='purge'){if(!confirm(`Permanently remove ${ids.length} selected entries? This cannot be undone.`))return;payload.yes=true;}
  if(action==='trash'&&!confirm(`Move ${ids.length} symbols to trash?`))return;
  await SD.manage(payload);SD.selection.clear();SD.trashSelection.clear();await SD.renderManager();
};
SD.restoreSnapshot=async function(id){
  const payload={action:'restore',ids:[id]},preview=await SD.manage({...payload,dry_run:true});
  if(confirm('Replace the active Gallery with this snapshot? Current active content will be saved as another snapshot.\n'+JSON.stringify(preview,null,2)))await SD.manage({...payload,yes:true});
};
SD.backupGallery=async function(){const blob=await SD.engine.fetch('/api/backup',undefined,true);downloadFile(blob,'Gallery.zip');};
SD.importGallery=async function(file){
  if(!confirm('Gallery archives may contain Python code that executes during validation and rendering. Do you trust this archive?'))return;
  const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  const payload={action:'import-gallery',archive:btoa(binary),force_sync:!!$('#forceSync')?.checked};
  const preview=await SD.manage({...payload,dry_run:true});
  if(confirm((payload.force_sync?'FULL SYNC replaces all active Gallery content and saves a trash snapshot.':'Add only nonconflicting symbols. Local settings and helpers stay unchanged.')+'\n'+JSON.stringify(preview,null,2)))await SD.manage({...payload,yes:payload.force_sync});
};
SD.importSVG=async function(file){
  const name=prompt('Symbol name',file.name.replace(/\.svg$/i,''));if(name===null)return;
  const id=prompt('Stable symbol ID',safeName(name));if(id===null)return;
  const category=prompt('Category ID','uncategorized');if(category===null)return;
  await SD.manage({action:'import-svg',id,name,category,svg:await file.text()});closeDialog('importDialog');SD.openAsset(id);
};
SD.importRecipe=async function(file){
  const recipe=await SD.engine.request({action:'validate_recipe',recipe:JSON.parse(await file.text())});
  closeDialog('importDialog');SD.openAsset({id:uid('draft'),name:recipe.name,category:'uncategorized',asset:recipe.asset,output:recipe.output});
};
SD.openSave=function(){
  if(!SD.current)return;$('#saveName').value=SD.current.item.name+' variant';$('#saveId').value=safeName($('#saveName').value);$('#saveStyle').value=SD.current.item.style||'default';$('#saveCategory').innerHTML=categoryOptions(SD.current.item.category);$('#saveTags').value=(SD.current.item.tags||[]).join(', ');$('#saveBlurb').value=SD.current.item.description||'';$('#saveNewCategory').value='';showDialog('saveDialog');
};
SD.saveVariant=async function(){
  let category=$('#saveCategory').value;if($('#saveNewCategory').value.trim())category=await SD.addCategory($('#saveNewCategory').value.trim());
  await SD.manage({action:'save-symbol',id:$('#saveId').value,name:$('#saveName').value,category,style:$('#saveStyle').value,tags:$('#saveTags').value,description:$('#saveBlurb').value,recipe:SD.recipe()});closeDialog('saveDialog');toast('Saved to the shared Gallery.');
};

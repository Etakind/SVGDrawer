/* Event wiring and application startup. All geometry requests go through PythonEngine. */
async function guarded(fn){try{await fn();}catch(error){libraryError(error);}}
SD.startEngine=async function(){
  if(SD.engineStarted)return;SD.engineStarted=true;$('#engineNotice').classList.add('hidden');
  try{
    let raw=null;try{raw=localStorage.getItem(SD.storageKey) ?? localStorage.getItem("svgdrawer.gallery.v1") ?? localStorage.getItem("vector-foundry.catalog.v1");}catch(_){}SD.startupRaw=raw;
    await SD.engine.initialize();
    if(raw!==null){
      try{SD.library=await SD.engine.request({action:'validate_library',library:JSON.parse(raw)});SD.storageBlocked=false;SD.storageRaw=null;}
      catch(error){SD.storageBlocked=true;SD.storageRaw=raw;$('#storageNoticeText').textContent='Saved library could not be loaded. It has not been overwritten. Download a recovery backup, then review Backup & restore. '+String(error.message).slice(0,180);$('#storageNotice').classList.remove('hidden');}
    }
    SD.libraryReady=true;if(raw!==null&&!SD.storageBlocked)persistLibrary();SD.refreshGallery();SD.updateDownloadState();if(SD.current){SD.renderSettings();SD.schedulePreview();}
  }catch(error){
    SD.engineStarted=false;$('#engineNoticeText').textContent='The single HTML needs internet access to start Python. For offline use, extract the bundle and run python server.py. '+String(error.message).slice(0,180);$('#engineNotice').classList.remove('hidden');SD.updateDownloadState();
  }
};
// Do not replace unreadable browser data as a side effect of an unrelated edit.
const commitLibraryOriginal=commitLibrary;
commitLibrary=async function(candidate){if(!SD.libraryReady)throw Error('Wait for Python and your saved library to finish loading.');if(SD.storageBlocked)throw Error('Unreadable saved data is protected. Download its recovery backup, then reset it under Manage my Gallery → Backup & restore.');return commitLibraryOriginal(candidate);};

document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button||button.disabled)return;
  const ds=button.dataset;
  guarded(async()=>{
    if(ds.close){closeDialog(ds.close);return;}
    if(ds.filter){SD.setFilter(ds.filter);return;}
    if(ds.open){SD.openAsset(ds.open);return;}
    if(ds.favorite){SD.toggleFavorite(ds.favorite);return;}
    if('clearQuery'in ds){SD.state.query='';$('#search').value='';SD.state.limit=48;SD.renderGrid();return;}
    if(ds.preview){$('#previewSurface').className='preview-surface '+ds.preview;$$('[data-preview]').forEach(b=>b.classList.toggle('active',b===button));return;}
    if(ds.tab){SD.setTab(ds.tab);return;}
    if('goParts'in ds){SD.setTab('parts');return;}
    if('paletteIndex'in ds){const palette=SD.boot.gallery.palettes[Number(ds.paletteIndex)];SD.change(d=>{for(const key of ['fill','accent','stroke','highlight'])d.asset.params[key]=palette[key];});return;}
    if(ds.none){const [scope,key]=ds.none.split(':');SD.change(d=>{if(scope==='part'){const override=SD.partOverride();if(override)override[key]='none';}else if(scope==='output')d.output[key]='none';else d.asset.params[key]='none';});return;}
    if(ds.outputSize){SD.change(d=>{d.output.width=Number(ds.outputSize);d.output.height=Number(ds.outputSize);});return;}
    if('resetPart'in ds){SD.change(d=>{delete d.asset.parts[SD.current.selectedPart];});return;}
    if('resetAllParts'in ds){SD.change(d=>{d.asset.parts={};});return;}
    if('viewSource'in ds){await SD.showSource();return;}
    if('saveRecipe'in ds){SD.saveRecipe();return;}
    if('pythonScript'in ds){SD.downloadPython();return;}
    if(ds.managerTab){SD.managerTab=ds.managerTab;SD.renderManager();return;}
    if(ds.deleteCategory){await SD.deleteCategory(ds.deleteCategory);return;}
    if(ds.removeItem){await SD.removeItem(ds.removeItem);return;}
    if(ds.editItem){closeDialog('libraryDialog');SD.openAsset(ds.editItem);return;}
    if('backup'in ds){SD.backupLibrary();return;}
    if('restoreLibrary'in ds){$('#libraryInput').click();return;}
    if('managerImport'in ds){closeDialog('libraryDialog');showDialog('importDialog');return;}
    if('recover'in ds){SD.recoverStorage();return;}
    if('resetStorage'in ds){
      if(!confirm('Clear the unreadable saved library? Download a recovery backup first.'))return;
      try{localStorage.removeItem(SD.storageKey);}catch(_){}
      SD.storageBlocked=false;SD.storageRaw=null;SD.startupRaw=null;persistLibrary();$('#storageNotice').classList.add('hidden');SD.renderManager();toast('Unreadable storage cleared.');return;
    }
  });
});
$('#search').addEventListener('input',event=>{SD.state.query=event.target.value;SD.state.limit=48;SD.renderGrid();});
$('#sort').addEventListener('change',event=>{SD.state.sort=event.target.value;SD.renderGrid();});
$('#mobileCategory').addEventListener('change',event=>SD.setFilter(event.target.value));
$('#loadMore').addEventListener('click',()=>{SD.state.limit+=48;SD.renderGrid();});
$('#clearSearch').addEventListener('click',()=>{SD.state.query='';$('#search').value='';SD.setFilter('all');});
$('.brand').addEventListener('click',event=>{event.preventDefault();SD.state.query='';$('#search').value='';SD.setFilter('all');window.scrollTo({top:0,behavior:'smooth'});});
$('#manageLibrary').addEventListener('click',()=>SD.openManager());
$('#addSymbol').addEventListener('click',()=>showDialog('importDialog'));
for(const id of ['#newCategoryShortcut','#sidebarAddCategory'])$(id).addEventListener('click',()=>{SD.openManager('categories');$('#newCategoryName')?.focus();});
$('#backupShortcut').addEventListener('click',SD.backupLibrary);
$('#projectGuide').addEventListener('click',()=>SD.openManager('guide'));
$('#retryEngine').addEventListener('click',SD.startEngine);
$('#recoverStorage').addEventListener('click',SD.recoverStorage);
$('#browseInstead').addEventListener('click',()=>closeDialog('importDialog'));
$('#restoreRecipe').addEventListener('click',()=>$('#recipeInput').click());
$('#detailFavorite').addEventListener('click',()=>{if(SD.current)SD.toggleFavorite(SD.current.item.id);});
$('#undoEdit').addEventListener('click',()=>SD.undo(false));$('#redoEdit').addEventListener('click',()=>SD.undo(true));
$('#resetSymbol').addEventListener('click',()=>{if(SD.current)SD.change(()=>{SD.current.draft=clone(SD.current.original);SD.current.selectedPart=null;});});
$('#saveVariant').addEventListener('click',SD.openSave);
$('#downloadSVG').addEventListener('click',()=>SD.downloadAsset('svg'));
$('#downloadPNG').addEventListener('click',()=>SD.downloadAsset('png'));
$('#outputSummary').addEventListener('click',()=>SD.setTab('export'));
$('#artPreview').addEventListener('click',event=>{const part=event.target.closest('[data-part]');if(part&&SD.current?.tab==='parts')SD.selectPart(part.dataset.part);});
$('#settingsPanel').addEventListener('input',event=>{if(event.target.dataset.scope)SD.applyControl(event.target);});
$('#settingsPanel').addEventListener('change',event=>{if(event.target.id==='partSelect')SD.selectPart(event.target.value);else if(event.target.dataset.scope)SD.applyControl(event.target,true);});
$('#settingsPanel').addEventListener('focusout',()=>SD.finishEdit());
$('#saveForm').addEventListener('submit',event=>{event.preventDefault();guarded(SD.saveVariant);});
$('#managerPanel').addEventListener('submit',event=>{if(event.target.id==='addCategoryForm'){event.preventDefault();guarded(()=>SD.addCategory($('#newCategoryName').value));}});
$('#managerPanel').addEventListener('change',event=>{const ds=event.target.dataset;guarded(async()=>{if(ds.renameCategory)await SD.renameCategory(ds.renameCategory,event.target.value);if(ds.renameItem)await SD.editItemMetadata(ds.renameItem,'name',event.target.value);if(ds.moveItem)await SD.editItemMetadata(ds.moveItem,'category',event.target.value);});});
for(const [id,handler] of [['#svgInput',SD.importSVG],['#recipeInput',SD.importRecipe],['#libraryInput',SD.mergeLibrary]]){
  $(id).addEventListener('change',event=>{const file=event.target.files[0];event.target.value='';if(file)guarded(()=>handler(file));});
}
$('#copySource').addEventListener('click',()=>guarded(async()=>{try{await navigator.clipboard.writeText($('#sourceText').value);toast('SVG code copied.');}catch(_){$('#sourceText').focus();$('#sourceText').select();toast('Code selected. Press Ctrl+C to copy.');}}));
$('#sourceDownload').addEventListener('click',()=>{if(SD.sourceExport)downloadFile(new Blob([SD.sourceExport.svg],{type:'image/svg+xml'}),SD.sourceExport.name+'.svg');});
$$('dialog').forEach(dialog=>dialog.addEventListener('close',()=>{if(dialog.id==='assetDialog')SD.closeAsset();document.body.classList.toggle('modal-open',!!$('dialog[open]'));}));
document.addEventListener('keydown',event=>{
  const input=event.target.closest('input,textarea,select,[contenteditable]');
  if(event.key==='/'&&!input&&!$('dialog[open]')){event.preventDefault();$('#search').focus();}
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'&&!input&&SD.current){event.preventDefault();SD.undo(event.shiftKey);}
  const tab=event.target.closest('[role=tab]');if(tab&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    const tabs=Array.from(tab.parentElement.querySelectorAll('[role=tab]'));let i=tabs.indexOf(tab);i=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;event.preventDefault();tabs[i].click();tabs[i].focus();
  }
});
window.SVGDrawer=Object.freeze({version:'3.0.0',getCurrentRecipe:()=>SD.recipe(),getLibrarySnapshot:()=>clone(SD.library)});
fillIcons();SD.initializeHero();SD.refreshGallery();SD.updateDownloadState();SD.startEngine();

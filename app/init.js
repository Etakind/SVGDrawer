/* Event wiring and application startup. All geometry requests go through PythonEngine. */
async function guarded(fn){try{await fn();}catch(error){libraryError(error);}}
SD.startEngine=async function(){
  try{await SD.engine.initialize();await SD.reload();SD.galleryReady=true;SD.refreshGallery();SD.updateDownloadState();$('#engineNotice').classList.add('hidden');}
  catch(error){$('#engineNoticeText').textContent='Cannot connect to the local Python application. '+error.message;$('#engineNotice').classList.remove('hidden');}
};

document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button||button.disabled)return;
  const ds=button.dataset;
  guarded(async()=>{
    if(ds.close){closeDialog(ds.close);return;}
    if(ds.filter){SD.setFilter(ds.filter);return;}
    if(ds.open){SD.openAsset(ds.open);return;}
    if(ds.favorite){await SD.toggleFavorite(ds.favorite);return;}
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
    if(ds.managerTab){SD.managerTab=ds.managerTab;await SD.renderManager();return;}
    if(ds.deleteCategory){await SD.deleteCategory(ds.deleteCategory);return;}
    if(ds.editCategory){await SD.editCategory(ds.editCategory);return;}
    if(ds.editItem){await SD.editMetadata(ds.editItem);return;}
    if(ds.batch){await SD.batch(ds.batch);return;}
    if(ds.snapshot){await SD.restoreSnapshot(ds.snapshot);return;}
    if('backup'in ds){await SD.backupGallery();return;}
    if('restoreLibrary'in ds){$('#libraryInput').click();return;}

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
$('#backupShortcut').addEventListener('click',()=>guarded(SD.backupGallery));
$('#projectGuide').addEventListener('click',()=>SD.openManager('guide'));
$('#retryEngine').addEventListener('click',SD.startEngine);
$('#browseInstead').addEventListener('click',()=>closeDialog('importDialog'));
$('#restoreRecipe').addEventListener('click',()=>$('#recipeInput').click());
$('#detailFavorite').addEventListener('click',()=>guarded(async()=>{if(SD.current)await SD.toggleFavorite(SD.current.item.id);}));
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
$('#managerPanel').addEventListener('submit',event=>{if(event.target.id==='addCategoryForm'){event.preventDefault();guarded(()=>SD.addCategory($('#newCategoryName').value,$('#newCategoryId').value));}});
$('#managerPanel').addEventListener('change',event=>{const el=event.target;if(el.dataset.select){el.checked?SD.selection.add(el.dataset.select):SD.selection.delete(el.dataset.select);}if(el.dataset.trashSelect){el.checked?SD.trashSelection.add(el.dataset.trashSelect):SD.trashSelection.delete(el.dataset.trashSelect);}});
$('#pythonForm').addEventListener('submit',event=>{event.preventDefault();guarded(async()=>{const form=event.target; if(!confirm('This Python renderer will execute locally. Do you trust its source?'))return;await SD.manage({action:'add-symbol',id:form.elements.id.value,script:await form.elements.script.files[0].text(),spec:JSON.parse(await form.elements.spec.files[0].text())});closeDialog('importDialog');toast('Python symbol added.');});});
for(const [id,handler] of [['#svgInput',SD.importSVG],['#recipeInput',SD.importRecipe],['#libraryInput',SD.importGallery]]){
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
window.SVGDrawer=Object.freeze({version:'3.0.0',getCurrentRecipe:()=>SD.recipe(),getGallerySnapshot:()=>clone(SD.boot.gallery)});
fillIcons();SD.refreshGallery();SD.updateDownloadState();SD.startEngine();

setInterval(()=>{if(SD.galleryReady&&!SD.refreshing)SD.reload().catch(()=>{});},2000);
window.addEventListener("focus",()=>{if(SD.galleryReady)SD.reload().catch(()=>{});});

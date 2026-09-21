/* One-symbol product detail, schema-driven controls and per-part customization. */
SD.makeDraft=function(item){return {asset:clone(item.asset||{type:item.id,params:item.defaults,parts:item.parts||{}}),output:clone({...DEFAULT_OUTPUT,...item.output}),filename:safeName(item.name),pngScale:2};};
SD.openAsset=function(idOrItem,tab='customize'){
  const item=typeof idOrItem==='string'?findItem(idOrItem):idOrItem;if(!item)return;
  if(SD.current)SD.closeAsset();
  const original=SD.makeDraft(item),draft=clone(SD.drafts.get(item.id)||original);
  SD.current={item:clone(item),draft,original,tab,selectedPart:null,history:[],future:[],baseline:null,renderSeq:0,renderTimer:null,lastSVG:null};
  $('#assetTitle').textContent=item.name;$('#assetCategory').textContent=categoryName(item.category)+' · '+(item.style||baseSpec(item)?.style||'default');
  $('#assetDescription').textContent=item.description||'Your custom vector symbol.';
  $('#assetTags').innerHTML=(item.tags||[]).map(t=>`<span>${esc(t)}</span>`).join('');
  $('#artPreview').innerHTML=SD.thumbs.get(item.id)||'';
  $('#previewSurface').className='preview-surface light';$$('[data-preview]').forEach(b=>b.classList.toggle('active',b.dataset.preview==='light'));
  SD.updateFavorite();SD.renderSettings();SD.updateHistory();SD.updateOutputSummary();SD.updateDownloadState();
  showDialog('assetDialog');SD.schedulePreview();
};
SD.closeAsset=function(){
  if(!SD.current)return;SD.finishEdit();SD.drafts.set(SD.current.item.id,clone(SD.current.draft));clearTimeout(SD.current.renderTimer);SD.current=null;
};
SD.updateFavorite=function(){const c=SD.current;if(!c)return;const on=!!findItem(c.item.id)?.favorite,button=$('#detailFavorite');button.classList.toggle('active',on);button.setAttribute('aria-pressed',on);button.setAttribute('aria-label',on?'Unfavorite symbol':'Favorite symbol');button.disabled=!persistentItem(c.item.id)||!SD.galleryReady;};
SD.beginEdit=function(){const c=SD.current;if(c&&!c.baseline)c.baseline=clone(c.draft);};
SD.finishEdit=function(){const c=SD.current;if(!c||!c.baseline)return;if(JSON.stringify(c.baseline)!==JSON.stringify(c.draft)){c.history.push(c.baseline);if(c.history.length>60)c.history.shift();c.future=[];}c.baseline=null;SD.updateHistory();};
SD.change=function(fn){if(!SD.current)return;SD.finishEdit();SD.beginEdit();fn(SD.current.draft);SD.finishEdit();SD.renderSettings();SD.schedulePreview();SD.updateOutputSummary();};
SD.updateHistory=function(){const c=SD.current;$('#undoEdit').disabled=!c?.history.length;$('#redoEdit').disabled=!c?.future.length;if(c)$('#draftLabel').textContent=JSON.stringify(c.draft.asset)===JSON.stringify(c.original.asset)?'Original stays unchanged':'Customized · draft kept in this tab';};
SD.undo=function(redo=false){const c=SD.current;if(!c)return;SD.finishEdit();const from=redo?c.future:c.history,to=redo?c.history:c.future;if(!from.length)return;to.push(clone(c.draft));c.draft=from.pop();SD.renderSettings();SD.updateHistory();SD.updateOutputSummary();SD.schedulePreview();};
SD.setTab=function(tab){if(!SD.current)return;SD.finishEdit();SD.current.tab=tab;SD.renderSettings();};

function section(title,body,hint='',symbol='sliders'){return `<section class="settings-section"><div class="section-heading"><h3>${icon(symbol)}${esc(title)}</h3>${hint?`<small>${esc(hint)}</small>`:''}</div>${body}</section>`;}
function numberControl(key,label,value,min,max,step=1,unit='',scope='param'){
  const val=Number(Number(value).toFixed(4));
  return `<div class="range-field"><span class="range-label"><span>${esc(label)}</span><span class="range-value"><input type="number" value="${val}" min="${min}" max="${max}" step="${step}" data-scope="${scope}" data-key="${esc(key)}" data-kind="number" data-role="number" aria-label="${esc(label)} value"><small>${esc(unit)}</small></span></span><span class="range-track"><input type="range" value="${val}" min="${min}" max="${max}" step="${step}" data-scope="${scope}" data-key="${esc(key)}" data-kind="number" data-role="range" aria-label="${esc(label)}"></span></div>`;
}
function textControl(key,label,value,scope='param',limit=100){return `<label class="field">${esc(label)}<input type="text" value="${esc(value)}" maxlength="${limit}" data-scope="${scope}" data-key="${esc(key)}" data-kind="text"></label>`;}
function selectControl(key,label,value,options,scope='param'){return `<label class="field">${esc(label)}<select data-scope="${scope}" data-key="${esc(key)}" data-kind="select">${options.map(option=>{const [v,l]=Array.isArray(option)?option:[option,option[0].toUpperCase()+option.slice(1)];return `<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(l)}</option>`;}).join('')}</select></label>`;}
function checkControl(key,label,value,scope='param'){return `<label class="check-field"><span>${esc(label)}</span><input type="checkbox" ${value?'checked':''} data-scope="${scope}" data-key="${esc(key)}" data-kind="boolean"></label>`;}
function colorControl(key,label,value,scope='param',allowNone=true){const v=value||'';return `<div class="color-field"><label for="${scope}-${esc(key)}-hex">${esc(label)}</label><div class="color-input"><input type="color" value="${hex(v)&&hex(v)!=='none'?hex(v):'#193E5B'}" data-scope="${scope}" data-key="${esc(key)}" data-kind="color" aria-label="${esc(label)} color picker"><input id="${scope}-${esc(key)}-hex" type="text" value="${esc(v)}" data-scope="${scope}" data-key="${esc(key)}" data-kind="hex" maxlength="9" spellcheck="false" placeholder="Inherited" aria-label="${esc(label)} hex">${allowNone?`<button class="color-none" data-none="${scope}:${esc(key)}" aria-label="Make ${esc(label)} transparent" title="Transparent / no paint">∅</button>`:''}</div></div>`;}
function paramControl(control,params){const value=params[control.key]??control.default;switch(control.type){case'number':return numberControl(control.key,control.label,value,control.min,control.max,control.step||1,control.unit||'');case'text':return textControl(control.key,control.label,value,'param',control.max_length);case'boolean':return checkControl(control.key,control.label,value);case'select':return selectControl(control.key,control.label,value,control.options);default:return '';}}
function actualPart(){const c=SD.current;return c?.selectedPart?$('#artPreview').querySelector(`[data-part="${CSS.escape(c.selectedPart)}"]`):null;}
function partColor(el,key){if(!el)return '#193E5B';const raw=getComputedStyle(el)[key];if(raw==='none')return 'none';if(hex(raw))return hex(raw);const values=raw.match(/^rgba?\(([^)]+)\)/);if(values){const rgb=values[1].split(/[,\s/]+/).slice(0,3);if(rgb.length===3)return '#'+rgb.map(v=>Math.round(clamp(v,0,255)).toString(16).padStart(2,'0')).join('').toUpperCase();}return '';}
function partRows(){return Array.from($('#artPreview').querySelectorAll('[data-part]')).map(el=>({id:el.dataset.part,label:el.dataset.label||el.dataset.part,hidden:el.getAttribute('visibility')==='hidden'}));}
SD.renderSettings=function(){
  const c=SD.current;if(!c)return;const d=c.draft,p=d.asset.params||{},spec=baseSpec(c.item);
  $$('[data-tab]').forEach(button=>{button.classList.toggle('active',button.dataset.tab===c.tab);button.setAttribute('aria-selected',button.dataset.tab===c.tab);button.tabIndex=button.dataset.tab===c.tab?0:-1;});
  $('#settingsPanel').setAttribute('aria-labelledby',({customize:'tabCustomize',parts:'tabParts',export:'tabExport'})[c.tab]);
  $('#artPreview').classList.toggle('parts-mode',c.tab==='parts');
  let body='';
  if(c.tab==='customize'){
    if(d.asset.type==='custom'||spec?.kind==='svg'){
      body=section('Your imported vector',`<p class="section-note">This is static SVG artwork. Use Inner parts to recolor individual shapes and change their width or height. For automatic counts and geometry controls, add a Python renderer to the project.</p><button class="button" data-go-parts>${icon('sliders')}Edit inner parts</button>`,'','shapes');
    }else{
      const palettes=SD.boot.gallery.palettes.map((pal,i)=>`<button class="palette" data-palette-index="${i}" title="Apply ${esc(pal.name)} palette"><span class="palette-swatches"><i style="background:${esc(pal.fill)}"></i><i style="background:${esc(pal.accent)}"></i><i style="background:${esc(pal.stroke)}"></i></span><span class="palette-name">${esc(pal.name)}</span></button>`).join('');
      body+=section('Colors',`<div class="palette-grid compact">${palettes}</div><div class="color-grid">${colorControl('fill','Main fill',p.fill)}${colorControl('accent','Accent',p.accent)}${colorControl('stroke','Outline',p.stroke)}${colorControl('highlight','Highlight',p.highlight)}</div>`,'Presets or hex','palette');
      body+=section('Geometry',(spec?.controls||[]).map(control=>paramControl(control,p)).join(''),`${spec?.controls.length||0} controls`);
      body+=section('Outline & corners',numberControl('stroke_width','Outline thickness',p.stroke_width,0,20,.5,'u')+numberControl('radius','Corner radius',p.radius,0,48,1,'u')+'<p class="tiny muted" style="margin-top:14px">Controls use a 256-unit design space. Some renderers set fixed corners or outlines for specific parts.</p>');
    }
  }else if(c.tab==='parts'){
    const rows=partRows();const el=actualPart();const override=c.selectedPart?(d.asset.parts[c.selectedPart]||{}):{};
    body=`<div class="part-picker"><div class="inline-note">${icon('info')}<span>Click a shape in the preview, or select it below. Changes affect only that inner part—not the whole symbol.</span></div><label class="field" style="margin-top:17px">Select an inner part<select id="partSelect"><option value="">Choose a part (${rows.length})</option>${rows.map(row=>`<option value="${esc(row.id)}" ${row.id===c.selectedPart?'selected':''}>${esc(row.label)}${row.hidden?' · hidden':''}</option>`).join('')}</select></label></div>`;
    if(el){
      body+=section('Part appearance',`<div class="color-grid">${colorControl('fill','Part fill',override.fill??partColor(el,'fill'),'part')}${colorControl('stroke','Part outline',override.stroke??partColor(el,'stroke'),'part')}</div><div style="margin-top:18px">${numberControl('stroke_width','Outline thickness',override.stroke_width??(parseFloat(el.getAttribute('stroke-width')||getComputedStyle(el).strokeWidth)||0),0,30,.5,'u','part')}</div>`,'Individual override','palette');
      body+=section('Part dimensions',numberControl('sx','Width scale',(override.sx??1)*100,5,400,1,'%','part')+numberControl('sy','Height scale',(override.sy??1)*100,5,400,1,'%','part')+checkControl('hidden','Hide this part',override.hidden||false,'part')+'<p class="tiny muted" style="margin-top:14px">Large parts may need extra padding in Export settings. Color presets do not erase individual overrides.</p>');
      body+='<div class="parts-reset"><button data-reset-part>Reset this part</button><button data-reset-all-parts>Reset all part overrides</button></div>';
    }else{body+='<p class="part-empty">Pick a pin, text line, chart bar, connector or other inner shape to customize it independently.</p>';}
  }else{
    const o=d.output;
    body+=section('Download size',`<div class="output-presets">${[128,256,512,1024].map(size=>`<button data-output-size="${size}" class="${o.width===size&&o.height===size?'active':''}">${size} px</button>`).join('')}</div><div class="two-fields"><label class="field">Width (px)<input type="number" min="16" max="4096" step="1" value="${o.width}" data-scope="output" data-key="width" data-kind="number"></label><label class="field">Height (px)<input type="number" min="16" max="4096" step="1" value="${o.height}" data-scope="output" data-key="height" data-kind="number"></label></div>${checkControl('preserve_aspect','Preserve icon proportions',o.preserve_aspect,'output')}${numberControl('padding','Extra padding',o.padding,0,96,1,'u','output')}`,'One symbol only','download');
    body+=section('Background',checkControl('transparent','Transparent background',o.transparent,'output')+(o.transparent?'':colorControl('background','Background color',o.background,'output',false)),'Preview color is separate','checker');
    body+=section('PNG settings',selectControl('pngScale','PNG resolution',String(d.pngScale),[['1','1× — standard'],['2','2× — retina'],['4','4× — high resolution']],'ui')+`<div class="export-summary-box" id="exportSizeInfo"></div>`,'SVG is always generated first','wave');
    body+=section('File & source',textControl('filename','File name',d.filename,'ui',90)+`<div class="export-tools"><button data-view-source>${icon('code')}View generated SVG</button><button data-save-recipe>${icon('file')}Save editable recipe (.asset.json)</button></div>`,'','file');
  }
  $('#settingsPanel').innerHTML=body;SD.highlightPart();SD.updateOutputSummary();
};
SD.selectPart=function(id){const c=SD.current;if(!c)return;SD.finishEdit();c.selectedPart=id||null;c.tab='parts';SD.renderSettings();};
SD.highlightPart=function(){const c=SD.current;$('#artPreview').querySelectorAll('[data-part]').forEach(el=>el.classList.toggle('selected-part',!!c?.selectedPart&&el.dataset.part===c.selectedPart&&c.tab==='parts'));};
SD.partOverride=function(){const c=SD.current;if(!c?.selectedPart)return null;const parts=c.draft.asset.parts||(c.draft.asset.parts={});const value=parts[c.selectedPart]||(parts[c.selectedPart]={});if(value.cx===undefined){try{const box=actualPart()?.getBBox();if(box){value.cx=box.x+box.width/2;value.cy=box.y+box.height/2;}}catch(_){} }return value;};
SD.applyControl=function(el,final=false){
  const c=SD.current;if(!c||!el.dataset.scope)return;const {scope,key,kind}=el.dataset;let value=el.value;
  if(kind==='number'){
    if(value===''||!Number.isFinite(Number(value)))return;
    const min=el.min===''?-100000:Number(el.min),max=el.max===''?100000:Number(el.max),step=Number(el.step)||1;
    value=clamp(Number(value),min,max);value=Number((min+Math.round((value-min)/step)*step).toFixed(6));
  }else if(kind==='boolean')value=el.checked;
  else if(kind==='color'||kind==='hex'){
    const normalized=hex(value);if(!normalized){if(final)el.setAttribute('aria-invalid','true');return;}value=normalized;el.removeAttribute('aria-invalid');
  }
  SD.beginEdit();
  if(scope==='param')c.draft.asset.params[key]=value;
  if(scope==='part'){const override=SD.partOverride();if(!override)return;override[key]=['sx','sy'].includes(key)?value/100:value;}
  if(scope==='output')c.draft.output[key]=value;
  if(scope==='ui')c.draft[key]=key==='pngScale'?Number(value):value;
  $('#settingsPanel').querySelectorAll(`[data-scope="${scope}"][data-key="${CSS.escape(key)}"]`).forEach(other=>{if(other===el&&!final)return;if(other.type==='checkbox')other.checked=!!value;else if(other.type==='color'){if(value!=='none')other.value=value;}else other.value=value;});
  SD.schedulePreview();SD.updateOutputSummary();
  if(final){SD.finishEdit();if(scope==='output'&&key==='transparent')SD.renderSettings();}
};
SD.schedulePreview=function(){const c=SD.current;if(!c)return;clearTimeout(c.renderTimer);const seq=++c.renderSeq;$('#renderStatus').textContent=SD.engine.ready?'Updating preview…':'Waiting for Python…';c.renderTimer=setTimeout(()=>SD.renderPreview(c,seq),45);};
SD.renderPreview=async function(c,seq){
  if(!SD.engine.ready||SD.current!==c)return;
  try{
    const result=await SD.engine.request({action:'render',asset:clone(c.draft.asset),options:clone(c.draft.output)});
    if(SD.current!==c||seq!==c.renderSeq)return;
    $('#artPreview').innerHTML=result.svg;c.lastSVG=result.svg;$('#renderStatus').textContent='Python-generated SVG';
    const count=partRows().length;$('#previewPartCount').textContent=`${count} inner part${count===1?'':'s'}`;
    if(c.selectedPart&&!actualPart()){c.selectedPart=null;SD.renderSettings();}
    if(c.tab==='parts'){
      const select=$('#partSelect');if(select){const old=select.value;select.innerHTML='<option value="">Choose a part ('+count+')</option>'+partRows().map(row=>`<option value="${esc(row.id)}">${esc(row.label)}${row.hidden?' · hidden':''}</option>`).join('');select.value=old;}
    }
    SD.highlightPart();SD.updateHistory();
  }catch(error){if(SD.current===c&&seq===c.renderSeq){$('#renderStatus').textContent='Preview could not render';toast(error.message,true);}}
};
SD.updateOutputSummary=function(){const c=SD.current;if(!c)return;const o=c.draft.output;$('#outputSummary').textContent=`${o.width} × ${o.height} · ${o.transparent?'Transparent':'Solid background'}`;const info=$('#exportSizeInfo');if(info){const width=o.width*c.draft.pngScale,height=o.height*c.draft.pngScale;info.textContent=`SVG: ${o.width} × ${o.height} px (vector). PNG: ${width} × ${height} px. ${width>8192||height>8192||width*height>50000000?'Too large: lower the size or PNG resolution.':'Padding is included within the requested output size.'}`;}};
SD.updateDownloadState=function(){for(const id of ['#downloadSVG','#downloadPNG'])$(id).disabled=!SD.engine?.ready||!!SD.exporting;$('#saveVariant').disabled=!SD.engine?.ready||!SD.galleryReady||!!SD.exporting;};
SD.downloadAsset=async function(format){
  const c=SD.current;if(!c||!SD.engine.ready||SD.exporting)return;SD.finishEdit();const d=clone(c.draft);SD.exporting=true;SD.updateDownloadState();
  try{
    const result=await SD.engine.request({action:'export',asset:d.asset,options:d.output});let blob;
    if(format==='svg')blob=new Blob([result.svg],{type:'image/svg+xml;charset=utf-8'});
    else blob=await SD.engine.png(d.asset,d.output,d.pngScale);
    downloadFile(blob,safeName(d.filename)+'.'+format);toast(`${format.toUpperCase()} ready — one symbol, no layout attached.`);
  }catch(error){libraryError(error);}finally{SD.exporting=false;SD.updateDownloadState();}
};
SD.recipe=function(){const c=SD.current;if(!c)return null;return {format:'svgdrawer.asset',schema_version:1,name:c.item.name,asset:clone(c.draft.asset),output:clone(c.draft.output)};};
SD.saveRecipe=function(){if(!SD.current)return;SD.finishEdit();downloadJSON(SD.recipe(),safeName(SD.current.draft.filename)+'.asset.json');toast('Editable recipe saved.');};
SD.showSource=async function(){try{const c=SD.current;if(!c)return;SD.finishEdit();const result=await SD.engine.request({action:'export',asset:clone(c.draft.asset),options:clone(c.draft.output)});SD.sourceExport={svg:result.svg,name:safeName(c.draft.filename)};$('#sourceText').value=result.svg.replace(/></g,'>\n<');showDialog('sourceDialog');}catch(error){libraryError(error);}};

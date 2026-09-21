/* Gallery navigation, searching, sorting and lazy thumbnail rendering. */
SD.renderNavigation=function(){
  const items=allSymbols(),counts=new Map();for(const item of items)counts.set(item.category,(counts.get(item.category)||0)+1);
  const nav=(id,name,symbol,count)=>`<button class="nav-item ${SD.state.filter===id?'active':''}" data-filter="${esc(id)}" aria-current="${SD.state.filter===id?'page':'false'}">${icon(symbol)}<span class="nav-name">${esc(name)}</span><span class="nav-count">${count}</span></button>`;
  $('#exploreNav').innerHTML=nav('all','Gallery','collection',items.length)+nav('favorites','Favorites','heart',allSymbols().filter(s=>s.favorite).length);
  $('#categoryNav').innerHTML=allCategories().map(c=>nav(c.id,c.name,c.icon,counts.get(c.id)||0)).join('');
  $('#mobileCategory').innerHTML=`<option value="all">Gallery (${items.length})</option><option value="favorites">Favorites (${allSymbols().filter(s=>s.favorite).length})</option>`+allCategories().map(c=>`<option value="${esc(c.id)}">${esc(c.name)} (${counts.get(c.id)||0})</option>`).join('');
  $('#mobileCategory').value=SD.state.filter;
  $('#totalSymbols').textContent=items.length;$('#totalCategories').textContent=allCategories().length;
};
SD.renderGrid=function(){
  const filter=SD.state.filter,query=SD.state.query.trim().toLowerCase();
  const category=allCategories().find(c=>c.id===filter);
  const label=category?.name||({all:'Gallery',favorites:'Favorites',mine:'My Gallery'}[filter]||'Gallery');
  let items=allSymbols().filter(item=>filter==='all'||(filter==='favorites'&&!!item.favorite)||item.category===filter);
  if(query){const terms=query.split(/\s+/);items=items.filter(item=>{const hay=[item.id,item.name,item.style||baseSpec(item)?.style,item.description,categoryName(item.category),...(item.tags||[])].join(' ').toLowerCase();return terms.every(term=>hay.includes(term));});}
  if(SD.state.sort==='name')items.sort((a,b)=>a.name.localeCompare(b.name));
  if(SD.state.sort==='recent')items.sort((a,b)=>(b.created_at||'').localeCompare(a.created_at||'')||a.name.localeCompare(b.name));
  $('#galleryTitle').innerHTML=esc(label)+` <span class="count-pill" id="resultCount">${items.length}</span>`;
  $('#breadcrumbLabel').textContent=label;
  $('#galleryDescription').textContent=category?.description||({favorites:'The symbols you want to keep close.',all:'Pick a symbol to explore its possibilities.'}[filter]||'Your custom collection.');
  $('#activeSearch').classList.toggle('hidden',!query);$('#activeSearch').innerHTML=query?`${items.length} result${items.length===1?'':'s'} for “${esc(SD.state.query.trim())}” <button data-clear-query>Clear search</button>`:'';
  const visible=items.slice(0,SD.state.limit);
  $('#symbolGrid').innerHTML=visible.map(item=>{
    const thumb=SD.thumbs.get(item.id),favorite=!!item.favorite,spec=baseSpec(item),count=spec?.controls?.length||0;
    return `<article class="symbol-card" data-category="${esc(item.category)}"><button class="open-card" data-open="${esc(item.id)}" aria-label="Customize ${esc(item.name)}"><span class="card-preview"><span class="card-category">${esc(categoryName(item.category))}</span>${thumb?`<img class="thumb-img" data-thumb="${esc(item.id)}" src="${svgURL(thumb)}" alt="" loading="lazy">`:`<span class="loading-thumb" data-thumb-placeholder="${esc(item.id)}">${icon('shapes')}</span>`}</span><span class="card-info"><span class="card-title">${esc(item.name)}</span><span class="card-description">${esc(item.description||'A custom addition to your Gallery.')}</span><span class="card-bottom"><span>${item.customizable?'customizable · '+count+' controls':'Static SVG'}</span><span class="customize-link">Customize ${icon('arrow-right')}</span></span></span></button><button class="favorite-button ${favorite?'active':''}" data-favorite="${esc(item.id)}" ${!SD.galleryReady?'disabled':''} aria-label="${favorite?'Unfavorite':'Favorite'} ${esc(item.name)}" aria-pressed="${favorite}">${icon('heart')}</button></article>`;
  }).join('');
  $('#emptyState').classList.toggle('hidden',items.length>0);$('#loadMore').classList.toggle('hidden',items.length<=visible.length);
  if(!items.length){$('#emptyState h3').textContent=query?'No matching symbols':filter==='favorites'?'Your favorites start here':'No symbols here yet';$('#emptyState p').textContent=query?'Try another name, category or search tag.':filter==='favorites'?'Click the heart on any symbol to save it here.':'Add a custom SVG or save a variation to this category.';}
  for(const item of visible){if(!SD.thumbs.has(item.id))SD.ensureThumbnail(item);}
};
SD.ensureThumbnail=async function(item){
  if(!SD.engine.ready||SD.thumbJobs.has(item.id)||SD.thumbs.has(item.id))return;
  SD.thumbJobs.add(item.id);const revision=SD.revision;
  try{
    const result=await SD.engine.request({action:'export',asset:item.asset||{type:item.id},options:{width:256,height:256,padding:8}});
    if(revision!==SD.revision)return;
    SD.thumbs.set(item.id,result.svg);
    const hero=({chip:'#heroChip',waveform:'#heroWave',code_page:'#heroPage'})[item.id];if(hero)$(hero).innerHTML=result.svg;
    const placeholders=$$(`[data-thumb-placeholder="${CSS.escape(item.id)}"]`);
    for(const placeholder of placeholders){const image=document.createElement('img');image.className='thumb-img';image.dataset.thumb=item.id;image.src=svgURL(result.svg);image.alt='';placeholder.replaceWith(image);}
  }catch(error){console.warn('Thumbnail unavailable:',item.id,error.message);}
  finally{SD.thumbJobs.delete(item.id);if(revision!==SD.revision&&findItem(item.id))SD.ensureThumbnail(findItem(item.id));}
};
SD.refreshGallery=function(){SD.renderNavigation();SD.renderGrid();};
SD.setFilter=function(id){if(!['all','favorites',...allCategories().map(c=>c.id)].includes(id))id='all';SD.state.filter=id;SD.state.limit=48;SD.refreshGallery();};
SD.toggleFavorite=async function(id){const item=findItem(id);if(!item)return;await SD.manage({action:'update-symbol',id,favorite:!item.favorite});if(SD.current)SD.updateFavorite();};


import {clone,allPhotos,pathsOf,catalogText,validateCatalog,removePhoto,savePhoto,renamePlace,changesBetween,sha256} from './model.js';

const OWNER='enfjp', REPO='enfjp.github.io', ROOT=`/repos/${OWNER}/${REPO}`;
const $=id=>document.getElementById(id);
const text=(tag,value,cls='')=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e;};
let token='', original=null, catalog=null, catalogSha='', busy=false, readonly=true, shown=36, editing=null;
const stagedBlobs=new Map(), previews=new Map(), pendingUploads=new Map();
let inactivity=null, statusTimer=null;

if(window.top!==window.self) {document.body.replaceChildren(text('p','请在独立窗口打开照片管理。'));throw Error('Framed editor blocked');}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
function writeAllowed(){if(!token||readonly)throw Error('请先用 enfjp 的 GitHub 授权连接。');if(busy)throw Error('正在处理，请稍候。');}
function renewSession(){clearTimeout(inactivity);if(token)inactivity=setTimeout(()=>{token='';readonly=true;status('授权已因 30 分钟未操作而清除。未提交修改仍在本页面内，请重新连接后保存。');$('auth').hidden=false;render();},30*60*1000);}
async function api(path,method='GET',body){
  if(!token)throw Error('尚未授权。');
  // Never accept caller-provided origins, redirects, or cookies for credentialed requests.
  if(!path.startsWith(ROOT+'/') && path!==ROOT && path!=='/user')throw Error('不允许的 API 目标。');
  renewSession();
  const response=await fetch('https://api.github.com'+path,{method,credentials:'omit',redirect:'error',cache:'no-store',
    headers:{Accept:'application/vnd.github+json',Authorization:'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28',...(body?{'Content-Type':'application/json'}:{})},
    ...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(90000)});
  const data=response.status===204?{}:await response.json();
  if(!response.ok){
    const hint=response.status===401?'授权无效或已过期，请重新创建令牌。':response.status===403?'GitHub 拒绝操作。请检查令牌是否仅选中了本站仓库并具有 Contents: Read and write 权限；也可能触发了速率限制。':response.status===409||response.status===422?'仓库发生变化或 GitHub 拒绝提交。当前修改仍保留，请先核对仓库版本。':`GitHub 请求失败（${response.status}），当前修改仍保留。`;
    throw Error(hint);
  }
  return data;
}
const decode64=s=>new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\s/g,'')),c=>c.charCodeAt(0)));
function bytes64(array){const b=new Uint8Array(array);let s='';for(let i=0;i<b.length;i+=32768)s+=String.fromCharCode(...b.subarray(i,i+32768));return btoa(s);}
function dirty(){return original&&catalog&&catalogText(original)!==catalogText(catalog);}
function releasePreviews(){for(const url of previews.values())URL.revokeObjectURL(url);previews.clear();pendingUploads.clear();stagedBlobs.clear();$('uploads').replaceChildren();}
async function readCatalog(){
  const ref=await api(ROOT+'/git/ref/heads/main');
  const item=await api(ROOT+'/contents/content/photography.json?ref='+ref.object.sha);
  const value=(item.encoding==='base64'&&item.content)?item:await api(ROOT+'/git/blobs/'+item.sha);
  if(value.encoding!=='base64'||!value.content)throw Error('无法读取图库目录。');
  const c=JSON.parse(decode64(value.content));validateCatalog(c);return {c,sha:item.sha};
}
$('connect').addEventListener('click',async()=>{
  if(busy)return;
  const supplied=$('token').value.trim();$('token').value='';
  if(!supplied.startsWith('github_pat_')){status('请使用 Fine-grained personal access token，不要输入 GitHub 密码或旧式全权限令牌。',true);return;}
  token=supplied;busy=true;$('connect').disabled=true;
  try{
    const user=await api('/user');if(user.login.toLowerCase()!==OWNER)throw Error('需要授权 enfjp 账号；当前账号不匹配。');
    const repo=await api(ROOT);if(!repo.permissions?.push)throw Error('此授权无法写入本站仓库。');
    const {c,sha}=await readCatalog();
    if(dirty() && catalogSha && sha!==catalogSha)throw Error('连接期间云端图库已改变。请先保存本地记录并刷新，不会覆盖云端内容。');
    if(!dirty()){original=clone(c);catalog=clone(c);catalogSha=sha;releasePreviews();}
    readonly=false;$('auth').hidden=true;$('logout').hidden=false;$('editor').hidden=false;
    status('已验证 enfjp。修改会先保留在当前页面，点击“保存并发布”后才提交。请勿在此页面粘贴任何其他账号密码。');
  }catch(e){token='';readonly=true;status(e.message,true);}finally{busy=false;$('connect').disabled=false;render();}
});
$('preview').addEventListener('click',async()=>{
  if(busy)return;
  try{const r=await fetch('../photography/catalog-public.json',{cache:'no-store'});if(!r.ok)throw Error('只读目录暂不可用。');const c=await r.json();delete c.catalog_sha256;validateCatalog(c);original=clone(c);catalog=clone(c);readonly=true;catalogSha='';$('editor').hidden=false;status('只读预览：可以浏览已发布作品，所有写入按钮均不可用。');render();}catch(e){status(e.message,true);}
});
$('logout').addEventListener('click',()=>{
  if(busy)return;if(dirty()&&!confirm('退出将丢弃当前页面尚未发布的修改，是否继续？'))return;
  token='';clearTimeout(inactivity);readonly=true;releasePreviews();original=catalog=null;catalogSha='';$('editor').hidden=true;$('auth').hidden=false;$('logout').hidden=true;status('已退出，页面内存中的授权已清除。');
});
function photoUrl(p){if(previews.has(p.id))return previews.get(p.id);const v=p.variants[0];return 'https://raw.githubusercontent.com/'+OWNER+'/'+REPO+'/main/'+v.src;}
function options(select,rows,current,first){select.replaceChildren();if(first){const op=new Option(first[0],first[1]);select.add(op);}for(const [name,value] of rows)select.add(new Option(name,value));if([...select.options].some(o=>o.value===current))select.value=current;}
function refreshSelects(){if(!catalog)return;const topics=catalog.collections.map(c=>[c.name,c.slug]);const places=catalog.places.map(p=>[p.name,p.id]);
  for(const id of ['topic-filter','upload-topic','edit-topic'])options($(id),topics,$(id).value,id==='topic-filter'?['全部题材','all']:null);
  for(const id of ['place-filter','upload-place','edit-place'])options($(id),places,$(id).value,id==='place-filter'?['全部地点','all']:null);
}
function render(){
  if(!catalog)return;refreshSelects();const all=allPhotos(catalog),visible=all.filter(x=>x.photo.published!==false);
  $('total').textContent=all.length;$('published').textContent=visible.length;$('featured').textContent=visible.filter(x=>catalog.selected.includes(x.photo.id)).length;
  const paths=new Map();for(const {photo} of visible)for(const v of photo.variants)paths.set(v.src,v.size_bytes||0);
  const bytes=[...paths.values()].reduce((a,b)=>a+b,0);$('storage').textContent=(bytes/1e6).toFixed(1)+' MB';
  const d=dirty();let msg='没有待保存的修改。';if(d){const v=changesBetween(original,catalog);msg=`待发布：新增 ${v.added}，编辑 ${v.edited}，下架 ${v.hidden}，恢复 ${v.restored}，删除 ${v.deleted}${v.places?'；地点已调整':''}${v.selected?'；精选已调整':''}。`;}
  if(bytes>800e6)msg+=' 图片接近容量预警线，请先检查网站总大小。';
  $('pending').textContent=msg;$('publish').disabled=readonly||busy||!d;$('discard').disabled=busy||!d;$('files').disabled=readonly||busy;$('add-place').disabled=readonly||busy;
  renderLibrary();renderPlaces();
}
function renderLibrary(){
  if(!catalog)return;const q=$('search').value.trim().toLowerCase(),topic=$('topic-filter').value,place=$('place-filter').value,mode=$('state-filter').value;
  const found=allPhotos(catalog).filter(({photo:p,collection:c})=>(topic==='all'||topic===c.slug)&&(place==='all'||place===p.location_id)&&(!q||(p.title+' '+p.location).toLowerCase().includes(q))&&(mode==='all'||(mode==='hidden'&&p.published===false)||(mode==='published'&&p.published!==false)||(mode==='selected'&&catalog.selected.includes(p.id))));
  $('library').replaceChildren();
  for(const {photo:p,collection:c} of found.slice(0,shown)){
    const card=text('article','','card');card.dataset.id=p.id;const img=document.createElement('img');img.src=photoUrl(p);img.alt=p.alt;img.loading='lazy';card.append(img);
    const body=text('div','','card-body');body.append(text('h3',p.title),text('p',p.location),text('p',c.name));
    if(p.published===false)body.append(text('span','已下架','tag'));if(catalog.selected.includes(p.id))body.append(text('span','精选','tag'));if(c.cover===p.src)body.append(text('span','封面','tag'));
    const actions=text('div','','card-actions');
    for(const [name,action,cls] of [['编辑',()=>openEdit(p.id),''],[p.published===false?'恢复展示':'下架',()=>togglePhoto(p.id),''],['删除',()=>deletePhoto(p.id),'danger']]){
      const button=text('button',name,cls);button.type='button';button.disabled=readonly||busy;button.addEventListener('click',action);actions.append(button);
    }
    if(catalog.selected.includes(p.id))for(const [label,step] of [['精选上移',-1],['精选下移',1]]){const b=text('button',label);b.disabled=readonly||busy;b.addEventListener('click',()=>{try{writeAllowed();const i=catalog.selected.indexOf(p.id),j=i+step;if(j<0||j>=catalog.selected.length)return;[catalog.selected[i],catalog.selected[j]]=[catalog.selected[j],catalog.selected[i]];render();}catch(e){status(e.message,true);}});actions.append(b);}
    body.append(actions);card.append(body);$('library').append(card);
  }
  if(!found.length)$('library').append(text('p','没有符合条件的作品。','note'));
  $('more').hidden=found.length<=shown;
}
for(const id of ['search','topic-filter','place-filter','state-filter'])$(id).addEventListener(id==='search'?'input':'change',()=>{shown=36;renderLibrary();});
$('more').addEventListener('click',()=>{shown+=36;renderLibrary();});
for(const tab of document.querySelectorAll('[data-tab]'))tab.addEventListener('click',()=>{document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b===tab)));document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==tab.dataset.tab);});
function openEdit(id){try{writeAllowed();const item=allPhotos(catalog).find(x=>x.photo.id===id);if(!item)return;editing=id;const p=item.photo;$('edit-image').src=photoUrl(p);$('edit-title').value=p.title;$('edit-alt').value=p.alt;$('edit-topic').value=item.collection.slug;$('edit-place').value=p.location_id;$('edit-published').checked=p.published!==false;$('edit-selected').checked=catalog.selected.includes(id);$('edit-cover').checked=item.collection.cover===p.src;$('edit-dialog').showModal();}catch(e){status(e.message,true);}}
$('edit-close').addEventListener('click',()=>$('edit-dialog').close());
$('edit-form').addEventListener('submit',event=>{event.preventDefault();try{writeAllowed();const item=allPhotos(catalog).find(x=>x.photo.id===editing);const p=clone(item.photo);p.title=$('edit-title').value.trim();p.alt=$('edit-alt').value.trim();p.location_id=$('edit-place').value;p.location=catalog.places.find(x=>x.id===p.location_id).name;p.published=$('edit-published').checked;const trial=clone(catalog);savePhoto(trial,p,$('edit-topic').value,{featured:$('edit-selected').checked,cover:$('edit-cover').checked});validateCatalog(trial);catalog=trial;$('edit-dialog').close();render();}catch(e){status(e.message,true);}});
function togglePhoto(id){try{writeAllowed();const p=allPhotos(catalog).find(x=>x.photo.id===id)?.photo;if(!p)return;if(p.published!==false&&!confirm('将这张照片加入待下架修改？原图和 GitHub 历史不会被清除。'))return;p.published=p.published===false;render();}catch(e){status(e.message,true);}}
function deletePhoto(id){try{writeAllowed();const p=allPhotos(catalog).find(x=>x.photo.id===id)?.photo;if(!p)return;if(prompt('删除“'+p.title+'”？保存后将从当前图库和当前版本的图片目录移除，但不是历史擦除。输入“删除”确认：')!=='删除')return;removePhoto(catalog,id);render();}catch(e){status(e.message,true);}}
function renderPlaces(){
  $('places').replaceChildren();for(const place of catalog.places){const row=text('div','','place-row');row.append(text('span',place.name));
    const rename=text('button','改名');rename.disabled=readonly||busy;rename.addEventListener('click',()=>{try{writeAllowed();const name=prompt('新的地点名称（将同步更新该地点全部作品）：',place.name);if(name===null)return;const trial=clone(catalog);renamePlace(trial,place.id,name);validateCatalog(trial);catalog=trial;render();}catch(e){status(e.message,true);}});
    const remove=text('button','删除地点','danger');remove.disabled=readonly||busy;remove.addEventListener('click',()=>{try{writeAllowed();if(allPhotos(catalog).some(x=>x.photo.location_id===place.id))throw Error('仍有照片使用该地点，请先移动这些照片，包括已下架的作品。');if(confirm('删除地点“'+place.name+'”？')){catalog.places=catalog.places.filter(p=>p.id!==place.id);render();}}catch(e){status(e.message,true);}});row.append(rename,remove);$('places').append(row);}
}
$('add-place').addEventListener('click',()=>{try{writeAllowed();const name=$('new-place').value.trim();if(!name||name.length>180)throw Error('请输入有效地点名称。');if(catalog.places.some(p=>p.name.toLowerCase()===name.toLowerCase()))throw Error('这个地点已经存在。');let id=name.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,70).replace(/-$/,'');if(!id||catalog.places.some(p=>p.id===id))id='place-'+crypto.randomUUID().split('-')[0];catalog.places.push({id,name});$('new-place').value='';render();}catch(e){status(e.message,true);}});

$('export-catalog').addEventListener('click',()=>{if(!catalog)return;const blob=new Blob([catalogText(catalog)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='photography-catalog-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

$('discard').addEventListener('click',()=>{if(!busy&&confirm('放弃所有尚未发布的修改和新图片？')){catalog=clone(original);releasePreviews();render();status('已放弃未发布的修改，网站未改变。');}});

async function webpVersions(file,id){
  const bitmap=await createImageBitmap(file,{imageOrientation:'from-image',colorSpaceConversion:'default'});
  try{
    if(bitmap.width*bitmap.height>60000000)throw Error('像素数量过大，请先导出长边 3200 像素的 sRGB JPEG。');
    const variants=[],blobs=[];let width=0,height=0,full='';
    for(const [edge,quality] of [[800,.88],[1400,.90],[2048,.92]]){
      const scale=Math.min(1,edge/Math.max(bitmap.width,bitmap.height));const w=Math.max(1,Math.round(bitmap.width*scale)),h=Math.max(1,Math.round(bitmap.height*scale));
      const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
      const ctx=canvas.getContext('2d',{colorSpace:'srgb'});if(!ctx)throw Error('浏览器不能处理图片。');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(bitmap,0,0,w,h);
      const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('图片转换失败。')),'image/webp',quality));canvas.width=canvas.height=1;
      if(blob.type!=='image/webp')throw Error('当前浏览器不支持导出 WebP，请使用较新的 Chrome 或 Edge。');
      const src=`assets/photos/uploads/${id}-${edge}.webp`;blobs.push({src,blob});
      // Identical widths are not repeated in srcset for small source files.
      const same=variants.findIndex(v=>v.width===w);if(same>=0)variants.splice(same,1);
      variants.push({src,width:w,size_bytes:blob.size});
      if(edge===1400){width=w;height=h;}if(edge===2048)full=src;
    }
    return {photo:{id,title:'',alt:'',src:`assets/photos/uploads/${id}-1400.webp`,full,width,height,variants,display:height>width?'portrait':'landscape',published:true},blobs};
  }finally{bitmap.close();}
}
$('files').addEventListener('change',async()=>{
  try{writeAllowed();}catch(e){status(e.message,true);return;}
  const files=[...$('files').files];$('files').value='';if(files.length>20){status('请每次选择不超过 20 张照片。',true);return;}
  busy=true;render();let prepared=0;const errors=[];
  for(const file of files){
    try{
      if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('仅支持 JPEG、PNG、WebP。');
      if(file.size>100*1024*1024)throw Error('超过 100 MB，请先导出缩小版。');
      status('正在本地转换：'+file.name+'。原文件不会上传。');
      const hash=await sha256(await file.arrayBuffer());const id='photo-'+hash.slice(0,20);
      if(allPhotos(catalog).some(x=>x.photo.id===id||x.photo.source_sha256===hash)||pendingUploads.has(id))throw Error('同一文件已在图库或本次待处理列表中。');
      const item=await webpVersions(file,id);item.photo.source_sha256=hash;item.topic=$('upload-topic').value;item.photo.location_id=$('upload-place').value;item.photo.location=catalog.places.find(p=>p.id===item.photo.location_id).name;
      item.name=file.name;previews.set(id,URL.createObjectURL(item.blobs[item.blobs.length-1].blob));pendingUploads.set(id,item);renderUpload(item);prepared++;
    }catch(e){errors.push(file.name+'：'+e.message);}
  }
  busy=false;render();status(`本地转换完成 ${prepared} 张。请填写每张的标题和描述，点击“加入待发布”，最后统一保存。`+(errors.length?'\n'+errors.join('\n'):''),errors.length>0);
});
function renderUpload(item){
  const p=item.photo,row=text('div','','upload-item');row.dataset.uploadId=p.id;
  const img=document.createElement('img');img.src=previews.get(p.id);img.alt='新照片预览';row.append(img);
  const details=document.createElement('div');details.append(text('p',item.name+' · '+p.location));
  const titleLabel=text('label','作品标题（不要用文件名）');const titleInput=document.createElement('input');titleInput.maxLength=160;titleInput.placeholder='简短描述性标题';titleLabel.append(titleInput);
  const altLabel=text('label','画面描述');const altInput=document.createElement('textarea');altInput.rows=2;altInput.maxLength=600;altInput.placeholder='描述照片中可见的主体和环境';altLabel.append(altInput);
  details.append(titleLabel,altLabel,text('p','三个网页文件合计 '+(item.blobs.reduce((a,b)=>a+b.blob.size,0)/1e6).toFixed(2)+' MB。请对照原片检查色彩。'));
  const confirmLabel=text('label','我确认照片可公开且符合当前无人像选片要求。','check');const approved=document.createElement('input');approved.type='checkbox';confirmLabel.prepend(approved);details.append(confirmLabel);
  const add=text('button','加入待发布','primary');add.addEventListener('click',()=>{try{writeAllowed();if(!approved.checked)throw Error('请先确认照片的公开范围和人物检查。');const photo=clone(p);const place=catalog.places.find(x=>x.id===photo.location_id);if(!place)throw Error('待上传照片的地点已删除，请重新选择照片和地点。');photo.location=place.name;photo.title=titleInput.value.trim();photo.alt=altInput.value.trim();const trial=clone(catalog);savePhoto(trial,photo,item.topic);validateCatalog(trial);catalog=trial;for(const b of item.blobs)stagedBlobs.set(b.src,b.blob);pendingUploads.delete(p.id);row.remove();render();status('已加入待发布；尚未上传或修改网站。');}catch(e){status(e.message,true);}});
  const cancel=text('button','不使用');cancel.addEventListener('click',()=>{if(busy)return;pendingUploads.delete(p.id);URL.revokeObjectURL(previews.get(p.id));previews.delete(p.id);row.remove();});details.append(add,cancel);row.append(details);$('uploads').append(row);
}

$('publish').addEventListener('click',async()=>{
  try{writeAllowed();validateCatalog(catalog);}catch(e){status(e.message,true);return;}
  const changes=changesBetween(original,catalog);if(!dirty())return;
  if(!confirm(`即将保存到公开网站：新增 ${changes.added}，编辑 ${changes.edited}，下架 ${changes.hidden}，恢复 ${changes.restored}，删除 ${changes.deleted}。\n\n未点击“加入待发布”的新照片不会提交。删除不是清除 Git 历史。是否继续？`))return;
  busy=true;render();clearTimeout(statusTimer);
  const nextCatalog=clone(catalog),nextText=catalogText(nextCatalog);
  try{
    let ref=await api(ROOT+'/git/ref/heads/main');
    let current=await api(ROOT+'/contents/content/photography.json?ref='+ref.object.sha);
    if(current.sha!==catalogSha)throw Error('云端目录已被其他页面或操作修改。为防覆盖，本次没有提交；请先导出记录并刷新核对。');
    const nextPaths=new Set(allPhotos(nextCatalog).flatMap(x=>pathsOf(x.photo)));
    const entries=[];let done=0;
    for(const [path,blob] of stagedBlobs){if(!nextPaths.has(path))continue;status(`上传网页图片 ${++done} / ${stagedBlobs.size}，请保持页面打开。`);const value=await api(ROOT+'/git/blobs','POST',{content:bytes64(await blob.arrayBuffer()),encoding:'base64'});entries.push({path,mode:'100644',type:'blob',sha:value.sha});}
    // A generated-docs commit can occur while files upload. Rebase only if catalog is unchanged.
    ref=await api(ROOT+'/git/ref/heads/main');current=await api(ROOT+'/contents/content/photography.json?ref='+ref.object.sha);
    if(current.sha!==catalogSha)throw Error('上传期间云端目录已改变。图片对象已传输，但没有更新图库或覆盖他人修改。');
    const commit=await api(ROOT+'/git/commits/'+ref.object.sha);
    const oldPaths=new Set(allPhotos(original).flatMap(x=>pathsOf(x.photo)));
    const removed=[...oldPaths].filter(p=>!nextPaths.has(p));
    if(removed.length){const tree=await api(ROOT+'/git/trees/'+commit.tree.sha+'?recursive=1');if(tree.truncated)throw Error('仓库目录过大，无法安全确认删除范围。');const exists=new Set(tree.tree.map(x=>x.path));for(const path of removed)for(const target of [path,'docs/'+path])if(exists.has(target))entries.push({path:target,mode:'100644',type:'blob',sha:null});}
    entries.push({path:'content/photography.json',mode:'100644',type:'blob',content:nextText});
    const tree=await api(ROOT+'/git/trees','POST',{base_tree:commit.tree.sha,tree:entries});
    const created=await api(ROOT+'/git/commits','POST',{message:'Update photography from owner editor',tree:tree.sha,parents:[ref.object.sha]});
    // A non-fast-forward update fails rather than discarding concurrent commits.
    await api(ROOT+'/git/refs/heads/main','PATCH',{sha:created.sha,force:false});
    const blob=tree.tree?.find(x=>x.path==='content/photography.json');
    const saved=blob?{sha:blob.sha}:await api(ROOT+'/contents/content/photography.json?ref='+created.sha);
    original=clone(nextCatalog);catalog=clone(nextCatalog);catalogSha=saved.sha;stagedBlobs.clear();
    status('修改已提交到 GitHub，正在等待自动生成和发布；现在还不表示公网已经更新。');
    const expected=await sha256(nextText);waitForPublish(expected,0);
  }catch(e){status(e.message+' 未确认的修改会保留在当前页面，不会显示为已上线。',true);}finally{busy=false;render();}
});
async function waitForPublish(expected,attempt){
  try{const r=await fetch('../photography/catalog-public.json?revision='+expected.slice(0,12)+'&t='+Date.now(),{cache:'no-store'});if(r.ok&&(await r.json()).catalog_sha256===expected){status('网站已返回对应的新目录，发布已确认。可以打开 Photography 检查照片。');return;}}catch{}
  if(attempt>=24){status('修改已提交，但暂未从网站确认发布。请查看 GitHub Actions 的“Publish photo library”及 Pages 构建结果，不要重复上传。');const a=document.createElement('a');a.href=`https://github.com/${OWNER}/${REPO}/actions`;a.target='_blank';a.rel='noopener noreferrer';a.textContent=' 查看构建记录 ↗';$('status').append(a);return;}
  statusTimer=setTimeout(()=>waitForPublish(expected,attempt+1),10000);
}
window.addEventListener('beforeunload',event=>{if(dirty()||pendingUploads.size||busy){event.preventDefault();event.returnValue='';}});

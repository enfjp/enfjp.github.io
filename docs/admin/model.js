/* Photo catalog operations only. Credentials never enter this module or the catalog. */
export const TOPICS = ['wild', 'land', 'on-the-road'];
const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const clone = value => JSON.parse(JSON.stringify(value));
export const allPhotos = catalog => catalog.collections.flatMap(c => c.photos.map(p => ({photo:p, collection:c})));
export const pathsOf = p => [...new Set([p.src, p.full, ...p.variants.map(v=>v.src)])];
export const catalogText = catalog => JSON.stringify(catalog, null, 2) + '\n';
export function validateCatalog(catalog) {
  const places = new Map((catalog.places || []).map(p=>[p.id,p.name]));
  if (places.size !== (catalog.places || []).length) throw Error('地点 ID 重复。');
  for (const [id,name] of places) if (!slug.test(id) || typeof name !== 'string' || !name.trim() || name.length>180) throw Error('地点名称无效。');
  const topicIds = catalog.collections.map(c=>c.slug);
  if (topicIds.length!==3 || TOPICS.some(t=>!topicIds.includes(t))) throw Error('图库题材目录不兼容。');
  const ids = new Set();
  for (const {photo:p} of allPhotos(catalog)) {
    if (!slug.test(p.id) || ids.has(p.id)) throw Error('照片 ID 无效或重复。');
    ids.add(p.id);
    for (const [key,max] of [['title',160],['alt',600]]) if(typeof p[key]!=='string'||!p[key].trim()||p[key].length>max) throw Error('请填写照片标题和画面描述，且不要超过长度限制。');
    if (!places.has(p.location_id) || places.get(p.location_id)!==p.location) throw Error('照片地点与地点目录不一致。');
    if (typeof (p.published ?? true)!=='boolean') throw Error('发布状态无效。');
    if (!['wide','landscape','portrait'].includes(p.display)) throw Error('照片布局无效。');
    for (const key of ['width','height']) if (!Number.isInteger(p[key]) || p[key]<1 || p[key]>2048) throw Error('图片尺寸无效。');
    if (!Array.isArray(p.variants)||!p.variants.length) throw Error('缺少图片尺寸。');
    const widths = p.variants.map(v=>v.width);
    if (new Set(widths).size!==widths.length || widths.some(w=>!Number.isInteger(w)||w<1||w>2048)) throw Error('图片尺寸不能重复或超出范围。');
    for (const path of pathsOf(p)) if (!/^assets\/photos\/[A-Za-z0-9/_-]+\.webp$/.test(path)) throw Error('图片路径无效。');
  }
  if (new Set(catalog.selected).size!==catalog.selected.length || catalog.selected.some(id=>!ids.has(id))) throw Error('精选列表包含未知或重复照片。');
  return true;
}
export function removePhoto(catalog,id) {
  for(const c of catalog.collections) {
    const found=c.photos.find(p=>p.id===id);
    c.photos=c.photos.filter(p=>p.id!==id);
    if(found && c.cover===found.src) c.cover=c.photos.find(p=>p.published!==false)?.src||'';
  }
  catalog.selected=catalog.selected.filter(p=>p!==id);
}
export function savePhoto(catalog,photo,topic,{featured=false,cover=false}={}) {
  const current = allPhotos(catalog).find(x=>x.photo.id===photo.id);
  if(current && current.collection.slug===topic) {
    current.collection.photos[current.collection.photos.findIndex(p=>p.id===photo.id)]=clone(photo);
  } else {
    if(current) {
      current.collection.photos=current.collection.photos.filter(p=>p.id!==photo.id);
      if(current.collection.cover===current.photo.src) current.collection.cover=current.collection.photos.find(p=>p.published!==false)?.src||'';
    }
    const c=catalog.collections.find(c=>c.slug===topic);
    if(!c)throw Error('请选择有效题材。');
    c.photos.push(clone(photo));
  }
  const c=catalog.collections.find(c=>c.slug===topic);
  if(cover || !c.cover)c.cover=photo.src;
  if(featured && !catalog.selected.includes(photo.id))catalog.selected.push(photo.id);
  if(!featured)catalog.selected=catalog.selected.filter(id=>id!==photo.id);
}
export function renamePlace(catalog,id,name) {
  const p=catalog.places.find(p=>p.id===id);if(!p)throw Error('地点不存在。');
  p.name=name.trim();
  for(const {photo} of allPhotos(catalog))if(photo.location_id===id)photo.location=p.name;
}
export function changesBetween(before,after) {
  const a=new Map(allPhotos(before).map(x=>[x.photo.id,x]));
  const b=new Map(allPhotos(after).map(x=>[x.photo.id,x]));
  const counts={added:0,deleted:0,hidden:0,restored:0,edited:0,places:0,selected:false};
  for(const [id,item] of b) {
    if(!a.has(id)){counts.added++;continue;}
    const old=a.get(id);
    if(old.photo.published!==false && item.photo.published===false)counts.hidden++;
    else if(old.photo.published===false && item.photo.published!==false)counts.restored++;
    else if(JSON.stringify(old.photo)!==JSON.stringify(item.photo)||old.collection.slug!==item.collection.slug)counts.edited++;
  }
  for(const id of a.keys())if(!b.has(id))counts.deleted++;
  counts.places=JSON.stringify(before.places)!==JSON.stringify(after.places)?1:0;
  counts.selected=JSON.stringify(before.selected)!==JSON.stringify(after.selected);
  return counts;
}
export async function sha256(input) {
  const bytes=typeof input==='string'?new TextEncoder().encode(input):input;
  const hash=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('');
}

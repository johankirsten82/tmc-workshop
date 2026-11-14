// Runs the REAL sync/Code.gs in Node with an in-memory fake Google Sheet.
// Usage: node gas_server.js <port> <teamCode>   — test use only.
const http=require('http'),fs=require('fs'),path=require('path'),vm=require('vm');
const port=+process.argv[2],code=(process.argv[3]&&process.argv[3]!=='-')?process.argv[3]:null;  // '-' = no TEAM_CODE (token-only app)
let props={};if(code)props.TEAM_CODE=code;
function Sheet(name){this.name=name;this.rows=[];this.fmt={};}
// like real Sheets: a date-like string typed into a cell that is NOT plain text ('@') becomes a Date
const coerce=(s,r,c,x)=>(typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&s.fmt[r+','+c]!=='@')?new Date(x+'T00:00:00'):x;
const disp=x=>x instanceof Date?x.toString():(x===undefined?'':String(x));
Sheet.prototype={getLastRow(){return this.rows.length},appendRow(r){const n=this.rows.length+1;this.rows.push(r.map((x,j)=>coerce(this,n,j+1,x)))},setFrozenRows(){},setColumnWidth(){},getName(){return this.name},getLastColumn(){return Math.max(0,...this.rows.map(r=>r.length))},
 getRange(r,c,nr,nc){const s=this;nr=nr||1;nc=nc||1;return{getValues(){const o=[];for(let i=0;i<nr;i++){const row=s.rows[r-1+i]||[];o.push(Array.from({length:nc},(_,j)=>row[c-1+j]===undefined?'':row[c-1+j]))}return o},
  getDisplayValues(){return this.getValues().map(row=>row.map(disp))},
  setFontWeight(){return this},setNumberFormat(f){for(let i=0;i<nr;i++)for(let j=0;j<nc;j++)s.fmt[(r+i)+','+(c+j)]=f;return this},setBackground(){return this},setFontColor(){return this},clearContents(){return this.clearContent()},clear(){return this.clearContent()},
  setValues(v){v.forEach((row,i)=>{const R=s.rows[r-1+i]||(s.rows[r-1+i]=[]);row.forEach((x,j)=>R[c-1+j]=coerce(s,r+i,c+j,x))})},clearContent(){for(let i=0;i<nr;i++)s.rows[r-1+i]=(s.rows[r-1+i]||[]).map(()=> '')}}}};
let sheets={},ssName='Untitled spreadsheet',trig=[],drive={n:0,files:{},folders:{}};
const ctx={console,JSON,Date,Number,String,Object,Math,
 SpreadsheetApp:(()=>{const ss={getSheetByName:n=>sheets[n]||null,insertSheet:n=>(sheets[n]=new Sheet(n)),setActiveSheet(){},getId:()=>'testsheet',getName:()=>ssName,rename:n=>{ssName=String(n)},getSheets:()=>Object.values(sheets)};return{getActiveSpreadsheet:()=>ss,getActive:()=>ss}})(),
 CacheService:{getScriptCache:()=>{const m={};return{get:k=>k in m?m[k]:null,put:(k,v)=>{m[k]=String(v)},remove:k=>{delete m[k]}}}},
 DriveApp:(()=>{const mkF=(id,name,bytes)=>({id,name,bytes,trashed:false,created:new Date(),getId(){return this.id},getName(){return this.name},getUrl(){return 'https://drive.google.com/file/d/'+this.id+'/view'},getBlob(){const b=this.bytes;return{getBytes:()=>b}},setTrashed(v){this.trashed=!!v},isTrashed(){return this.trashed},getDateCreated(){return this.created},setSharing(){}});
  const mkD=(id,name)=>({id,name,trashed:false,getId(){return this.id},getName(){return this.name},isTrashed(){return this.trashed},setSharing(){},
   createFile(b){const f=mkF('file'+(++drive.n),b.getName(),b.getBytes());f.folder=this.id;drive.files[f.id]=f;return f},
   getFiles(){const a=Object.values(drive.files).filter(f=>f.folder===this.id&&!f.trashed);let i=0;return{hasNext:()=>i<a.length,next:()=>a[i++]}}});
  return{getFoldersByName:()=>({hasNext:()=>false}),createFolder:n=>{const d=mkD('fold'+(++drive.n),n);drive.folders[d.id]=d;return d},
   getFolderById:id=>{if(!drive.folders[id])throw new Error('no folder');return drive.folders[id]},getFileById:id=>{if(!drive.files[id])throw new Error('no file');return drive.files[id]},Access:{},Permission:{}}})(),
 Utilities:{getUuid:()=>require('crypto').randomUUID(),Charset:{UTF_8:'utf8'},DigestAlgorithm:{SHA_256:'sha256',MD5:'md5'},
  computeDigest:(a,v)=>Array.from(require('crypto').createHash(a||'sha256').update(String(v)).digest()).map(b=>b>127?b-256:b),
  base64Decode:s=>Array.from(Buffer.from(s,'base64')),base64Encode:b=>Buffer.from(b.map?b.map(x=>x&255):b).toString('base64'),newBlob:(d,t,n)=>({getBytes:()=>d,setName(){return this},getName:()=>n})},
 PropertiesService:{getScriptProperties:()=>({getProperty:k=>k in props?props[k]:null,setProperty:(k,v)=>{props[k]=String(v)},deleteProperty:k=>{delete props[k]},getProperties:()=>Object.assign({},props)})},
 ScriptApp:{getProjectTriggers:()=>trig.slice(),deleteTrigger:t=>{trig=trig.filter(x=>x!==t)},newTrigger:fn=>{const b={timeBased:()=>b,everyDays:()=>b,atHour:()=>b,nearMinute:()=>b,everyHours:()=>b,create:()=>{const t={getHandlerFunction:()=>fn};trig.push(t);return t}};return b}},
 LockService:{getScriptLock:()=>({tryLock:()=>true,waitLock(){},releaseLock(){}})},
 ContentService:{MimeType:{JSON:'json'},createTextOutput:s=>({s,setMimeType(){return this}})}};
/* v1.6.0: fake TMC Assets behind UrlFetchApp (codes 'wsc' items, 'rdc' locations); /_assets?mode=ok|down|busy, /_assets?locs=JSON */
const FA={mode:'ok',items:{},calls:[],locs:[{id:'c-alfa',name:'10 Alfa',camp:'10 Alfa',places:[{id:'p-store',name:'Store A'},{id:'p-yard',name:'yard'}]},{id:'c-bravo',name:'Bravo',camp:'Bravo',places:[]}]};
ctx.UrlFetchApp={fetch:(url,opt)=>{const b=JSON.parse(opt.payload);FA.calls.push(b.action);const R=(o,c)=>({getResponseCode:()=>c||200,getContentText:()=>JSON.stringify(o)});
 if(FA.mode==='down')throw new Error('Address unavailable');if(FA.mode==='busy')return R({ok:false,error:'busy_try_again'});
 if(b.action==='listLocations')return R(b.code==='rdc'?{ok:true,locations:FA.locs}:{ok:false,error:'bad_code'});
 if(b.action!=='importFinishedItem')return R({ok:false,error:'bad_request'});if(b.code!=='wsc')return R({ok:false,error:'bad_code'});
 const it=b.item||{};if(it.destinationApp!=='tmcassets')return R({ok:false,error:'wrong_app'});const camp=FA.locs.find(c=>c.id===it.campId);if(!camp)return R({ok:false,error:'bad_camp'});
 if(FA.items[it.id])return R({ok:true,itemId:'wsf-'+it.id,placeId:FA.items[it.id].placeId,result:'duplicate'});
 let pid=it.placeId||'';if(!pid&&it.placeName){const m=camp.places.find(p=>p.name.toLowerCase()===String(it.placeName).toLowerCase());pid=m?m.id:'p-new-'+Object.keys(FA.items).length}
 FA.items[it.id]={item:it,placeId:pid};return R({ok:true,itemId:'wsf-'+it.id,placeId:pid,result:'accepted'})}};
vm.createContext(ctx);const SRC=fs.readFileSync(process.env.GAS_FILE||path.join(__dirname,'..','sync','Code.gs'),'utf8');vm.runInContext(SRC,ctx);
let log=[];
http.createServer((q,res)=>{let b='';q.on('data',d=>b+=d);q.on('end',()=>{
 const H={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Content-Type':'application/json'};
 if(q.method==='OPTIONS'){res.writeHead(204,H);return res.end()}
 if(q.url.startsWith('/_dump')){const s=sheets._Records;const recs=s?s.rows.slice(1).map(r=>({kind:r[1],id:r[2],u:r[3],del:r[4],data:r[7]?JSON.parse(r[7]):null})):[];res.writeHead(200,H);return res.end(JSON.stringify({recs,log,users:sheets.Users?sheets.Users.rows:[]}))}
 if(q.url.startsWith('/_sheets')){res.writeHead(200,H);return res.end(JSON.stringify(Object.fromEntries(Object.entries(sheets).map(([k,v])=>[k,v.rows]))))}
 // test-only hooks: run setupOnce (optionally with a code / triggers swapped in), set a Script Property, read state
 if(q.url.startsWith('/_setup')){const u=new URL(q.url,'http://x');if(u.searchParams.has('code'))vm.runInContext('TEAM_CODE_SETUP='+JSON.stringify(u.searchParams.get('code')),ctx);if(u.searchParams.has('trig'))vm.runInContext('TRIGGERS='+u.searchParams.get('trig'),ctx);
  let o;try{o=JSON.parse(ctx.setupOnce())}catch(e){o={err:String(e)}}res.writeHead(200,H);return res.end(JSON.stringify(o))}
 if(q.url.startsWith('/_assets')){const u=new URL(q.url,'http://x');if(u.searchParams.has('mode'))FA.mode=u.searchParams.get('mode');if(u.searchParams.has('locs'))FA.locs=JSON.parse(u.searchParams.get('locs'));if(u.searchParams.has('retry'))ctx.assetsRetry();res.writeHead(200,H);return res.end(JSON.stringify(FA))}
 if(q.url.startsWith('/_prop')){const u=new URL(q.url,'http://x');for(const [k,v] of u.searchParams){if(v==='')delete props[k];else props[k]=v}res.writeHead(200,H);return res.end('{}')}
 if(q.url.startsWith('/_state')){res.writeHead(200,H);return res.end(JSON.stringify({name:ssName,triggers:trig.map(t=>t.getHandlerFunction()),props:Object.keys(props).filter(k=>k.indexOf('TOK_')&&k.indexOf('FAIL_')),teamCode:props.TEAM_CODE||null,tabs:Object.keys(sheets),src:/__TMC_TEAM_CODE__/.test(SRC)}))}
 if(q.url.startsWith('/_drive')){res.writeHead(200,H);return res.end(JSON.stringify({folders:Object.values(drive.folders).map(d=>({id:d.id,name:d.name})),files:Object.values(drive.files).map(f=>({id:f.id,name:f.name,folder:f.folder,trashed:f.trashed,size:f.bytes.length})),folderProp:props.PHOTO_FOLDER_ID||null}))}
 if(q.url.startsWith('/_age')){const u=new URL(q.url,'http://x'),id=u.searchParams.get('id'),days=+u.searchParams.get('days');const k='pl:'+id,s=sheets._Records;let hit=0;if(s)s.rows.forEach(r=>{if(r[0]===k){const d=JSON.parse(r[7]);d.at=new Date(Date.now()-days*864e5).toISOString();r[7]=JSON.stringify(d);hit=1;if(drive.files[d.fid])drive.files[d.fid].created=new Date(Date.now()-days*864e5)}});res.writeHead(200,H);return res.end(JSON.stringify({hit}))}
 if(q.url.startsWith('/_cleanup')){let o;try{o={n:ctx.photoCleanup()}}catch(e){o={err:String(e)}}res.writeHead(200,H);return res.end(JSON.stringify(o))}
 if(q.url.startsWith('/_reset')){sheets={};ssName='Untitled spreadsheet';trig=[];drive.n=0;drive.files={};drive.folders={};props=code?{TEAM_CODE:code}:{};log=[];res.writeHead(200,H);return res.end('{}')}
 if(q.method==='POST'){let j={};try{j=JSON.parse(b)}catch(e){}log.push({t:Date.now(),device:j.device,since:j.since,n:(j.changes||[]).length});
  const o=ctx.doPost({postData:{contents:b}});res.writeHead(200,H);return res.end(o.s)}
 res.writeHead(200,H);res.end(ctx.doGet().s)})}).listen(port,'127.0.0.1',()=>console.log('gas ready '+port));

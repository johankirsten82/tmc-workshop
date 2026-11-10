// VER 7 server guard unit test: discard_ never removes the main Admin (any alias), yourself or the last Admin; staff/team code refused.
const fs=require('fs'),path=require('path'),vm=require('vm');
const props={TOK_a:JSON.stringify({uid:'s1'}),TOK_b:JSON.stringify({uid:'x'})};
const ctx={console,JSON,Date,Number,String,Object,Math,PropertiesService:{getScriptProperties:()=>({getProperty:k=>k in props?props[k]:null,setProperty:(k,v)=>{props[k]=String(v)},deleteProperty:k=>{delete props[k]},getProperties:()=>Object.assign({},props)})}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.env.GAS_FILE||path.join(__dirname,'..','sync','Code.gs'),'utf8'),ctx);
const rec=u=>({key:'u:'+u.id,kind:'u',id:u.id,u:1,del:0,data:JSON.stringify(u)});
const mk=L=>{const st={map:{}};L.forEach(u=>st.map['u:'+u.id]=rec(u));return st};
const store=mk([{id:'a1',name:'Template Admin',status:'active',admin:1},{id:'a2',name:'Pat Boss',status:'active',admin:1},{id:'s1',name:'Staff One',status:'active'},{id:'m2',name:'johan a. kirsten',status:'active',admin:1},{id:'p1',name:'Johan Kirsten',status:'pending'}]);
const solo=mk([{id:'a2',name:'Pat Boss',status:'active',admin:1}]);
const D=id=>[{kind:'u',id:id,u:9,del:1,data:{discarded:1}}];
const run=(st,me,ch)=>{const r={n:0};const kept=ctx.discard_(st,me,ch,r);return {kept:kept.length,why:r.discWhy||''}};
const o={
 mainByAdmin:run(store,{id:'a2',admin:1},D('a1')),
 mainAlias:run(store,{id:'a2',admin:1},D('m2')),
 mainBlock:run(store,{id:'a2',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Template Admin',status:'blocked',admin:1}}]),
 mainPurge:run(store,null,[{kind:'u',id:'a1',u:9,del:1,purge:1,data:null}]),
 pendingAlias:run(store,{id:'a2',admin:1},D('p1')),
 demote:run(store,{id:'a2',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Template Admin',status:'active',admin:0}}]),
 rename:run(store,{id:'a2',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Someone Else',status:'active',admin:1}}]),
 aliasRename:run(store,{id:'a1',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Johan Kirsten',status:'active',admin:1}}]),
 resetPin:run(store,{id:'a2',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Template Admin',status:'active',admin:1,pinReset:5}}]),
 mainEdit:run(store,{id:'a2',admin:1},[{kind:'u',id:'a1',u:9,del:0,data:{id:'a1',name:'Template Admin',status:'active',admin:1,perms:[]}}]),
 lastAdmin:run(solo,{id:'ghost',admin:1},D('a2')),
 self:run(store,{id:'a2',admin:1},D('a2')),
 staff:run(store,{id:'s1'},D('a2')),
 code:run(store,null,D('s1')),
 ok:run(store,{id:'a2',admin:1},D('s1')),
 tokGone:!('TOK_a' in props)&&('TOK_b' in props)
};
console.log(JSON.stringify(o));

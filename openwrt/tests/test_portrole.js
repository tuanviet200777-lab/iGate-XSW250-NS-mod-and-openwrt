const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const base=path.resolve(__dirname,'../files/www/luci-static/resources');
const role=new Function('baseclass',fs.readFileSync(base+'/xsw250ns/portrole.js','utf8'))({extend:x=>x});
new Function(fs.readFileSync(base+'/view/status/include/98_xsw250ns_port_v2.js','utf8'));
const ports=['lan2p5','lan1','lan2','lan3','lan4'];
function fixture(){return {network:{br:{'.type':'device',name:'br-lan',type:'bridge',ports:ports.slice(1)},lan:{'.type':'interface',device:'br-lan'},wan:{'.type':'interface',device:'lan2p5',proto:'pppoe',password:'fixture-secret'},wan6:{'.type':'interface',device:'@wan',proto:'dhcpv6'}},firewall:{z:{'.type':'zone',name:'wan',network:['wan','wan6']}}};}
function apply(f,port,action){for(const op of role.plan(f.network,f.firewall,action,port)){const c=f[op.config];if(op.type)c[op.section]={'.type':op.type};else if(op.remove)delete c[op.section];else if(op.value==null)delete c[op.section][op.option];else c[op.section][op.option]=op.value;}}
let count=0;
for(const a of ports)for(const b of ports){const f=fixture();apply(f,a,'wan');apply(f,b,'wan');assert.equal(f.network.wan.device,b);assert.equal(f.network.wan.password,'fixture-secret');assert.equal(f.network.wan6.device,'@wan');assert.equal(new Set(f.network.br.ports).size,4);for(const p of ports)assert.equal(role.inspect(f.network,f.firewall,p).role,p===b?'wan':'lan');count++;}
for(const p of ports){const f=fixture();apply(f,p,'wan');apply(f,p,'lan');assert.equal(f.network.wan.disabled,'1');assert.equal(f.network.wan6.disabled,'1');apply(f,p,'wan');assert.equal(f.network.wan.disabled,undefined);assert.equal(f.network.wan6.disabled,undefined);count++;}
for(const mutate of [f=>f.network.br.vlan_filtering='1',f=>f.network.x={'.type':'interface',device:'lan3'},f=>f.network.x={'.type':'device',name:'lan2.10'},f=>f.firewall.x={'.type':'zone',name:'guest',network:['wan']},f=>f.network.wan.device='tun0']){const f=fixture();mutate(f);const before=JSON.stringify(f);assert.throws(()=>role.plan(f.network,f.firewall,'wan','lan4'));assert.equal(JSON.stringify(f),before);count++;}
console.log(count+' port-role cases passed; UI syntax parsed');

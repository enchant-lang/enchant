// Rebuild the distributable native DOM/geometry/code adapters from pinned deps.
import {build,version} from 'esbuild';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../..');
const output=path.join(root,'priv/lib/live/edit/assets/runtime');await mkdir(output,{recursive:true});
const result=await build({absWorkingDir:root,entryPoints:[path.join(root,'priv/lib/live/edit/host.mjs')],outfile:path.join(output,'host.js'),
  nodePaths:[path.join(here,'node_modules')],bundle:true,format:'esm',target:'es2022',minify:true,
  legalComments:'linked',metafile:true,logLevel:'warning'});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const inputs={};for(const name of Object.keys(result.metafile.inputs)){
  const absolute=path.resolve(root,name);if(absolute.startsWith(path.join(root,'priv/')))inputs[path.relative(root,absolute)]=digest(await readFile(absolute));
}
const lock=await readFile(path.join(here,'package-lock.json'));
await writeFile(path.join(output,'build.json'),JSON.stringify({schema:'enchant.edit.host/1',esbuild:version,lock_sha256:digest(lock),inputs,
  artifact_sha256:digest(await readFile(path.join(output,'host.js')))},null,2)+'\n');
console.log(JSON.stringify({status:'built',inputs:Object.keys(inputs).length,bytes:(await readFile(path.join(output,'host.js'))).length}));

const notices=[];
for(const name of Object.keys(result.metafile.inputs).filter(n=>n.includes('/node_modules/'))){
  const start=name.slice(0,name.indexOf('/node_modules/')+14),parts=name.slice(start.length).split('/');
  const pkg=parts[0].startsWith('@')?parts.slice(0,2).join('/'):parts[0];
  const pkgRoot=path.resolve(root,start,pkg);if(notices.some(row=>row.root===pkgRoot))continue;
  const meta=JSON.parse(await readFile(path.join(pkgRoot,'package.json'),'utf8'));
  let license;for(const file of ['LICENSE','LICENSE.md','LICENSE.txt'])try{license=await readFile(path.join(pkgRoot,file),'utf8');break;}catch{}
  if(!license)throw Error('Missing license: '+pkgRoot);
  notices.push({root:pkgRoot,name:meta.name,version:meta.version,license});
}
await writeFile(path.join(output,'THIRD-PARTY.txt'),notices.sort((a,b)=>a.name.localeCompare(b.name)).map(p=>`${p.name} ${p.version}\n${p.license}`).join('\n\n'));

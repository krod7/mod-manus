import {clone,normalize,validate,compile,simulate,operation,escapeHTML,TYPES} from './engine.js';
import {samples} from './samples.js';
import {renderIcons,icon} from './icons.js';
import {intake,download} from './upload.js';
import {convert,health,getEndpoint,setEndpoint} from './api.js';
import {FlowchartView} from './flowchart-view.js';
import {CodeView} from './code-view.js';
import {stage,toast,showValidation} from './status.js';
import {guideHTML} from './guide.js';

const $=id=>document.getElementById(id), esc=escapeHTML;
const storeKey='modulo.workspace.v1';
let projects=[],currentId='',result=null,selected=null,history=[],future=[],busy=false,sourceURL=null,editorTab='node',replaceTarget=null,generationToken=0;
try{const saved=JSON.parse(localStorage.getItem(storeKey)||'null');if(saved?.projects?.length){projects=saved.projects.slice(0,40).map(p=>({...p,graph:normalize(p.graph),source:null}));currentId=saved.currentId;}}catch{/* Recover with a sample if storage was damaged. */}
if(!projects.length){projects=[{id:crypto.randomUUID(),graph:normalize(samples[0]),demo:true,generated:true,reviewed:true,recognitionWarnings:[]}];currentId=projects[0].id;}
if(!projects.some(p=>p.id===currentId))currentId=projects[0].id;
const current=()=>projects.find(p=>p.id===currentId);
const graph=()=>current().graph;
const language=()=>$('language').value;
const codeView=new CodeView($('code-content'),select);
const flowView=new FlowchartView($('graph-svg'),{
 onSelect:select,
 onMove:(id,x,y,phase)=>{if(phase==='start')pushHistory();else{save();updateUndo();}},
 onConnect:(source,target)=>{if(busy)return;pushHistory();const n=graph().nodes.find(n=>n.id===source),used=graph().edges.filter(e=>e.source===source);graph().edges.push({id:newId('e',graph().edges),source,target,label:n.type==='decision'?(used.some(e=>/^yes$/i.test(e.label))?'No':'Yes'):''});invalidate();toast('Connection added. Review its direction and label.');}
});
function newId(prefix,list){let i=1;while(list.some(n=>n.id===`${prefix}${i}`))i++;return `${prefix}${i}`;}
function save(){
 try{localStorage.setItem(storeKey,JSON.stringify({currentId,projects:projects.map(({source,...p})=>p)}));$('save-state').innerHTML='<span class="green-dot"></span> Saved locally';}
 catch{$('save-state').textContent='Not saved — export a backup';}
 renderProjects();
}
function renderProjects(){
 $('project-count').textContent=projects.length;
 $('project-list').innerHTML=projects.map(p=>`<button class="project-item ${p.id===currentId?'active':''}" data-project="${p.id}"><span class="project-indicator"></span><span>${esc(p.graph.name)}</span></button>`).join('');
}
function pushHistory(){history.push(clone(graph()));if(history.length>50)history.shift();future=[];updateUndo();}
function updateUndo(){$('undo').disabled=!history.length;$('redo').disabled=!future.length;}
function check(){const validation=validate(graph());showValidation(validation);flowView.setIssues(validation);return validation;}
function render(fit=false){
 $('flow-title').textContent=graph().name;$('breadcrumb-name').textContent=graph().name;$('demo-badge').hidden=!current().demo;
 $('node-count').textContent=`${graph().nodes.length} nodes`;
 flowView.setGraph(graph(),fit);check();codeView.setResult(result);
 $('generated-label').textContent=result?(current().demo?'GENERATED · DEMO':'GENERATED · REVIEWED'):'NOT YET GENERATED';
 $('copy-code').disabled=!result;$('download-code').disabled=!result;$('run-flow').disabled=Boolean(validate(graph()).errors.length);
 stage(result?4:2,result?'Ready to explore':'Review your graph');renderProjects();updateUndo();
 if(selected)select(selected.id,selected.kind,false);else $('inspector').hidden=true;
}
function invalidate(){current().demo=false;current().generated=false;result=null;save();render();}
function select(id,kind='node',scroll=true){
 selected={id,kind};flowView.select(id,kind);codeView.select(id,kind,scroll);
 const n=kind==='node'?graph().nodes.find(n=>n.id===id):graph().edges.find(e=>e.id===id);if(!n){$('inspector').hidden=true;return;}
 const t=result?.trace.find(t=>kind==='node'?t.nodeId===id&&!t.edgeId:t.edgeId===id),title=kind==='node'?n.label:`${n.source} → ${n.target}${n.label?' · '+n.label:''}`;
 $('inspector').hidden=false;$('inspector').innerHTML=`<span class="inspector-id">${esc(id)}</span><div class="inspector-main"><strong>${esc(title)}</strong><p>${kind==='node'?`${esc(n.type.toUpperCase())} · ${n.confidence<.8?'UNCERTAIN RECOGNITION':'REVIEWABLE ELEMENT'}${n.note?' · '+esc(n.note):''}`:'DIRECTED CONNECTION · TRACE TO ITS SOURCE TRANSITION'}</p></div><span class="inspector-lines">${t?`SOURCE L${Math.min(...t.codeLines)}–${Math.max(...t.codeLines)} ↔ PSEUDO L${Math.min(...t.pseudoLines)}–${Math.max(...t.pseudoLines)}`:'GENERATE TO TRACE'}</span><button class="button small" id="inspect-edit">${icon('edit')} Edit ${kind}</button>`;
 $('inspect-edit').onclick=()=>openEditor(kind==='edge'?'connections':'node');
}
function modal(title,html,eyebrow='MODULO WORKSPACE'){$('modal-title').textContent=title;$('modal-eyebrow').textContent=eyebrow;$('modal-body').innerHTML=html;renderIcons($('modal-body'));if(!$('modal').open)$('modal').showModal();}
function closeModal(){replaceTarget=null;$('modal').close();}
$('close-modal').onclick=closeModal;
$('modal').addEventListener('click',e=>{if(e.target===$('modal')){const r=$('modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeModal();}});

function openImport(target=null){if(busy)return;replaceTarget=typeof target==='string'?target:null;modal(replaceTarget?'Replace this flowchart.':'Bring your logic in.',`<p class="modal-copy">${replaceTarget?'The chosen file will replace this flow’s graph and original file. Export a backup first if needed.':'One flowchart. A clear path to code. Import a single-page file, then inspect the reconstructed logic before generating.'}</p><div class="dropzone" id="dropzone" role="button" tabindex="0"><span class="dropzone-icon" data-icon="upload"></span><strong>Drop your flowchart here</strong><p>or choose a file from your computer<br>One file · One page · Up to 10 MB</p><button class="button primary" id="browse-file">Choose file</button></div><div class="import-formats"><div class="format-note"><span class="tag">BROWSER-ONLY</span><strong>JSON · Modulo SVG · draw.io · Mermaid</strong>Structured diagrams convert locally. No API, key, or account required.</div><div class="format-note api"><span class="tag">PYTHON API REQUIRED</span><strong>PNG · JPEG · Single-page PDF</strong>OCR and visual recognition need a connected backend. Always review its results.</div></div><div id="import-error" class="error-text" role="alert"></div><div class="modal-actions"><button class="button left" id="import-sample">Explore an example instead</button><button class="text-button" id="import-api">API connection →</button></div>`,'01 / IMPORT FLOWCHART');
 const zone=$('dropzone');zone.onclick=()=>{$('file-input').value='';$('file-input').click();};zone.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();zone.click();}};
 zone.ondragover=e=>{e.preventDefault();zone.classList.add('over');};zone.ondragleave=()=>zone.classList.remove('over');zone.ondrop=e=>{e.preventDefault();zone.classList.remove('over');if(e.dataTransfer.files.length!==1){$('import-error').textContent='Attach exactly one file at a time.';return;}importFile(e.dataTransfer.files[0]);};
 $('import-sample').onclick=openSamples;$('import-api').onclick=openSettings;
}
async function importFile(file){
 if(busy)return;const replacing=replaceTarget;busy=true;$('import-error')&&($('import-error').textContent='');stage(1,'Reading your flowchart…',true);
 const zone=$('dropzone');if(zone){zone.style.pointerEvents='none';zone.innerHTML='<span class="busy-spinner"></span><strong>Reading your file…</strong><p>OCR can take up to 90 seconds.</p>';}
 try{
  const data=await intake(file,(i,m)=>stage(i,m,true));
  if(!replacing&&projects.length>=40)throw new Error('This workspace has 40 flows. Export and remove a flow before importing another.');
  const p={id:replacing||crypto.randomUUID(),graph:data.graph,demo:false,generated:false,reviewed:!data.needsReview,recognitionWarnings:data.warnings,source:data.source};
  if(replacing){const index=projects.findIndex(p=>p.id===replacing);if(index<0)throw new Error('The flow being replaced no longer exists.');projects[index]=p;}else projects.push(p);
  currentId=p.id;replaceTarget=null;result=null;history=[];future=[];selected=null;save();render(true);showGraphTab();closeModal();toast(replacing?'Flowchart replaced. Review the new graph.':'Flow imported. Review the graph before generating.');
  if(data.needsReview||validate(graph()).errors.length)openValidation();
 }catch(e){busy=false;stage(0,'Import needs attention');if($('modal').open){openImport(replacing);$('import-error').textContent=e.message;}else toast(e.message,true);}
 finally{busy=false;}
}
// Intake errors must be able to restore the import dialog while work is marked busy.
$('file-input').onchange=()=>{if($('file-input').files.length===1)importFile($('file-input').files[0]);};
$('import-button').onclick=openImport;
function openSamples(){modal('Start with a working example.',`<p class="modal-copy">Explore a complete flow, inspect its trace map, then make it your own. These examples run entirely in your browser.</p>${samples.map((s,i)=>`<div class="sample-card"><span class="sample-mark">${esc(s.mark)}</span><div><h3>${esc(s.name)}</h3><p>${esc(s.description)}<br>${s.nodes.length} nodes · ${i===1?'Loop + branch':i===0?'Two-way branch':'Sequential logic'}</p></div><button class="button small" data-sample="${i}">Open flow →</button></div>`).join('')}`,'EXAMPLE LIBRARY');$('modal-body').querySelectorAll('[data-sample]').forEach(el=>el.onclick=()=>{if(projects.length>=40){toast('Export and remove a flow first. Maximum: 40.',true);return;}const p={id:crypto.randomUUID(),graph:normalize(samples[Number(el.dataset.sample)]),demo:true,generated:true,reviewed:true,recognitionWarnings:[]};projects.push(p);currentId=p.id;result=compile(p.graph,language());history=[];future=[];selected=null;save();render(true);closeModal();});}
$('samples-button').onclick=openSamples;$('guide-button').onclick=()=>modal('Draw with intention.',guideHTML,'THE FLOWCHART FIELD GUIDE');$('workspace-button').onclick=()=>{renderProjects();toast(`${projects.length} flow${projects.length>1?'s':''} saved in this browser.`);};
$('project-list').onclick=e=>{const el=e.target.closest('[data-project]');if(!el||busy)return;currentId=el.dataset.project;history=[];future=[];selected=null;result=null;try{if(current().generated)result=compile(graph(),language());}catch{current().generated=false;}save();render(true);showGraphTab();};
$('new-project').onclick=()=>{if(busy)return;if(projects.length>=40){toast('Maximum 40 flows. Export and remove a flow first.',true);return;}const p={id:crypto.randomUUID(),graph:normalize({name:'Untitled flow',nodes:[{id:'start',type:'start',label:'Start',x:330,y:160},{id:'end',type:'end',label:'End',x:330,y:360}],edges:[{id:'e1',source:'start',target:'end',label:''}]}),demo:false,generated:false,reviewed:true,recognitionWarnings:[]};projects.push(p);currentId=p.id;result=null;selected=null;history=[];future=[];save();render(true);openRename();};
function openRename(){modal('Name this flow.',`<label class="field">Flow name<input id="rename-input" maxlength="100" value="${esc(graph().name)}"></label><div class="modal-actions"><button class="button danger-button left" id="remove-project">Remove local flow</button><button class="button primary" id="save-name">Save name</button></div>`);$('save-name').onclick=()=>{const name=$('rename-input').value.trim();if(!name){toast('Add a flow name.',true);return;}pushHistory();graph().name=name;invalidate();closeModal();};$('remove-project').onclick=()=>{modal('Remove this local flow?',`<p class="modal-copy">“${esc(graph().name)}” will be removed from this browser. Export a backup first if you need it. Other flows will stay untouched.</p><div class="modal-actions"><button class="button left" id="backup-remove">Export backup</button><button class="button" id="cancel-remove">Keep flow</button><button class="button danger-button" id="confirm-remove">Remove flow</button></div>`);$('backup-remove').onclick=exportProject;$('cancel-remove').onclick=closeModal;$('confirm-remove').onclick=()=>{projects=projects.filter(p=>p.id!==currentId);if(!projects.length)projects=[{id:crypto.randomUUID(),graph:normalize(samples[0]),demo:true,generated:true,reviewed:true,recognitionWarnings:[]}];currentId=projects[0].id;result=current().generated?compile(graph(),language()):null;selected=null;history=[];future=[];save();render(true);closeModal();toast('Local flow removed.');};};}
$('rename-flow').onclick=openRename;
function exportProject(){download(JSON.stringify({schemaVersion:1,graph:graph()},null,2),`${slug()}.modulo.json`,'application/json');toast('Flow exported with nodes, connections and notes.');}
function slug(){return graph().name.toLowerCase().replace(/[^a-z0-9]+/g,'_')||'flow';}
$('export-project').onclick=exportProject;$('export-svg').onclick=()=>{download(flowView.exportSVG(),`${slug()}.svg`,'image/svg+xml');toast('SVG exported with re-importable graph metadata.');};
$('undo').onclick=()=>{if(!history.length)return;future.push(clone(graph()));current().graph=history.pop();current().generated=false;result=null;save();render();};
$('redo').onclick=()=>{if(!future.length)return;history.push(clone(graph()));current().graph=future.pop();current().generated=false;result=null;save();render();};
$('zoom-in').onclick=()=>flowView.zoom(1.2);$('zoom-out').onclick=()=>flowView.zoom(.8);$('fit-view').onclick=()=>flowView.fit();
function setMode(mode){flowView.setMode(mode);$('select-mode').classList.toggle('active',mode==='select');$('connect-mode').classList.toggle('active',mode==='connect');if(mode==='connect')toast('Click the source node, then its destination.');}
$('select-mode').onclick=()=>setMode('select');$('connect-mode').onclick=()=>setMode('connect');
$('add-node').onclick=()=>{if(busy)return;pushHistory();const id=newId('node',graph().nodes);graph().nodes.push({id,type:'process',label:'total = 0',x:330,y:Math.max(...graph().nodes.map(n=>n.y))+100,confidence:1,note:'',color:''});selected={id,kind:'node'};invalidate();flowView.fit();openEditor('node');};
function showGraphTab(){$('source-preview').hidden=true;$('graph-svg').style.visibility='visible';$('graph-tab').classList.add('active');$('source-tab').classList.remove('active');}
$('graph-tab').onclick=showGraphTab;
$('source-tab').onclick=()=>{
 const source=current().source;const host=$('source-preview');host.replaceChildren();if(sourceURL){URL.revokeObjectURL(sourceURL);sourceURL=null;}
 if(!source){const p=document.createElement('pre');p.textContent=current().demo?'This example was created as a structured graph. Export JSON or SVG to try importing it.':'Original files are previewed only during this session. Re-import the file to view it again. Saved graphs do not store original files.';host.append(p);}
 else if(source.kind==='text'){const p=document.createElement('pre');p.textContent=source.text;host.append(p);}
 else {sourceURL=URL.createObjectURL(source.file);const element=document.createElement(source.kind==='pdf'?'iframe':'img');element.src=sourceURL;if(source.kind==='image')element.alt='Original uploaded flowchart';else element.title='Original uploaded one-page PDF';host.append(element);}
 const actions=document.createElement('div');actions.className='modal-actions';actions.innerHTML='<button class="button small" id="replace-source">Replace file</button><button class="button small danger-button" id="remove-source">Remove file</button>';host.append(actions);$('replace-source').onclick=()=>openImport(currentId);$('remove-source').onclick=()=>{current().source=null;if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=null;showGraphTab();toast('Source preview removed. Reconstructed graph retained.');};
 host.hidden=false;$('graph-svg').style.visibility='hidden';$('graph-tab').classList.remove('active');$('source-tab').classList.add('active');
};

function openEditor(tab='node'){
 if(busy)return;
 editorTab=tab;
 if(!selected||selected.kind!=='node')selected={id:graph().nodes[0]?.id,kind:'node'};
 const n=graph().nodes.find(n=>n.id===selected.id)||graph().nodes[0];
 const options=(value)=>graph().nodes.map(n=>`<option value="${esc(n.id)}" ${n.id===value?'selected':''}>${esc(n.id)} · ${esc(n.label.slice(0,30))}</option>`).join('');
 let body='';
 if(tab==='node')body=`<label class="field">Selected node<select id="editor-node">${options(n?.id)}</select></label>${n?`<div class="form-grid"><label class="field">Node ID<input value="${esc(n.id)}" disabled></label><label class="field">Shape / type<select id="node-type">${TYPES.map(t=>`<option ${n.type===t?'selected':''}>${t}</option>`).join('')}</select></label></div><label class="field">Executable label<input id="node-label" maxlength="240" value="${esc(n.label)}"><span class="help">INPUT n · x = x + 1 · x &gt; 0? · OUTPUT "Done" · Max 240 characters</span></label><div class="form-grid"><label class="field">Node tint<input id="node-color" type="color" value="${n.color||'#f4fafc'}"></label><label class="field"><input style="width:auto;display:inline;margin-top:32px" type="checkbox" id="use-node-color" ${n.color?'checked':''}> Use custom tint</label></div><label class="field">Node note<textarea id="node-note" maxlength="2000">${esc(n.note||'')}</textarea></label><label class="field"><input style="width:auto;display:inline" type="checkbox" id="node-reviewed" ${n.confidence>=.8?'checked':''}> I checked this node against the source</label><div class="modal-actions"><button class="button danger-button left" id="delete-node">Delete node</button><button class="button primary" id="save-node">Apply changes</button></div>`:''}`;
 else if(tab==='connections')body=`<p class="modal-copy">Every arrow has a source and a destination. Decision branches need Yes/No labels.</p><table class="edge-table"><thead><tr><th>From</th><th>To</th><th>Branch label</th><th></th></tr></thead><tbody>${graph().edges.map(e=>`<tr data-edge-row="${esc(e.id)}"><td><select data-source>${options(e.source)}</select></td><td><select data-target>${options(e.target)}</select></td><td><input data-label maxlength="100" value="${esc(e.label)}" placeholder="Yes / No"></td><td><button class="icon-button" data-delete-edge="${esc(e.id)}" title="Remove connection" aria-label="Remove connection">${icon('x')}</button></td></tr>`).join('')}</tbody></table><div class="modal-actions"><button class="button left" id="editor-add-edge">+ Add connection</button><button class="button primary" id="save-edges">Apply connections</button></div>`;
 else body=`<p class="modal-copy">Edit the complete graph schema. Node IDs stay attached to trace entries. Changes are normalized and validated before use.</p><label class="field">Graph JSON<textarea id="graph-json" style="height:330px">${esc(JSON.stringify(graph(),null,2))}</textarea></label><div id="json-error" class="error-text" role="alert"></div><div class="modal-actions"><button class="button primary" id="save-json">Apply graph</button></div>`;
 modal('Make the logic explicit.',`<div class="editor-tabs"><button class="button small ${tab==='node'?'active':''}" data-editor-tab="node">Nodes & notes</button><button class="button small ${tab==='connections'?'active':''}" data-editor-tab="connections">Connections</button><button class="button small ${tab==='json'?'active':''}" data-editor-tab="json">Graph JSON</button></div>${body}`,'02 / REVIEW & EDIT');
 $('modal-body').querySelectorAll('[data-editor-tab]').forEach(b=>b.onclick=()=>openEditor(b.dataset.editorTab));
 if(tab==='node'&&n){$('editor-node').onchange=()=>{selected={id:$('editor-node').value,kind:'node'};openEditor('node');};$('save-node').onclick=()=>{pushHistory();n.type=$('node-type').value;n.label=$('node-label').value.trim();n.note=$('node-note').value;n.color=$('use-node-color').checked?$('node-color').value:'';n.confidence=$('node-reviewed').checked?1:.5;invalidate();closeModal();select(n.id,'node');toast('Node updated. Generate code to refresh its trace.');};$('delete-node').onclick=()=>{pushHistory();graph().nodes=graph().nodes.filter(v=>v.id!==n.id);graph().edges=graph().edges.filter(e=>e.source!==n.id&&e.target!==n.id);selected=null;invalidate();closeModal();toast('Node and its attached connections removed.');};}
 if(tab==='connections'){
  const draftEdges=()=>[...$('modal-body').querySelectorAll('[data-edge-row]')].map(row=>({id:row.dataset.edgeRow,source:row.querySelector('[data-source]').value,target:row.querySelector('[data-target]').value,label:row.querySelector('[data-label]').value.trim()}));
  $('modal-body').querySelectorAll('[data-delete-edge]').forEach(b=>b.onclick=()=>b.closest('tr').remove());
  $('save-edges').onclick=()=>{pushHistory();graph().edges=draftEdges();invalidate();closeModal();toast('Connections updated.');};
  $('editor-add-edge').onclick=()=>{const existing=draftEdges(),id=newId('e',existing),row=document.createElement('tr');row.dataset.edgeRow=id;row.innerHTML=`<td><select data-source>${options(graph().nodes[0]?.id)}</select></td><td><select data-target>${options(graph().nodes[1]?.id||graph().nodes[0]?.id)}</select></td><td><input data-label maxlength="80" placeholder="Yes / No"></td><td><button class="icon-button" title="Remove connection" aria-label="Remove connection">${icon('x')}</button></td>`;row.querySelector('button').onclick=()=>row.remove();$('modal-body').querySelector('tbody').append(row);};
 }
 if(tab==='json')$('save-json').onclick=()=>{try{const raw=JSON.parse($('graph-json').value),g=normalize(raw);pushHistory();current().graph=g;selected=null;invalidate();flowView.fit();closeModal();toast('Graph JSON applied. Review validation results.');}catch(e){$('json-error').textContent=e.message;}};
}
$('edit-graph').onclick=()=>openEditor(editorTab);
function openValidation(){
 const v=check(),warnings=[...v.warnings,...(current().recognitionWarnings||[]).map(message=>({message}))];
 modal(v.errors.length?'A few paths need attention.':'Your graph is ready to review.',`<p class="modal-copy">Validation checks connectivity, branch labels, terminal nodes, loop exits, executable labels and variable assignment. Image recognition is best-effort; it does not replace source review.</p>${!v.errors.length?'<div class="issue-item good">✓ No structural or executable-logic errors found.</div>':''}${v.errors.map(e=>`<div class="issue-item">${e.nodeId?`<button data-issue-node="${esc(e.nodeId)}">${esc(e.nodeId)}</button>`:'<strong>FLOW</strong>'}<span>${esc(e.message)}</span></div>`).join('')}${warnings.map(w=>`<div class="issue-item">${w.nodeId?`<button data-issue-node="${esc(w.nodeId)}">${esc(w.nodeId)}</button>`:'<strong>NOTE</strong>'}<span>${esc(w.message)}</span></div>`).join('')}${!current().reviewed?'<div class="notice warning">Before generating, compare every recognized node and arrow against the original file.</div><label class="field"><input type="checkbox" id="confirm-review" style="width:auto;display:inline"> I reviewed labels, node types, arrows, and Yes/No branches.</label>':''}<div class="modal-actions"><button class="button left" id="validation-edit">Edit flow</button><button class="button primary" id="validation-generate" ${v.errors.length?'disabled':''}>${current().reviewed?'Generate code':'Confirm review & generate'}</button></div>`,'GRAPH VALIDATION');
 $('modal-body').querySelectorAll('[data-issue-node]').forEach(b=>b.onclick=()=>{select(b.dataset.issueNode,'node');closeModal();openEditor('node');});$('validation-edit').onclick=()=>openEditor('connections');$('validation-generate').onclick=()=>{if(!current().reviewed&&!$('confirm-review')?.checked){toast('Confirm that you reviewed the reconstructed flow first.',true);return;}current().reviewed=true;for(const n of graph().nodes)n.confidence=1;save();closeModal();generate();};
}
$('validation-button').onclick=openValidation;
async function generate(){
 if(busy)return;const v=check();if(v.errors.length||!current().reviewed){openValidation();return;}
 const snapshot=clone(graph()),requestedLanguage=language(),projectId=currentId,token=++generationToken;
 busy=true;flowView.disabled=true;['generate-button','language','edit-graph','rename-flow','undo','redo'].forEach(id=>$(id).disabled=true);stage(3,'Compiling validated logic…',true);
 try{const generated=await convert(snapshot,requestedLanguage);if(token!==generationToken||currentId!==projectId||language()!==requestedLanguage||JSON.stringify(graph())!==JSON.stringify(snapshot))throw new Error('The flow changed during compilation. Generate again to refresh its source.');result=generated;current().generated=true;save();render();toast('Code generated. Every node is linked to its source lines.');}
 catch(e){result=null;current().generated=false;render();stage(2,'Generation needs attention');const details=e.validation;let messages=[];if(Array.isArray(details))messages=details;else if(details?.errors)messages=details.errors;toast([e.message,...messages.map(m=>typeof m==='string'?m:m.message)].join(' · '),true);}
 finally{busy=false;flowView.disabled=false;['generate-button','language','edit-graph','rename-flow'].forEach(id=>$(id).disabled=false);updateUndo();}
}
$('generate-button').onclick=generate;
$('language').onchange=()=>{if(result)generate();};
$('code-content').setAttribute('tabindex','0');
$('modal-body').addEventListener('keydown',e=>{if(e.key==='Tab'&&e.target.tagName==='TEXTAREA'&&e.target.id==='graph-json'){e.preventDefault();const t=e.target,start=t.selectionStart;t.setRangeText('  ',start,t.selectionEnd,'end');}});
document.querySelectorAll('[data-view]').forEach(el=>el.onclick=()=>{document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b===el));codeView.setView(el.dataset.view);if(selected)codeView.select(selected.id,selected.kind,false);});
$('copy-code').onclick=async()=>{try{await navigator.clipboard.writeText(codeView.text());toast('Copied to clipboard.');}catch{toast('Clipboard unavailable. Use Download instead.',true);}};
$('download-code').onclick=()=>{if(!result)return;const view=codeView.view,ext=view==='trace'?'trace.json':view==='pseudo'?'pseudo.txt':result.language==='python'?'py':'js';download(codeView.text(),`${slug()}.${ext}`,view==='trace'?'application/json':'text/plain');toast('Generated artifact downloaded.');};
function openRun(){
 const v=validate(graph());if(v.errors.length){openValidation();return;}
 const inputs=graph().nodes.map(n=>operation(n)).filter(op=>op.kind==='input');
 modal('Follow a real execution path.',`<p class="modal-copy">Supply values and simulate this graph locally. The interpreter runs supported operations only, with a 10,000-step limit. It never evaluates uploaded source.</p>${inputs.map(op=>`<label class="field">${esc(op.name)} <span class="muted">/ ${esc(op.dataType)}</span><input data-run-input="${esc(op.name)}" data-type="${op.dataType}" value="${op.dataType==='number'?'8':op.dataType==='boolean'?'true':'Hello'}" placeholder="${op.dataType==='boolean'?'true or false':op.dataType}"></label>`).join('')}${!inputs.length?'<div class="notice">This flow needs no external inputs.</div>':''}<button class="button primary" id="simulate-button">${icon('play')} Simulate flow</button><div id="simulation-results"></div>`,'SAFE GRAPH SIMULATION');
 $('simulate-button').onclick=()=>{try{const values={};$('modal-body').querySelectorAll('[data-run-input]').forEach(el=>{let value=el.value;if(el.dataset.type==='boolean'){if(!/^(true|false)$/i.test(value.trim()))throw new Error(`${el.dataset.runInput} must be true or false.`);value=/^true$/i.test(value.trim());}values[el.dataset.runInput]=value;});const r=simulate(graph(),values);$('simulation-results').innerHTML=`<div class="run-result-label">OUTPUT / ${r.steps} STEPS</div><pre class="run-output">${esc(r.output.length?r.output.map(v=>typeof v==='string'?v:JSON.stringify(v)).join('\n'):'(No output)')}</pre><div class="run-result-label">EXECUTION PATH</div><div class="notice">${r.path.slice(0,100).map(id=>`<button class="button small" data-run-node="${esc(id)}">${esc(id)}</button>`).join(' → ')}${r.path.length>100?' … (first 100 shown)':''}</div><div class="run-result-label">FINAL VARIABLES</div><pre class="run-output">${esc(JSON.stringify(r.variables,null,2))}</pre>`;$('simulation-results').querySelectorAll('[data-run-node]').forEach(b=>b.onclick=()=>{select(b.dataset.runNode,'node');closeModal();});}catch(e){$('simulation-results').innerHTML=`<p class="error-text" role="alert">${esc(e.message)}</p>`;}};
}
$('run-flow').onclick=openRun;
function openSettings(){modal('Connect the recognition engine.',`<p class="modal-copy">Structured conversion stays in your browser. Connect the separately hosted Python API to recognize PNG, JPEG and single-page PDF files. Uploads will be sent to this address—not to a built-in cloud service.</p><label class="field">Python API base URL<input type="url" id="api-url" value="${esc(getEndpoint())}" placeholder="https://your-modulo-api.example.com"><span class="help">Leave empty for browser-only conversion. When served by run.py, the same-origin API is detected automatically. Do not put API keys here.</span></label><div class="notice">On the backend, set MODULO_ALLOWED_ORIGINS to your exact GitHub Pages origin (https://username.github.io). Use HTTPS and protect a publicly exposed recognition API with rate limits.</div><div id="api-result" role="status"></div><div class="modal-actions"><button class="button left" id="api-disconnect">Browser-only mode</button><button class="button primary" id="api-test">Save & test connection</button></div>`,'OPTIONAL PYTHON SERVICE');$('api-test').onclick=async()=>{try{setEndpoint($('api-url').value);$('api-result').innerHTML='<span class="busy-spinner"></span> Checking API health…';const ok=await health();$('connection-dot').classList.toggle('on',ok);$('api-result').textContent=ok?'Connected. Image/PDF recognition is available.':'No API connection. Check the URL, HTTPS, CORS and whether the Python server is running.';if(ok)toast('Recognition API connected.');}catch(e){$('api-result').textContent=e.message;}};$('api-disconnect').onclick=()=>{setEndpoint('');$('api-url').value='';$('connection-dot').classList.remove('on');$('api-result').textContent='Browser-only conversion selected. Same-origin run.py recognition remains available.';};}
$('settings-button').onclick=openSettings;
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='i'){e.preventDefault();openImport();}if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'&&!$('modal').open){e.preventDefault();(e.shiftKey?$('redo'):$('undo')).click();}});
// Global drops only import a file; dropping regular text never mutates a flow.
document.addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('Files'))e.preventDefault();});document.addEventListener('drop',e=>{if(!e.dataTransfer.files.length||e.target.closest('#dropzone'))return;e.preventDefault();if(e.dataTransfer.files.length!==1){toast('Attach exactly one flowchart file.',true);return;}importFile(e.dataTransfer.files[0]);});
renderIcons();try{if(current().generated)result=compile(graph(),language());}catch{current().generated=false;}
render(true);save();health().then(ok=>$('connection-dot').classList.toggle('on',ok));

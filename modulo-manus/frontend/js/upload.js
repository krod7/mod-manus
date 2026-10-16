import {normalize,parseMermaid} from './engine.js';
import {analyze} from './api.js';
export const MAX_BYTES=10*1024*1024;
export function checkFile(file){
  if(!file||file.size===0)throw new Error('Choose a non-empty flowchart file.');
  if(file.size>MAX_BYTES)throw new Error('The file is too large. Maximum size: 10 MB.');
  const ext=file.name.split('.').pop().toLowerCase();
  if(!['json','svg','mmd','mermaid','txt','drawio','xml','png','jpg','jpeg','pdf'].includes(ext))throw new Error('Unsupported file. Use JSON, SVG, Mermaid, draw.io, PNG, JPEG or a single-page PDF.');
  return ext;
}
function parseXML(text){const doc=new DOMParser().parseFromString(text,'application/xml');if(doc.querySelector('parsererror'))throw new Error('This XML file could not be read.');return doc;}
function drawio(text){
  const doc=parseXML(text),pages=doc.querySelectorAll('diagram');
  if(pages.length>1)throw new Error('Upload a single-page flowchart. This draw.io file contains multiple pages.');
  if(pages.length===1&&!pages[0].querySelector('mxGraphModel'))throw new Error('Save draw.io as uncompressed XML (File → Export as → XML, uncheck Compressed).');
  const nodes=[],edges=[];
  for(const cell of doc.querySelectorAll('mxCell')) {
    if(cell.getAttribute('vertex')==='1') {
      const raw=cell.getAttribute('value')||'';
      const label=raw.replace(/<[^>]*>/g,' ').replace(/&nbsp;/g,' ').trim();
      const style=cell.getAttribute('style')||'',g=cell.querySelector('mxGeometry');
      const type=/rhombus/.test(style)?'decision':/^start$/i.test(label)?'start':/^(end|stop)$/i.test(label)?'end':/^(INPUT|READ)\s/i.test(label)?'input':/^(OUTPUT|PRINT|DISPLAY)\s/i.test(label)?'output':'process';
      nodes.push({id:`n_${cell.getAttribute('id')}`,label,type,x:Number(g?.getAttribute('x')||0)+Number(g?.getAttribute('width')||150)/2,y:Number(g?.getAttribute('y')||0)+Number(g?.getAttribute('height')||60)/2});
    } else if(cell.getAttribute('edge')==='1')edges.push({id:`e_${cell.getAttribute('id')}`,source:`n_${cell.getAttribute('source')}`,target:`n_${cell.getAttribute('target')}`,label:(cell.getAttribute('value')||'').replace(/<[^>]*>/g,'').trim()});
  }
  if(!nodes.length)throw new Error('No flowchart nodes found in this draw.io file.');
  return normalize({name:'Imported draw.io flow',nodes,edges});
}
export async function intake(file,onStage=()=>{}) {
  const ext=checkFile(file);onStage(1,'Reading your flowchart…');
  if(['png','jpg','jpeg','pdf'].includes(ext)) {
    const data=await analyze(file);const graph=normalize(data.graph);
    return {graph,source:{name:file.name,kind:ext==='pdf'?'pdf':'image',file},warnings:(data.warnings||[]).map(w=>typeof w==='string'?w:w.message),needsReview:true,method:data.recognition?.method||'OCR + computer vision'};
  }
  const text=await file.text(); let graph;
  if(ext==='json'){let data;try{data=JSON.parse(text);}catch{throw new Error('Invalid JSON. Check for missing commas or quotation marks.');}graph=normalize(data.graph||data);}
  else if(['mmd','mermaid','txt'].includes(ext))graph=parseMermaid(text);
  else if(['drawio','xml'].includes(ext))graph=drawio(text);
  else {
    const doc=parseXML(text);const metadata=doc.querySelector('metadata#modulo-graph');
    if(!metadata)throw new Error('This SVG has no Modulo graph metadata. Export an annotated SVG from Modulo, use draw.io XML, or upload a PNG/PDF through the recognition API.');
    try{graph=normalize(JSON.parse(metadata.textContent));}catch(e){throw new Error(`Invalid SVG graph metadata: ${e.message}`);}
  }
  if(!graph.nodes.length)throw new Error('No nodes were found. Attach a flowchart containing a Start and End.');
  graph.name=file.name.replace(/\.[^.]+$/,'').replace(/[_-]/g,' ');
  onStage(2,'Ready for graph review');
  return {graph,source:{name:file.name,kind:'text',text},warnings:[],needsReview:false,method:'Structured graph import'};
}
export function download(content,name,type='text/plain'){
  const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

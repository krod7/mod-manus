import {escapeHTML} from './engine.js';
import {syntax,traceLines,highlightCode} from './highlighter.js';
export class CodeView{
  constructor(host,onSelect){this.host=host;this.onSelect=onSelect;this.view='code';this.result=null;host.addEventListener('click',event=>{const row=event.target.closest('[data-line],[data-node]');if(!row||!this.result)return;if(row.dataset.node){onSelect(row.dataset.node,'node');return;}const line=Number(row.dataset.line),key=this.view==='pseudo'?'pseudoLines':'codeLines';const t=this.result.trace.find(t=>!t.edgeId&&t[key]?.includes(line));if(t)onSelect(t.nodeId,'node',false);});}
  setView(view){this.view=view;this.render();}
  setResult(result){this.result=result;this.render();}
  render(){
    if(!this.result){this.host.innerHTML='<div class="code-empty"><span class="mono">{ }</span><h3>Your next step is visible.</h3><p>Review the reconstructed flow, resolve any issues, then generate your code.</p></div>';document.getElementById('code-stats').textContent='Waiting for generation';return;}
    if(this.view==='trace'){
      this.host.innerHTML=this.result.trace.filter(t=>!t.edgeId).map(t=>{const n=this.result.graph.nodes.find(n=>n.id===t.nodeId);return `<button class="trace-row" data-node="${escapeHTML(t.nodeId)}"><span class="trace-node-id">${escapeHTML(t.nodeId)}</span><span class="trace-node-label">${escapeHTML(n?.label||'')}</span><span class="trace-line-range">L${t.codeLines[0]}–${t.codeLines.at(-1)} ↗</span></button>`;}).join('');
    }else{
      const text=this.view==='pseudo'?this.result.pseudocode:this.result.code;
      this.host.innerHTML=text.split('\n').map((line,i)=>`<div class="code-line" data-line="${i+1}"><span class="line-number">${i+1}</span><span class="line-source">${this.view==='pseudo'?escapeHTML(line):syntax(line,this.result.language)}</span></div>`).join('');
    }
    const count=this.result.code.split('\n').length;
    document.getElementById('code-stats').textContent=`${this.result.language==='python'?'Python':'JavaScript'} · ${count} lines · UTF-8`;
    document.getElementById('trace-count').textContent=this.result.graph.nodes.length;
    document.getElementById('code-filename').textContent=`${this.result.graph.name.toLowerCase().replace(/[^a-z0-9]+/g,'_')}.${this.result.language==='python'?'py':'js'}`;
  }
  select(id,kind='node',scroll=true){
    if(!this.result)return;
    if(this.view==='trace'){this.host.querySelectorAll('[data-node]').forEach(row=>row.classList.toggle('selected',row.dataset.node===id));return;}
    highlightCode(traceLines(this.result.trace,id,kind,this.view),scroll);
  }
  text(){return this.result?(this.view==='pseudo'?this.result.pseudocode:this.view==='trace'?JSON.stringify(this.result.trace,null,2):this.result.code):'';}
}

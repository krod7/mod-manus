import {escapeHTML} from './engine.js';
export function syntax(line,language){
  const pattern=/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|#.*$|\/\/.*$|\b(?:def|return|if|elif|else|for|in|raise|True|False|None|and|or|not|import|function|const|let|switch|case|break|default|throw|new|true|false)\b|\b\d+(?:\.\d+)?\b)/g;
  let last=0,result='';
  for(const m of line.matchAll(pattern)){result+=escapeHTML(line.slice(last,m.index));const token=m[0],type=token.startsWith('#')||token.startsWith('//')?'comment':/^["']/.test(token)?'string':/^\d/.test(token)?'number':'keyword';result+=`<span class="syntax-${type}">${escapeHTML(token)}</span>`;last=m.index+token.length;}
  return result+escapeHTML(line.slice(last));
}
export function traceLines(trace,id,kind='node',view='code'){
  const rows=trace.filter(t=>kind==='edge'?t.edgeId===id:t.nodeId===id&&!t.edgeId);
  return new Set(rows.flatMap(t=>view==='pseudo'?t.pseudoLines:t.codeLines));
}
export function highlightCode(lines,scroll=true){const host=document.getElementById('code-content');let first;host.querySelectorAll('[data-line]').forEach(el=>{const selected=lines.has(Number(el.dataset.line));el.classList.toggle('selected',selected);if(selected&&!first)first=el;});if(scroll&&first){const top=first.offsetTop-host.offsetTop;if(top<host.scrollTop||top>host.scrollTop+host.clientHeight-40)host.scrollTop=Math.max(0,top-40);}}

/* Modulo's static compiler. No eval, Function constructor or source execution. */
export const TYPES = ['start', 'input', 'process', 'decision', 'output', 'end'];
const ID = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
const forbidden = new Set(['__proto__','prototype','constructor','eval','function','window','globalthis','import','exec','open','globals','locals','require','process','global','this','class','lambda','new','delete','getattr','setattr','compile','input','builtins']);
const unsafe = name => forbidden.has(name.toLowerCase()) || name.includes('__');
export const clone = value => JSON.parse(JSON.stringify(value));
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function expression(source) {
  const text = String(source).trim().replace(/\?$/, '');
  const tokens = [];
  let i = 0;
  while (i < text.length) {
    if (/\s/.test(text[i])) { i++; continue; }
    const rest = text.slice(i);
    const m = rest.match(/^(?:\d+(?:\.\d+)?|(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|[A-Za-z_][A-Za-z0-9_]*|===|!==|==|!=|>=|<=|&&|\|\||[+\-*/%><!()])/);
    if (!m) throw new Error(`Unsupported expression near “${rest.slice(0, 20)}”. Use literals, variables, arithmetic and comparisons.`);
    tokens.push(m[0]); i += m[0].length;
    if (tokens.length > 256) throw new Error('Expression is too long.');
  }
  let cursor = 0;
  const precedence = {or:1,'||':1,and:2,'&&':2,'==':3,'===':3,'!=':3,'!==':3,'>':4,'<':4,'>=':4,'<=':4,'+':5,'-':5,'*':6,'/':6,'%':6};
  function primary(depth) {
    if (depth > 40) throw new Error('Expression nesting exceeds 40 levels.');
    const token = tokens[cursor++];
    if (!token) throw new Error('Expected an expression.');
    if (['-', '+', '!', 'not'].includes(token)) return {kind:'unary', op:token, child:primary(depth + 1)};
    if (token === '(') { const result = binary(1, depth + 1); if (tokens[cursor++] !== ')') throw new Error('Unclosed parentheses.'); return result; }
    if (/^\d/.test(token)) return {kind:'literal', value:Number(token)};
    if (/^["']/.test(token)) {
      let value;
      try { value = token[0] === '"' ? JSON.parse(token) : token.slice(1,-1).replace(/\\'/g,"'").replace(/\\n/g,'\n').replace(/\\\\/g,'\\'); }
      catch { throw new Error('Invalid string literal.'); }
      return {kind:'literal',value};
    }
    if (['true','True','false','False'].includes(token)) return {kind:'literal',value:/^true$/i.test(token)};
    if (NAME.test(token) && !unsafe(token) && !['and','or','not'].includes(token)) return {kind:'name',value:token};
    throw new Error(`Unsupported token “${token}”.`);
  }
  function binary(min, depth) {
    let left = primary(depth);
    while (precedence[tokens[cursor]] >= min) {
      const op = tokens[cursor++]; const right = binary(precedence[op] + 1, depth + 1);
      const comparison=v=>v?.kind==='binary'&&['==','===','!=','!==','>','<','>=','<='].includes(v.op);
      if(['==','===','!=','!==','>','<','>=','<='].includes(op)&&(comparison(left)||comparison(right)))throw new Error('Use separate comparisons joined by and/or instead of chained comparisons.');
      left = {kind:'binary', op, left, right};
    }
    return left;
  }
  const tree = binary(1,0);
  if (cursor !== tokens.length) throw new Error(`Unexpected token “${tokens[cursor]}”. Calls and member access are not supported.`);
  return tree;
}
function names(tree) {
  if (tree.kind === 'name') return [tree.value];
  if (tree.kind === 'unary') return names(tree.child);
  return tree.kind === 'binary' ? [...names(tree.left), ...names(tree.right)] : [];
}
function emit(tree, language) {
  if (tree.kind === 'name') return `env[${JSON.stringify(tree.value)}]`;
  if (tree.kind === 'literal') return typeof tree.value === 'boolean' && language === 'python' ? (tree.value ? 'True' : 'False') : JSON.stringify(tree.value);
  if (tree.kind === 'unary') { const op = ['not','!'].includes(tree.op) ? (language === 'python' ? 'not ' : '!') : tree.op; return `(${op}${emit(tree.child, language)})`; }
  const ops = language === 'python' ? {'&&':'and','||':'or','===':'==','!==':'!='} : {and:'&&',or:'||','==':'===','!=':'!=='};
  if(language==='javascript'&&['%','/'].includes(tree.op))return `${tree.op==='%'?'modulo':'divide'}(${emit(tree.left,language)}, ${emit(tree.right,language)})`;
  return `(${emit(tree.left,language)} ${ops[tree.op] || tree.op} ${emit(tree.right,language)})`;
}
function evaluate(tree, env) {
  if (tree.kind === 'literal') return tree.value;
  if (tree.kind === 'name') { if (!Object.hasOwn(env,tree.value)) throw new Error(`Variable “${tree.value}” is not defined. Add an INPUT or assignment first.`); return env[tree.value]; }
  if (tree.kind === 'unary') { const v = evaluate(tree.child,env); return ['!','not'].includes(tree.op) ? !v : tree.op === '-' ? -Number(v) : Number(v); }
  const a = evaluate(tree.left,env);
  if (['and','&&'].includes(tree.op)) return a && evaluate(tree.right,env);
  if (['or','||'].includes(tree.op)) return a || evaluate(tree.right,env);
  const b = evaluate(tree.right,env);
  switch (tree.op) {
    case '+': if (typeof a !== typeof b || !['string','number'].includes(typeof a)) throw new Error('Addition requires two numbers or two strings.'); return a+b;
    case '-': return a-b; case '*': return a*b;
    case '/': if (b === 0) throw new Error('Division by zero.'); return a/b;
    case '%': if (b === 0) throw new Error('Modulo by zero.'); return ((a%b)+b)%b;
    case '==': case '===': return a===b; case '!=': case '!==': return a!==b;
    case '>': return a>b; case '<': return a<b; case '>=': return a>=b; case '<=': return a<=b;
    default: throw new Error('Unknown operator.');
  }
}
export function operation(node) {
  const label = String(node.label || '').trim();
  if (['start','end'].includes(node.type)) return {kind:node.type};
  if (node.type === 'input') {
    const m = label.match(/^(?:INPUT|READ)\s+([A-Za-z_][A-Za-z0-9_]{0,63})(?:\s*:\s*(number|string|text|boolean))?$/i);
    if (!m || unsafe(m[1])) throw new Error('Use INPUT variable or INPUT variable: number/string/boolean.');
    return {kind:'input', name:m[1], dataType:(m[2] || 'number').toLowerCase()==='text'?'string':(m[2]||'number').toLowerCase()};
  }
  if (node.type === 'output') return {kind:'output',tree:expression(label.replace(/^(?:OUTPUT|PRINT|DISPLAY)\s+/i,''))};
  if (node.type === 'decision') return {kind:'decision',tree:expression(label)};
  const m = label.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?!=)(.+)$/);
  if (!m || unsafe(m[1]) || m[1].length>64) throw new Error('Process labels must be explicit assignments, for example total = total + 1. Named business operations need an implementation.');
  return {kind:'process',name:m[1],tree:expression(m[2])};
}
export function normalize(raw) {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.nodes) || !Array.isArray(raw.edges)) throw new Error('A flowchart needs nodes and edges arrays.');
  if (raw.nodes.length > 100 || raw.edges.length > 300) throw new Error('Use at most 100 nodes and 300 connections.');
  if(raw.nodes.some(n=>!n||typeof n!=='object')||raw.edges.some(e=>!e||typeof e!=='object'))throw new Error('Every node and connection must be an object.');
  return {
    name:String(raw.name || 'Untitled flow').slice(0,100),
    nodes:raw.nodes.map((n,i) => ({id:String(n.id || ''),type:n.type==='input_output'?/^(INPUT|READ)\s/i.test(n.label||'')?'input':/^(OUTPUT|PRINT|DISPLAY)\s/i.test(n.label||'')?'output':'process':String(n.type || 'process'),label:String(n.label || ''),x:Number.isFinite(Number(n.x)) ? Math.max(-5000,Math.min(5000,Number(n.x))) : 280,y:Number.isFinite(Number(n.y)) ? Math.max(-5000,Math.min(5000,Number(n.y))) : 60+i*110,confidence:Number.isFinite(Number(n.confidence)) ? Math.max(0,Math.min(1,Number(n.confidence))) : 1,note:String(n.note || '').slice(0,2000),color:/^#[0-9a-f]{6}$/i.test(n.color || '') ? n.color : ''})),
    edges:raw.edges.map((e,i) => ({id:String(e.id || `e${i+1}`),source:String(e.source || ''),target:String(e.target || ''),label:String(e.label || '')}))
  };
}
const isYes = e => /^(yes|true)$/i.test(e.label.trim());
const isNo = e => /^(no|false)$/i.test(e.label.trim());
export function validate(graph) {
  const errors = [], warnings = []; const add = (nodeId,message) => errors.push({nodeId,message});
  if(graph.nodes.length>100)add(null,'Use at most 100 nodes.');
  if(graph.edges.length>300)add(null,'Use at most 300 connections.');
  const ids = new Set(); const edgeIds = new Set(); const out = new Map(graph.nodes.map(n => [n.id,[]]));
  for (const n of graph.nodes) {
    if (!ID.test(n.id) || ids.has(n.id)) add(n.id,'Node IDs must be unique identifiers (letters, digits, _ or -).');
    ids.add(n.id);
    if (!TYPES.includes(n.type)) add(n.id,'Choose a supported node type.');
    if (!n.label.trim()) add(n.id,'Add a readable label.');
    if(n.label.length>240)add(n.id,'Node labels are limited to 240 characters.');
    try { operation(n); } catch (e) { add(n.id,e.message); }
    if (n.confidence < .8) warnings.push({nodeId:n.id,message:'Recognition is uncertain. Review this node against the source.'});
  }
  for (const e of graph.edges) {
    if (!ID.test(e.id) || edgeIds.has(e.id)) add(e.source,'Connection IDs must be unique identifiers.');
    edgeIds.add(e.id);
    if(e.label.length>80)add(e.source,'Connection labels are limited to 80 characters.');
    if (!ids.has(e.source) || !ids.has(e.target)) add(e.source,'A connection points to a missing node.');
    else out.get(e.source).push(e);
  }
  const starts = graph.nodes.filter(n=>n.type==='start');
  if (starts.length !== 1) add(null,'The flow must have exactly one Start node.');
  if (!graph.nodes.some(n=>n.type==='end')) add(null,'Add at least one End node.');
  for (const n of graph.nodes) {
    const edges = out.get(n.id) || [];
    if (n.type === 'end' && edges.length) add(n.id,'End nodes cannot have outgoing connections.');
    else if (n.type === 'decision') {
      if (edges.length !== 2 || edges.filter(isYes).length !== 1 || edges.filter(isNo).length !== 1) add(n.id,'A decision needs exactly two connections labeled Yes/No or True/False.');
    } else if (n.type !== 'end' && edges.length !== 1) add(n.id,'This node needs exactly one outgoing connection.');
  }
  if (starts.length === 1) {
    const visited = new Set(), active = new Set(); let cycle = false;
    function visit(id) { if (active.has(id)) {cycle=true;return;} if (visited.has(id)) return; visited.add(id); active.add(id); for(const e of out.get(id)||[]) visit(e.target); active.delete(id); }
    visit(starts[0].id);
    for (const n of graph.nodes) if (!visited.has(n.id)) add(n.id,'This node is disconnected or unreachable from Start.');
    if (cycle) warnings.push({nodeId:null,message:'Loop detected. Generated code and simulation enforce a 10,000-step limit.'});
    const canEnd = new Set(graph.nodes.filter(n=>n.type==='end').map(n=>n.id));
    let changed = true; while(changed) { changed=false; for(const e of graph.edges) if(canEnd.has(e.target)&&!canEnd.has(e.source)){canEnd.add(e.source);changed=true;} }
    for(const n of graph.nodes) if(visited.has(n.id)&&!canEnd.has(n.id)) add(n.id,'No path from this node reaches an End.');
  }
  // Definite assignment across all incoming paths (including back edges).
  if (!errors.length) {
    const allNames = new Set(graph.nodes.flatMap(n=>{const op=operation(n);return op.name?[op.name]:[];}));
    const incoming = new Map(graph.nodes.map(n=>[n.id,graph.edges.filter(e=>e.target===n.id).map(e=>e.source)]));
    const before = new Map(graph.nodes.map(n=>[n.id,new Set(n.type==='start'?[]:allNames)]));
    const after = new Map(graph.nodes.map(n=>[n.id,new Set(n.type==='start'?[]:allNames)]));
    for(let pass=0;pass<graph.nodes.length*3;pass++) {
      let change=false;
      for(const n of graph.nodes) {
        const parents = incoming.get(n.id); const b = n.type==='start'||!parents.length ? new Set() : new Set([...after.get(parents[0])].filter(v=>parents.every(id=>after.get(id).has(v))));
        const a = new Set(b); const op=operation(n); if(op.name) a.add(op.name);
        if([...a].sort().join()!==[...after.get(n.id)].sort().join()) change=true;
        before.set(n.id,b);after.set(n.id,a);
      }
      if(!change) break;
    }
    for(const n of graph.nodes) { const op=operation(n); if(op.tree) for(const name of new Set(names(op.tree))) if(!before.get(n.id).has(name)) add(n.id,`Variable “${name}” is not assigned on every incoming path.`); }
  }
  return {errors,warnings};
}
export function compile(raw, language='python') {
  if (!['python','javascript'].includes(language)) throw new Error('Choose Python or JavaScript.');
  const graph=normalize(raw), validation=validate(graph);
  if(validation.errors.length) {const e=new Error(validation.errors[0].message); e.validation=validation;throw e;}
  const py=language==='python'; const code=[], pseudo=[],trace=[];
  const line=s=>code.push(s), ps=s=>pseudo.push(s);
  const start=graph.nodes.find(n=>n.type==='start').id;
  if(py) {
    line('# Generated by Modulo · graph state machine');
    line('import math');
    line('def run(inputs=None, max_steps=10000):');line('    inputs = inputs or {}');line('    env, output = {}, []');line(`    state = ${JSON.stringify(start)}`);line('    for _step in range(max_steps):');
  } else {
    line('// Generated by Modulo · graph state machine');
    line("function divide(a, b) { if (b === 0) throw new Error('Division by zero'); return a / b; }");
    line("function modulo(a, b) { if (b === 0) throw new Error('Modulo by zero'); return ((a % b) + b) % b; }");
    line('function run(inputs = {}, maxSteps = 10000) {');line('  const env = Object.create(null), output = [];');line(`  let state = ${JSON.stringify(start)};`);line('  for (let step = 0; step < maxSteps; step++) {');line('    switch (state) {');
  }
  ps(`FLOW ${graph.name}`); ps(`STATE ← ${start}`); ps('REPEAT (at most 10,000 steps)');
  for(let i=0;i<graph.nodes.length;i++) {
    const n=graph.nodes[i],op=operation(n),edges=graph.edges.filter(e=>e.source===n.id);
    const begin=code.length+1,pbegin=pseudo.length+1, indent=py?'            ':'        ';
    line(py?`        ${i===0?'if':'elif'} state == ${JSON.stringify(n.id)}:  # ${n.id}`:`      case ${JSON.stringify(n.id)}: { // ${n.id}`);
    ps(`  ${n.id} [${n.type.toUpperCase()}] ${n.label}`);
    if(op.kind==='input') {
      const key=JSON.stringify(op.name), type=op.dataType;
      if(py) {
        line(`${indent}if ${key} not in inputs: raise ValueError('Missing input: ${op.name}')`);
        if(type==='number') {line(`${indent}env[${key}] = float(inputs[${key}])`);line(`${indent}if not math.isfinite(env[${key}]): raise ValueError('Input must be finite')`);}
        else if(type==='boolean') {line(`${indent}if not isinstance(inputs[${key}], bool): raise ValueError('Input must be boolean')`);line(`${indent}env[${key}] = inputs[${key}]`);}
        else line(`${indent}env[${key}] = str(inputs[${key}])`);
      } else {
        line(`${indent}if (!Object.hasOwn(inputs, ${key})) throw new Error('Missing input: ${op.name}');`);
        line(`${indent}env[${key}] = ${type==='number'?`Number(inputs[${key}])`:type==='string'?`String(inputs[${key}])`:`inputs[${key}]`};`);
        if(type==='number') line(`${indent}if (!Number.isFinite(env[${key}]) || String(inputs[${key}]).trim() === '') throw new Error('Input must be a finite number');`);
        if(type==='boolean') line(`${indent}if (typeof env[${key}] !== 'boolean') throw new Error('Input must be boolean');`);
      }
    } else if(op.kind==='process') line(`${indent}env[${JSON.stringify(op.name)}] = ${emit(op.tree,language)}${py?'':';'}`);
    else if(op.kind==='output') line(`${indent}output.${py?'append':'push'}(${emit(op.tree,language)})${py?'':';'}`);
    if(op.kind==='end') {line(`${indent}return output${py?'':';'}`);ps('    RETURN output');}
    else if(op.kind==='decision') {
      const yes=edges.find(isYes), no=edges.find(isNo), cond=emit(op.tree,language);
      line(`${indent}state = ${py?`${JSON.stringify(yes.target)} if ${cond} else ${JSON.stringify(no.target)}`:`${cond} ? ${JSON.stringify(yes.target)} : ${JSON.stringify(no.target)};`}`);
      ps(`    IF ${n.label.replace(/\?$/,'')} → ${yes.target} ELSE → ${no.target}`);
    } else {line(`${indent}state = ${JSON.stringify(edges[0].target)}${py?'':';'}`);ps(`    NEXT → ${edges[0].target}`);}
    if(!py) {if(op.kind!=='end')line('        break;');line('      }');}
    trace.push({nodeId:n.id,codeLines:Array.from({length:code.length-begin+1},(_,j)=>begin+j),pseudoLines:Array.from({length:pseudo.length-pbegin+1},(_,j)=>pbegin+j)});
    for(const e of edges) trace.push({edgeId:e.id,nodeId:n.id,codeLines:[code.length-(py?0:op.kind==='end'?1:2)],pseudoLines:[pseudo.length]});
  }
  if(py) {line('        else:');line("            raise RuntimeError('Unknown flow state')");line("    raise RuntimeError('Step limit reached; check loop termination')");}
  else {line("      default: throw new Error('Unknown flow state');");line('    }');line('  }');line("  throw new Error('Step limit reached; check loop termination');");line('}');}
  return {graph,language,code:code.join('\n'),pseudocode:pseudo.join('\n'),trace,validation};
}
export function simulate(raw, inputs={}, maxSteps=10000) {
  const graph=normalize(raw),check=validate(graph); if(check.errors.length)throw new Error(check.errors[0].message);
  const env=Object.create(null),output=[],path=[],usedEdges=[];
  let state=graph.nodes.find(n=>n.type==='start').id;
  for(let step=0;step<maxSteps;step++) {
    const n=graph.nodes.find(n=>n.id===state),op=operation(n);path.push(n.id);
    if(op.kind==='end')return {output,path,edges:usedEdges,variables:{...env},steps:step+1};
    if(op.kind==='input') {
      if(!Object.hasOwn(inputs,op.name))throw new Error(`Missing input: ${op.name}`);
      const value=inputs[op.name];
      if(op.dataType==='number') {if(String(value).trim()===''||!Number.isFinite(Number(value)))throw new Error(`${op.name} must be a finite number.`);env[op.name]=Number(value);}
      else if(op.dataType==='boolean') {if(typeof value!=='boolean')throw new Error(`${op.name} must be boolean.`);env[op.name]=value;}
      else env[op.name]=String(value);
    } else if(op.kind==='process')env[op.name]=evaluate(op.tree,env);
    else if(op.kind==='output')output.push(evaluate(op.tree,env));
    const outgoing=graph.edges.filter(e=>e.source===state);
    const e=op.kind==='decision'?outgoing.find(e=>evaluate(op.tree,env)?isYes(e):isNo(e)):outgoing[0];
    usedEdges.push(e.id);state=e.target;
  }
  throw new Error(`Step limit (${maxSteps}) reached. Check your loop's exit condition.`);
}
export function parseMermaid(text) {
  const nodes=new Map(),edges=[];
  const nodePattern=/^([A-Za-z_][\w-]*)(?:\(\((.*?)\)\)|\{(.*?)\}|\[\/(.*?)\/\]|\[(.*?)\]|\((.*?)\))?$/;
  function node(token) {
    const m=token.trim().replace(/\(\[([^\]]*)\]\)$/,'($1)').match(nodePattern); if(!m)throw new Error(`Unsupported Mermaid node: ${token}. Use the documented subset.`);
    const label=(m.slice(2).find(v=>v!==undefined)||m[1]).replace(/^"(.*)"$/,'$1');
    const type=m[3]!==undefined?'decision':/^start$/i.test(label)?'start':/^(end|stop)$/i.test(label)?'end':/^(INPUT|READ)\s/i.test(label)?'input':/^(OUTPUT|PRINT|DISPLAY)\s/i.test(label)?'output':'process';
    if(!nodes.has(m[1])||m.slice(2).some(v=>v!==undefined))nodes.set(m[1],{id:m[1],type,label,x:280,y:60+nodes.size*110});
    return m[1];
  }
  for(const raw of text.split(/[\n;]/)) {
    const s=raw.trim();if(!s||s.startsWith('%%')||/^(flowchart|graph)\s+(TD|TB|LR|RL|BT)$/i.test(s))continue;
    const m=s.match(/^(.*?)\s*-->\s*(?:\|([^|]*)\|\s*)?(.*?)$/);
    if(m)edges.push({id:`e${edges.length+1}`,source:node(m[1]),target:node(m[3]),label:m[2]||''});else node(s);
  }
  return normalize({name:'Imported Mermaid flow',nodes:[...nodes.values()],edges});
}

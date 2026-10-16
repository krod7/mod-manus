import {escapeHTML} from './engine.js';
const SVG='http://www.w3.org/2000/svg';
function dimensions(node){return {w:node.type==='decision'?172:node.type==='start'||node.type==='end'?106:Math.min(300,Math.max(176,node.label.length*5.6+30)),h:node.type==='decision'?94:48};}
function shape(n){const {w,h}=dimensions(n),x=-w/2,y=-h/2;if(n.type==='decision')return `<polygon class="node-shape" points="0,${y} ${w/2},0 0,${h/2} ${x},0"/>`;if(['input','output'].includes(n.type))return `<polygon class="node-shape" points="${x+14},${y} ${w/2+14},${y} ${w/2-14},${h/2} ${x-14},${h/2}"/>`;return `<rect class="node-shape" x="${x}" y="${y}" width="${w}" height="${h}" rx="${['start','end'].includes(n.type)?24:4}"/>`;}
function route(a,b,index){
  const da=dimensions(a),db=dimensions(b);
  if(b.y>a.y+30){
    const x1=a.x,y1=a.y+da.h/2,x2=b.x,y2=b.y-db.h/2;
    if(Math.abs(x2-x1)<2)return {d:`M${x1} ${y1}V${y2}`,lx:x1+11,ly:(y1+y2)/2};
    const mid=y1+(y2-y1)*.48;
    return {d:`M${x1} ${y1}V${mid}Q${x1} ${mid+5} ${x1+(x2>x1?5:-5)} ${mid+5}H${x2-(x2>x1?5:-5)}Q${x2} ${mid+5} ${x2} ${mid+10}V${y2}`,lx:(x1+x2)/2,ly:mid-7};
  }
  const side=b.x>a.x?1:-1,x1=a.x+side*da.w/2,x2=b.x+side*db.w/2,outer=side>0?Math.max(x1,x2)+70+index*5:Math.min(x1,x2)-70-index*5;
  return {d:`M${x1} ${a.y}H${outer}V${b.y}H${x2}`,lx:outer+side*10,ly:(a.y+b.y)/2};
}
export class FlowchartView{
  constructor(svg,{onSelect,onMove,onConnect}){
    this.svg=svg;this.onSelect=onSelect;this.onMove=onMove;this.onConnect=onConnect;this.graph={nodes:[],edges:[]};this.box={x:0,y:0,w:660,h:600};this.base={...this.box};this.mode='select';this.connectStart=null;this.drag=null;
    svg.addEventListener('click',event=>{const node=event.target.closest('[data-node]'),edge=event.target.closest('[data-edge]');if(this.moved||this.disabled)return;
      if(node){if(this.mode==='connect'){if(!this.connectStart){this.connectStart=node.dataset.node;onSelect(this.connectStart,'node');}else{const source=this.connectStart;this.connectStart=null;onConnect(source,node.dataset.node);}}else onSelect(node.dataset.node,'node');}
      else if(edge)onSelect(edge.dataset.edge,'edge');
    });
    svg.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){const n=event.target.closest('[data-node]'),e=event.target.closest('[data-edge]');if(n||e){event.preventDefault();onSelect(n?n.dataset.node:e.dataset.edge,n?'node':'edge');}}});
    svg.addEventListener('pointerdown',event=>{if(this.disabled||event.button!==0||this.mode==='connect')return;const edge=event.target.closest('[data-edge]');if(edge){onSelect(edge.dataset.edge,'edge');return;}const node=event.target.closest('[data-node]'),p=this.point(event);this.moved=false;this.drag={id:node?.dataset.node,x:p.x,y:p.y,box:{...this.box},original:node?{...this.graph.nodes.find(n=>n.id===node.dataset.node)}:null};if(node){onSelect(node.dataset.node,'node',false);onMove(node.dataset.node,0,0,'start');}svg.setPointerCapture(event.pointerId);});
    svg.addEventListener('pointermove',event=>{if(!this.drag)return;const p=this.point(event),dx=p.x-this.drag.x,dy=p.y-this.drag.y;if(Math.abs(dx)+Math.abs(dy)>2)this.moved=true;
      if(this.drag.id&&this.moved){const n=this.graph.nodes.find(n=>n.id===this.drag.id);n.x=Math.round(this.drag.original.x+dx);n.y=Math.round(this.drag.original.y+dy);this.render();}
      else if(!this.drag.id&&this.moved){this.box.x-=dx;this.box.y-=dy;this.applyBox();}
    });
    const up=()=>{if(!this.drag)return;if(this.drag.id&&this.moved){const n=this.graph.nodes.find(n=>n.id===this.drag.id);onMove(n.id,n.x,n.y,'end');}this.drag=null;setTimeout(()=>{this.moved=false;},0);};
    svg.addEventListener('pointerup',up);svg.addEventListener('pointercancel',up);
    svg.addEventListener('wheel',event=>{if(!event.ctrlKey&&!event.metaKey)return;event.preventDefault();this.zoom(event.deltaY>0?.9:1.1);},{passive:false});
  }
  point(event){const p=this.svg.createSVGPoint();p.x=event.clientX;p.y=event.clientY;const matrix=this.svg.getScreenCTM();return matrix?p.matrixTransform(matrix.inverse()):{x:0,y:0};}
  applyBox(){this.svg.setAttribute('viewBox',`${this.box.x} ${this.box.y} ${this.box.w} ${this.box.h}`);document.getElementById('zoom-label').textContent=`${Math.round(this.base.w/this.box.w*100)}%`;}
  setGraph(graph,fit=false){this.graph=graph;this.render();if(fit)this.fit();}
  setMode(mode){this.mode=mode;this.connectStart=null;this.svg.style.cursor=mode==='connect'?'crosshair':'';}
  fit(){
    if(!this.graph.nodes.length){this.box={x:0,y:0,w:660,h:600};}
    else{const minX=Math.min(...this.graph.nodes.map(n=>n.x-dimensions(n).w/2))-65,maxX=Math.max(...this.graph.nodes.map(n=>n.x+dimensions(n).w/2))+65,minY=Math.min(...this.graph.nodes.map(n=>n.y-dimensions(n).h/2))-55,maxY=Math.max(...this.graph.nodes.map(n=>n.y+dimensions(n).h/2))+65;this.box={x:minX,y:minY,w:Math.max(400,maxX-minX),h:Math.max(420,maxY-minY)};}
    this.base={...this.box};this.applyBox();
  }
  zoom(factor){const width=Math.max(this.base.w*.25,Math.min(this.base.w*3,this.box.w/factor)),height=this.box.h*(width/this.box.w);this.box={x:this.box.x+(this.box.w-width)/2,y:this.box.y+(this.box.h-height)/2,w:width,h:height};this.applyBox();}
  render(){
    this.svg.innerHTML='<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8caabb"/></marker><marker id="arrow-selected" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#11af9e"/></marker></defs>';
    if(!this.graph.nodes.length)this.svg.innerHTML+='<text class="empty-canvas" x="330" y="300" text-anchor="middle">Import a flowchart to begin.</text>';
    const edges=this.graph.edges.map((e,i)=>{const a=this.graph.nodes.find(n=>n.id===e.source),b=this.graph.nodes.find(n=>n.id===e.target);if(!a||!b)return '';const r=route(a,b,i);return `<g class="edge" data-edge="${escapeHTML(e.id)}" tabindex="0" role="button" aria-label="Connection ${escapeHTML(e.source)} to ${escapeHTML(e.target)}, ${escapeHTML(e.label||'next')}"><path class="edge-hit" d="${r.d}"/><path class="edge-line" d="${r.d}" marker-end="url(#arrow)"/><text class="edge-label" x="${r.lx}" y="${r.ly}" text-anchor="middle">${escapeHTML(e.label)}</text></g>`;}).join('');
    const nodes=this.graph.nodes.map(n=>`<g class="node ${escapeHTML(n.type)} ${this.issues?.has(n.id)?'issue':''}" data-node="${escapeHTML(n.id)}" transform="translate(${n.x},${n.y})" tabindex="0" role="button" aria-label="${escapeHTML(n.type)}: ${escapeHTML(n.label)}">${shape(n)}<text class="node-label" y="4" text-anchor="middle" ${n.label.length>45?'font-size="9"':''}>${escapeHTML(n.label.length>51?n.label.slice(0,49)+'…':n.label)}</text><text class="node-id" y="${dimensions(n).h/2+15}" text-anchor="middle">${escapeHTML(n.id.toUpperCase())}</text></g>`).join('');
    this.svg.innerHTML+=edges+nodes;
    for(const element of this.svg.querySelectorAll('[data-node]')){const n=this.graph.nodes.find(n=>n.id===element.dataset.node);if(n?.color)element.querySelector('.node-shape').style.fill=n.color;}
    this.select(this.selected?.id,this.selected?.kind);this.applyBox();
  }
  select(id,kind='node') {this.selected={id,kind};this.svg.querySelectorAll('.node').forEach(n=>n.classList.toggle('selected',kind==='node'&&n.dataset.node===id));this.svg.querySelectorAll('.edge').forEach(e=>{const selected=kind==='edge'&&e.dataset.edge===id;e.classList.toggle('selected',selected);e.querySelector('.edge-line')?.setAttribute('marker-end',selected?'url(#arrow-selected)':'url(#arrow)');});}
  setIssues(validation){this.issues=new Set([...(validation.errors||[]),...(validation.warnings||[])].map(v=>v.nodeId));this.render();}
  exportSVG(){
    const svg=this.svg.cloneNode(true);svg.setAttribute('xmlns',SVG);svg.setAttribute('width','900');svg.setAttribute('height','800');svg.setAttribute('viewBox',`${this.base.x} ${this.base.y} ${this.base.w} ${this.base.h}`);
    const style=document.createElementNS(SVG,'style');style.textContent='.node-shape{fill:#f4fafc;stroke:#588099;stroke-width:1.3}.node-label{font:11px monospace;fill:#123b5d}.node-id{font:7px monospace;fill:#7899ad}.edge-line{stroke:#8caabb;stroke-width:1.3;fill:none}.edge-hit{display:none}.edge-label{font:9px monospace;fill:#587f94}';svg.insertBefore(style,svg.firstChild);
    const meta=document.createElementNS(SVG,'metadata');meta.id='modulo-graph';meta.textContent=JSON.stringify(this.graph);svg.insertBefore(meta,svg.firstChild);
    return new XMLSerializer().serializeToString(svg);
  }
}

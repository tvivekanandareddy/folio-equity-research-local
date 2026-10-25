// Keep the approved horizontal diagram fully visible in the main page.
function fitEmbeddedDiagram(){
  if(document.body.classList.contains('architecture-expanded'))return;
  const frame=document.querySelector('.architecture-scroll'),board=document.querySelector('.reference-diagram');
  if(!frame||!board||!frame.clientWidth)return;
  const scale=Math.min(1,frame.clientWidth/1060);
  board.style.width='1060px';board.style.transform='scale('+scale+')';
  const height=board.offsetHeight*scale+'px';if(frame.style.height!==height)frame.style.height=height;
}
// Reference layout: straight ingestion/query tracks with explicit storage branches.
function drawArchitectureConnections(){
  fitEmbeddedDiagram();
  const board=document.querySelector('.reference-diagram');if(!board)return;
  const bounds=board.getBoundingClientRect();if(!bounds.width||!bounds.height)return;
  const ns='http://www.w3.org/2000/svg';
  board.querySelectorAll('.flow-connections').forEach(e=>e.remove());
  let svg=board.querySelector('.architecture-connectors');
  if(!svg){svg=document.createElementNS(ns,'svg');svg.classList.add('architecture-connectors');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');board.prepend(svg);}
  const origin=svg.getBoundingClientRect();svg.setAttribute('viewBox',`0 0 ${origin.width} ${origin.height}`);svg.replaceChildren();
  const defs=document.createElementNS(ns,'defs');const marker=document.createElementNS(ns,'marker');
  for(const [key,value] of Object.entries({id:'reference-arrow',viewBox:'0 0 8 8',refX:'8',refY:'4',markerWidth:'8',markerHeight:'8',orient:'auto',markerUnits:'userSpaceOnUse'}))marker.setAttribute(key,value);
  const head=document.createElementNS(ns,'path');head.setAttribute('d','M 0 0 L 8 4 L 0 8');head.setAttribute('fill','none');head.setAttribute('stroke','#65775a');head.setAttribute('stroke-width','1.3');marker.append(head);defs.append(marker);svg.append(defs);
  const point=el=>{const r=el.getBoundingClientRect();return {left:r.left-origin.left,right:r.right-origin.left,top:r.top-origin.top,bottom:r.bottom-origin.top,cx:r.left-origin.left+r.width/2,cy:r.top-origin.top+r.height/2};};
  const line=path=>{const el=document.createElementNS(ns,'path');el.setAttribute('d',path);el.setAttribute('fill','none');el.setAttribute('stroke','#65775a');el.setAttribute('stroke-width','1.3');el.setAttribute('stroke-linejoin','round');el.setAttribute('marker-end','url(#reference-arrow)');svg.append(el);};
  board.querySelectorAll('.flow-row').forEach(row=>{const nodes=[...row.querySelectorAll(':scope > .node')].map(point);for(let i=0;i<nodes.length-1;i++)line(`M ${nodes[i].right} ${nodes[i].cy} L ${nodes[i+1].left} ${nodes[i+1].cy}`);});
  const files=point(board.querySelector('.storage-note.files')),metadata=point(board.querySelector('.storage-note.metadata'));
  const reports=point(board.querySelector('#ingest-reports')),extract=point(board.querySelector('#ingest-extract'));
  line(`M ${reports.cx} ${reports.bottom} L ${reports.cx} ${files.cy} L ${files.left-10} ${files.cy}`);
  const mid=extract.bottom+20;
  line(`M ${extract.cx} ${extract.bottom} L ${extract.cx} ${mid} L ${metadata.left-30} ${mid} L ${metadata.left-30} ${metadata.cy} L ${metadata.left-10} ${metadata.cy}`);
}
let arrowFrame;function scheduleArchitectureConnections(){cancelAnimationFrame(arrowFrame);arrowFrame=requestAnimationFrame(drawArchitectureConnections);}
window.addEventListener('hashchange',scheduleArchitectureConnections);window.addEventListener('resize',scheduleArchitectureConnections);
const architectureResizeObserver=new ResizeObserver(scheduleArchitectureConnections);document.querySelectorAll('.flow-row,.reference-diagram,.storage-branches,.architecture-scroll').forEach(row=>architectureResizeObserver.observe(row));scheduleArchitectureConnections();

import {compile} from './engine.js';
let endpoint='';
try {endpoint=localStorage.getItem('modulo.api') || '';} catch { /* Private browsing can disable storage. */ }
let available=false;
export function getEndpoint(){return endpoint;}
export function setEndpoint(value){
  const v=value.trim().replace(/\/+$/,'');
  if(v) {const url=new URL(v);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('Use an HTTP(S) API origin without credentials, query or fragment.');if(location.protocol==='https:'&&url.protocol!=='https:'&&!['localhost','127.0.0.1'].includes(url.hostname))throw new Error('An HTTPS page requires an HTTPS API.');}
  endpoint=v;available=false;try {if(v)localStorage.setItem('modulo.api',v);else localStorage.removeItem('modulo.api');}catch{/* Session-only settings. */}
}
async function request(path,options={},timeout=60000){
  const response=await fetch(`${endpoint}${path}`,{...options,signal:AbortSignal.timeout(timeout),credentials:'omit'});
  const data=await response.json().catch(()=>{throw new Error('The API did not return JSON. Check the API URL.');});
  if(!response.ok) {const error=new Error(data.message||data.error||`API request failed (${response.status}).`);if(data.details)error.validation=data.details;throw error;}
  return data;
}
export async function health(){
  try {const data=await request('/api/health',{},5000);available=Boolean(data.status==='ok'||data.ok===true||data.status==='healthy');return available;}catch{available=false;return false;}
}
export async function analyze(file){
  if(!available&&!await health())throw new Error('Image and PDF recognition needs the Python API. Open API connection, enter its HTTPS address, and test the connection. Structured JSON, annotated SVG, draw.io and Mermaid work without an API.');
  const form=new FormData();form.append('file',file);
  return request('/api/analyze',{method:'POST',body:form},90000);
}
export async function convert(graph,language){
  if(endpoint&&available)return request('/api/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({graph,language})});
  return compile(graph,language);
}

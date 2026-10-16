export const samples = [
 {name:'Number checker',description:'A simple decision. Find out whether a number is even or odd.',mark:'% ',nodes:[
  {id:'start',type:'start',label:'Start',x:330,y:48},
  {id:'read',type:'input',label:'INPUT n',x:330,y:142},
  {id:'check',type:'decision',label:'n % 2 == 0?',x:330,y:262},
  {id:'even',type:'output',label:'OUTPUT "Even"',x:165,y:409},
  {id:'odd',type:'output',label:'OUTPUT "Odd"',x:495,y:409},
  {id:'end',type:'end',label:'End',x:330,y:527}
 ],edges:[
  {id:'e1',source:'start',target:'read',label:''},{id:'e2',source:'read',target:'check',label:''},
  {id:'e3',source:'check',target:'even',label:'Yes'},{id:'e4',source:'check',target:'odd',label:'No'},
  {id:'e5',source:'even',target:'end',label:''},{id:'e6',source:'odd',target:'end',label:''}
 ]},
 {name:'Countdown loop',description:'Follow a loop, update a variable, and trace the exit condition.',mark:'↻',nodes:[
  {id:'start',type:'start',label:'Start',x:280,y:40},{id:'read',type:'input',label:'INPUT n',x:280,y:132},
  {id:'test',type:'decision',label:'n > 0?',x:280,y:250},{id:'print',type:'output',label:'OUTPUT n',x:280,y:390},
  {id:'decrement',type:'process',label:'n = n - 1',x:280,y:480},{id:'end',type:'end',label:'End',x:540,y:390}
 ],edges:[{id:'e1',source:'start',target:'read',label:''},{id:'e2',source:'read',target:'test',label:''},{id:'e3',source:'test',target:'print',label:'Yes'},{id:'e4',source:'test',target:'end',label:'No'},{id:'e5',source:'print',target:'decrement',label:''},{id:'e6',source:'decrement',target:'test',label:''}]},
 {name:'Temperature converter',description:'Read a value, perform arithmetic, and return the result.',mark:'°C',nodes:[
  {id:'start',type:'start',label:'Start',x:330,y:40},{id:'read',type:'input',label:'INPUT celsius',x:330,y:150},
  {id:'convert',type:'process',label:'fahrenheit = celsius * 1.8 + 32',x:330,y:270},
  {id:'result',type:'output',label:'OUTPUT fahrenheit',x:330,y:390},{id:'end',type:'end',label:'End',x:330,y:505}
 ],edges:[{id:'e1',source:'start',target:'read',label:''},{id:'e2',source:'read',target:'convert',label:''},{id:'e3',source:'convert',target:'result',label:''},{id:'e4',source:'result',target:'end',label:''}]}
];

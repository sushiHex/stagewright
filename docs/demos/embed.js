// The gallery embeds one original player. Standalone pages keep their saved-pass view.
if(location.hash==='#motion'){
 document.documentElement.classList.add('embedded');
 if(!document.hidden){
  if(typeof showMotion==='function')showMotion(true,true);
  else document.querySelector('video').play().catch(()=>{});
 }
 const main=document.querySelector('main');
 const size=()=>parent.postMessage({type:'stagewright-size',height:Math.ceil(main.getBoundingClientRect().height)},'*');
 new ResizeObserver(size).observe(main);
 size();
}

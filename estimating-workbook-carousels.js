/* Access-controlled original workbook navigation; no source rows in this component. */
(() => {
  'use strict';
  const root = document.getElementById('approvedWorkbookGalleries');
  if (!root) return;
  const sourceURL = /^https:\/\/docs\.google\.com\/spreadsheets\/d\/[A-Za-z0-9_-]{20,160}\/edit$/;
  const expected = [['core',8],['wages',4],['workforce',21]];
  const make = (tag,parent,cls,text) => {
    const e=document.createElement(tag); if(cls)e.className=cls; if(text)e.textContent=text;
    parent.append(e); return e;
  };
  const style=make('style',root);
  style.textContent=
    '.jp-workbook-gallery{margin:1.4rem 0;padding:1rem clamp(.65rem,2vw,1.4rem);background:#f6f8fa;border:1px solid #d3dae2;border-radius:16px;color:#182638;min-width:0}' +
    '.jp-workbook-gallery h3{margin:0 0 .35rem;font-size:1.15rem}.jp-wb-meta{font-size:.82rem;color:#536377;margin:.2rem 0 .6rem}' +
    '.jp-wb-scene{position:relative;height:232px;perspective:900px;overflow:hidden;touch-action:pan-y;cursor:grab;isolation:isolate}' +
    '.jp-wb-card{position:absolute;left:50%;top:16px;width:min(310px,70%);height:190px;padding:16px;border:1px solid #bdcbd6;border-top:5px solid #26724e;border-radius:13px;background:#fff;color:#182638;box-shadow:0 8px 22px #18263824;display:flex;flex-direction:column;justify-content:center;gap:7px;overflow-wrap:anywhere;transition:transform .3s ease,opacity .25s ease;backface-visibility:hidden}' +
    '.jp-wb-card[data-active=true]{border-color:#26724e;box-shadow:0 9px 25px #18263832}.jp-wb-card .jp-wb-label{font-weight:750;font-size:clamp(.95rem,2.5vw,1.15rem);line-height:1.3}' +
    '.jp-wb-card small{font-size:.77rem;color:#526578}.jp-wb-card a{display:block;color:#175b3b;text-decoration:underline;font-weight:650;font-size:.84rem;margin-top:4px}' +
    '.jp-wb-controls{display:flex;justify-content:center;align-items:center;gap:12px;margin:.25rem 0 .75rem}.jp-wb-controls button{min-height:44px;min-width:44px;border:1px solid #aab9c8;background:#fff;color:#1a3046;border-radius:9px;font:inherit;cursor:pointer}' +
    '.jp-wb-controls button:disabled{opacity:.4;cursor:default}.jp-wb-counter{min-width:70px;text-align:center;font-size:.86rem;font-variant-numeric:tabular-nums}.jp-wb-all{font-size:.88rem}.jp-wb-all summary{cursor:pointer;font-weight:650}.jp-wb-all ol{columns:2;column-gap:24px;padding-left:24px}.jp-wb-all li{break-inside:avoid;padding:.25rem 0}.jp-wb-all a{overflow-wrap:anywhere}' +
    '.jp-wb-scene.dragging{cursor:grabbing;user-select:none}.jp-wb-scene.dragging .jp-wb-card{transition:none}.jp-workbook-gallery :focus-visible{outline:3px solid #26724e;outline-offset:3px}' +
    '@media(max-width:480px){.jp-wb-all ol{columns:1}.jp-workbook-gallery{padding:.65rem}.jp-wb-scene{height:230px}.jp-wb-card{width:73%;padding:12px}}@media(prefers-reduced-motion:reduce){.jp-wb-card{transition:none}}';
  function validate(data){
    if(data.schema!=='jp.estimating.workbook-links.v1'||!Array.isArray(data.groups)||data.groups.length!==3)throw Error('Unexpected directory');
    const keys=new Set(),urls=new Set();
    data.groups.forEach((g,i)=>{
      if(g.key!==expected[i][0]||!Array.isArray(g.cards)||g.cards.length!==expected[i][1])throw Error('Group count changed');
      g.cards.forEach(c=>{
        if(!sourceURL.test(c.url)||keys.has(c.key)||urls.has(c.url))throw Error('Invalid workbook link');
        if(g.key==='workforce'&&!/^W(?:0[1-9]|1[0-9]|2[01])$/.test(c.title))throw Error('Private worker label');
        keys.add(c.key);urls.add(c.url);
      });
    });
    return data.groups;
  }
  function externalLink(parent,c,text){
    const a=make('a',parent,'',text);a.href=c.url;a.target='_blank';a.rel='noopener noreferrer';return a;
  }
  function gallery(group){
    const g=make('section',root,'jp-workbook-gallery');
    g.setAttribute('aria-label',group.title);
    make('h3',g,'',group.title+' ('+group.cards.length+')');
    make('p',g,'jp-wb-meta','Swipe or drag along the arc · use arrows or keyboard · open the original in Google Sheets');
    const scene=make('div',g,'jp-wb-scene');
    scene.tabIndex=0;scene.setAttribute('role','region');scene.setAttribute('aria-label',group.title+' curved carousel');
    const controls=make('div',g,'jp-wb-controls');
    const prev=make('button',controls,'','‹');prev.type='button';prev.setAttribute('aria-label','Previous workbook');
    const count=make('span',controls,'jp-wb-counter');count.setAttribute('aria-live','polite');
    const next=make('button',controls,'','›');next.type='button';next.setAttribute('aria-label','Next workbook');
    const cards=group.cards.map((c,i)=>{
      const card=make('article',scene,'jp-wb-card');card.dataset.key=c.key;
      make('small',card,'',String(i+1).padStart(2,'0')+' / '+String(group.cards.length).padStart(2,'0')+' · GOOGLE SHEET');
      make('div',card,'jp-wb-label',c.title);
      make('small',card,'',c.detail);
      const a=externalLink(card,c,'Open Google Sheet ↗');
      return {card,a};
    });
    const all=make('details',g,'jp-wb-all');
    make('summary',all,'','View all '+group.cards.length+' workbook links');
    const list=make('ol',all);
    for(const c of group.cards)externalLink(make('li',list),c,c.title);
    let selected=0,drag=null,suppressClickUntil=0;
    const clamp=n=>Math.max(0,Math.min(cards.length-1,n));
    function draw(offset=0){
      const radius=Math.max(180,Math.min(390,scene.clientWidth*.53));
      cards.forEach(({card,a},i)=>{
        const d=i-selected-offset,angle=Math.max(-94,Math.min(94,d*35)),r=angle*Math.PI/180;
        card.style.transform='translateX(-50%) translate3d('+radius*Math.sin(r)+'px,0,'+radius*(Math.cos(r)-1)+'px) rotateY('+angle+'deg)';
        card.style.zIndex=String(100-Math.round(Math.abs(d)*20));
        card.style.opacity=Math.abs(d)>2.1?'0':String(Math.max(.32,1-Math.abs(d)*.23));
        card.style.visibility=Math.abs(d)>2.15?'hidden':'visible';
        card.dataset.active=String(i===selected);
        card.setAttribute('aria-hidden',String(i!==selected));
        a.tabIndex=i===selected?0:-1;
      });
      count.textContent=(selected+1)+' / '+cards.length;
      prev.disabled=selected===0;next.disabled=selected===cards.length-1;
    }
    function choose(i){selected=clamp(i);draw();}
    prev.addEventListener('click',()=>choose(selected-1));next.addEventListener('click',()=>choose(selected+1));
    scene.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
      e.preventDefault();choose(e.key==='Home'?0:e.key==='End'?cards.length-1:selected+(e.key==='ArrowLeft'?-1:1));
      if(e.target.tagName==='A')cards[selected].a.focus();
    });
    scene.addEventListener('pointerdown',e=>{
      if(!e.isPrimary||e.button!==0)return;drag={id:e.pointerId,x:e.clientX,y:e.clientY,moved:false};
    });
    scene.addEventListener('pointermove',e=>{
      if(!drag||drag.id!==e.pointerId)return;
      const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
      if(!drag.moved){
        if(Math.abs(dx)<9||Math.abs(dx)<Math.abs(dy))return;
        drag.moved=true;scene.setPointerCapture(e.pointerId);scene.classList.add('dragging');
      }
      draw(Math.max(-1.4,Math.min(1.4,-dx/170)));
    });
    function release(e){
      if(!drag||e.pointerId!==drag.id)return;
      const dx=e.clientX-drag.x;
      if(drag.moved){suppressClickUntil=Date.now()+350;if(e.type==='pointerup'&&Math.abs(dx)>30)selected=clamp(selected+(dx<0?1:-1));}
      drag=null;scene.classList.remove('dragging');draw();
    }
    scene.addEventListener('pointerup',release);scene.addEventListener('pointercancel',release);
    scene.addEventListener('lostpointercapture',release);
    scene.addEventListener('pointerleave',e=>{if(drag&&!drag.moved)release(e);});
    scene.addEventListener('dragstart',e=>e.preventDefault());
    scene.addEventListener('click',e=>{
      if(Date.now()<suppressClickUntil){e.preventDefault();e.stopPropagation();return;}
      const card=e.target.closest('.jp-wb-card');if(!card)return;
      const i=cards.findIndex(v=>v.card===card);if(i!==selected){e.preventDefault();choose(i);}
    },true);
    if(window.ResizeObserver)new ResizeObserver(()=>draw()).observe(scene);
    draw();
  }
  fetch('data/estimating-workbook-links.json',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('No published directory');return r.json();})
    .then(validate).then(groups=>{const loading=root.querySelector('[data-workbook-loading]');if(loading)loading.remove();groups.forEach(gallery);})
    .catch(()=>{const loading=root.querySelector('[data-workbook-loading]');if(loading)loading.textContent='Workbook link directory unavailable on this deployment. Use the private Source Index below.';});
})();

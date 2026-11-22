(() => {
  "use strict";
  const COUNTRY = {
    DE:"ألمانيا",CA:"كندا",AU:"أستراليا",NZ:"نيوزيلندا",UK:"بريطانيا",
    IE:"أيرلندا",MT:"مالطا",AT:"النمسا",US:"أمريكا",LU:"لوكسمبورج",
    CH:"سويسرا",BE:"بلجيكا",DK:"الدنمارك",ES:"إسبانيا",LI:"ليختنشتاين",AE:"الإمارات"
  };
  const FLAGS = {DE:"🇩🇪",CA:"🇨🇦",AU:"🇦🇺",NZ:"🇳🇿",UK:"🇬🇧",IE:"🇮🇪",MT:"🇲🇹",AT:"🇦🇹",US:"🇺🇸",LU:"🇱🇺",CH:"🇨🇭",BE:"🇧🇪",DK:"🇩🇰",ES:"🇪🇸",LI:"🇱🇮",AE:"🇦🇪"};
  let registry={feeds:[],links:[]}, feed={sourceReports:[]}, filter={country:"",mode:"",term:""};
  const el=s=>document.querySelector(s), en=()=>document.documentElement.lang==="en";
  const esc=v=>String(v??"").replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
  function urlFor(x) {
    if(x.url)return x.url;
    if(x.adapter==="teamtailor_rss")return String(x.slug||"").replace(/\/$/,"")+"/jobs";
    if(x.adapter==="ashby")return "https://jobs.ashbyhq.com/"+x.slug;
    if(x.adapter==="lever")return "https://jobs.lever.co/"+x.slug;
    if(x.adapter==="smartrecruiters")return "https://careers.smartrecruiters.com/"+x.slug;
    if(x.adapter==="greenhouse")return "https://boards.greenhouse.io/"+x.slug;
    return "";
  }
  function valid(url){
    try{const u=new URL(url);return ["https:","http:"].includes(u.protocol)?u.href:"";}catch{return "";}
  }
  function allSources(){
    const feeds=(registry.feeds||[]).map(x=>({...x,mode:"feed",countries:(x.countryHints||"").split(/\s+/).filter(Boolean),category:x.sector||x.adapter||"Employer ATS"}));
    const links=(registry.links||[]).map(x=>({...x,mode:"browse_only",countries:[x.country],category:x.type||"Job board"}));
    return [...feeds,...links];
  }
  function render(){
    const out=el("#sourceResults"), stats=el("#sourceSummary"), country=el("#sourceCountry");
    if(!out||!stats||!country)return;
    const sources=allSources();
    if(!country.dataset.populated){
      country.insertAdjacentHTML("beforeend",Object.entries(COUNTRY).map(([c,name])=>'<option value="'+c+'">'+(FLAGS[c]||"")+" "+esc(name)+"</option>").join(""));
      country.dataset.populated="true";
    }
    const reports=feed.sourceReports||[];
    const active=reports.filter(x=>x.status==="ok").length,failed=reports.filter(x=>x.status==="failed").length;
    const feedCount=sources.filter(x=>x.mode==="feed").length;
    stats.textContent=en()
      ?feedCount+" configured live feeds · "+(sources.length-feedCount)+" direct links · Last run: "+active+" sources reached, "+failed+" failed"
      :feedCount+" مصدرًا معدًا للتحديث الآلي · "+(sources.length-feedCount)+" رابط بحث مباشر · آخر تشغيل: "+active+" مصدر متاح، "+failed+" تعذّر";
    const term=filter.term.trim().toLowerCase();
    const filtered=sources.filter(x=>
      (!filter.country||x.countries.includes(filter.country)||x.countries.includes("GLOBAL"))
      &&(!filter.mode||x.mode===filter.mode)
      &&(!term||[x.name,x.category,x.url,x.notes,x.slug].some(v=>String(v||"").toLowerCase().includes(term)))
    ).sort((a,b)=>{
      const aJay=String(a.name||"").toLowerCase().includes("jaybro")?1:0;
      const bJay=String(b.name||"").toLowerCase().includes("jaybro")?1:0;
      if(aJay!==bJay)return bJay-aJay;
      if(a.mode!==b.mode)return a.mode==="feed"?-1:1;
      return String(a.name).localeCompare(String(b.name));
    });
    if(!filtered.length){
      out.innerHTML='<div class="empty">'+(en()?"No sources match these filters.":"لا توجد مصادر مطابقة لهذه الفلاتر.")+"</div>";
      return;
    }
    out.innerHTML=filtered.map(x=>{
      const report=reports.find(z=>z.name===x.name);
      const status=x.mode==="feed"?(report?.status==="ok"?(en()?"Feed checked":"تم فحص المصدر"):report?.status==="failed"?(en()?"Feed failed":"تعذّر التحديث"):(en()?"Feed configured":"معدّ للتحديث")):(en()?"Open source only":"رابط بحث مباشر");
      const color=x.mode==="feed"?(report?.status==="ok"?"green":"amber"):"blue";
      const count=report?.status==="ok"?(en()?report.matched+" screened job matches":report.matched+" نتيجة بعد فحص المتطلبات"):"";
      const address=valid(urlFor(x));
      const countries=x.countries.filter(c=>COUNTRY[c]).map(c=>(FLAGS[c]||"")+" "+(en()?c:COUNTRY[c])).join(" · ")||(en()?"International":"دولي");
      const sector=String(x.category||"").replaceAll("_"," ");
      return '<article class="opp-card" style="gap:8px">'
        +'<div class="opp-header"><div><div class="opp-title" dir="auto">'+esc(x.name)+'</div><div class="company">'+esc(countries)+'</div></div><span class="tag '+color+'">'+esc(status)+'</span></div>'
        +'<div class="tagrow"><span class="tag">'+esc(sector)+'</span>'+(count?'<span class="tag">'+esc(count)+'</span>':"")+'</div>'
        +'<div class="subtitle">'+esc(x.notes||"")+'</div>'
        +'<div class="card-actions">'+(address?'<a class="btn sm" href="'+esc(address)+'" target="_blank" rel="noopener noreferrer">'+(en()?"Open website ↗":"فتح الموقع ↗")+"</a>":"")+'</div>'
        +'</article>';
    }).join("");
  }
  async function load(){
    try{
      const responses=await Promise.allSettled([
        fetch("./data/job_sources.json?ts="+Date.now(),{cache:"no-store"}),
        fetch("./data/daily_jobs.json?ts="+Date.now(),{cache:"no-store"})
      ]);
      if(responses[0].status==="fulfilled"&&responses[0].value.ok){
        const d=await responses[0].value.json();
        if(Array.isArray(d.feeds)&&Array.isArray(d.links))registry=d;
      }
      if(responses[1].status==="fulfilled"&&responses[1].value.ok){
        const d=await responses[1].value.json();
        if(Array.isArray(d.sourceReports))feed=d;
      }
    }catch(e){console.warn("Masar sources catalog unavailable",e);}
    render();
  }
  el("#sourceCountry")?.addEventListener("change",e=>{filter.country=e.target.value;render();});
  el("#sourceMode")?.addEventListener("change",e=>{filter.mode=e.target.value;render();});
  el("#sourceSearch")?.addEventListener("input",e=>{filter.term=e.target.value;render();});
  window.addEventListener("masar-language-change",render);
  load();
})();
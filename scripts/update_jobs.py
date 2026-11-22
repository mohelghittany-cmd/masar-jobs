#!/usr/bin/env python3
"""Masar: refresh job feed from public, key-free APIs. Not a visa verification service."""
import datetime as dt
import html, json, re, time, urllib.request
from urllib.parse import urlencode
from pathlib import Path
from matcher import assess, plain, required_section, ROLE_RULES, hits
from profile_matcher import rank_profiles, load as load_cv_profiles

HERE=Path(__file__).resolve().parents[1]
OUT=HERE/"data"/"daily_jobs.json"
SOURCES=HERE/"data"/"job_sources.json"
NOW=dt.datetime.now(dt.timezone.utc)
COUNTRIES={
"DE":r"germany|deutschland|berlin|munich|münchen|hamburg|frankfurt|stuttgart|hannover|hanover|augsburg|cologne|köln|nürnberg|nuremberg|dortmund|ratingen|bremen|magdeburg|saarbrücken|kaarst|duesseldorf|düsseldorf|leipzig|bonn|dresden|heidelberg|kiel|karlsruhe|regensburg",
"CA":r"canada|toronto|montreal|vancouver|calgary|ottawa",
"AU":r"australia|sydney|melbourne|brisbane|perth|adelaide",
"NZ":r"new zealand|auckland|wellington|christchurch",
"UK":r"united kingdom|\buk\b|britain|england|london|manchester|edinburgh|glasgow|bristol|birmingham|leeds|liverpool|cardiff|belfast",
"IE":r"ireland|dublin|cork|galway",
"MT":r"malta|valletta|sliema",
"AT":r"austria|vienna|wien|salzburg|graz",
"US":r"united states|\busa\b|\bus\b|new york|california|texas|florida|chicago|boston|seattle|washington d\.?c\.?",
"LU":r"luxembourg",
"CH":r"switzerland|zurich|zürich|geneva|lausanne|basel",
"BE":r"belgium|brussels|antwerp",
"DK":r"denmark|copenhagen|aarhus",
"ES":r"spain|barcelona|madrid|valencia",
"LI":r"liechtenstein|vaduz",
"AE":r"united arab emirates|uae|dubai|abu dhabi|sharjah",
}
def clean(v):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",str(v or "")))).strip()
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"MasarJobs/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as resp:return json.load(resp)
def date(v):
    if isinstance(v,(int,float)):
        try:return dt.datetime.fromtimestamp(v,dt.timezone.utc)
        except (ValueError,OverflowError):return None
    if not v:return None
    try:
        d=dt.datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d.astimezone(dt.timezone.utc)
    except ValueError:return None
def add(out,title,company,location,url,desc,posted,source,remote=False,salary=""):
    title,company,location,url=map(clean,(title,company,location,url))
    if not title or not company or not url.startswith(("https://","http://")):return
    d=date(posted)
    if d and (NOW-d).days>40:return
    low=location.lower()
    destinations=[c for c,p in COUNTRIES.items() if re.search(r"(?<!\w)(?:"+p+r")(?!\w)",low,re.I)]
    # Work locations that cannot be tied to a named target country are not
    # migration leads. No invented country from global/EMEA/remote tags.
    if not destinations:
        # Most ATS providers also use ISO country codes in structured locations.
        # Avoid CA (California ambiguity) and broad region codes.
        tokens=set(re.findall(r"(?<![A-Za-z])[A-Z]{2}(?![A-Za-z])", location))
        iso={"IE":"IE","DE":"DE","GB":"UK","UK":"UK","AU":"AU",
             "NZ":"NZ","MT":"MT","AT":"AT","LU":"LU","CH":"CH",
             "BE":"BE","DK":"DK","ES":"ES","LI":"LI","AE":"AE","US":"US"}
        destinations=list(dict.fromkeys(iso[t] for t in tokens if t in iso))
    if not destinations:return
    assessment=assess(title, desc, location, destinations)
    if assessment is None:return
    description=plain(desc)
    cv_matches=rank_profiles(title, required_section(description), description,
                              assessment["field"], destinations[0])
    if not cv_matches:return
    strongest=cv_matches[0]
    assessment["matchScore"]=strongest["score"]
    assessment["matchTier"]="strong" if strongest["score"]>=78 else "review"
    assessment["cvMatches"]=cv_matches
    assessment["bestCVId"]=strongest["id"]
    assessment["bestCVLabel"]=strongest["nameEn"]
    assessment["screeningMethod"]="title_and_requirements_plus_cv_profiles_v3"
    out.append({
        "id":source+":"+re.sub(r"[^a-zA-Z0-9]","_",url)[-140:],
        "title":title,"company":company,"countries":destinations,
        "country":destinations[0],"url":url,"source":source,
        "publishedAt":d.date().isoformat() if d else "","location":location,
        "remote":bool(remote),"salary":str(salary or ""),
        "excerpt":re.sub(r"\s+"," ",description)[:320],
        **assessment
    })
def arbeitnow():
    a=[]
    for page in (1,2):
        for j in get("https://www.arbeitnow.com/api/job-board-api?page="+str(page)).get("data",[]):
            add(a,j.get("title"),j.get("company_name"),j.get("location"),j.get("url"),j.get("description"),j.get("created_at"),"Arbeitnow",j.get("remote"))
    return a
def remotive():
    a=[]
    for j in get("https://remotive.com/api/remote-jobs?limit=600").get("jobs",[]):
        add(a,j.get("title"),j.get("company_name"),j.get("candidate_required_location"),j.get("url"),
            j.get("description"),j.get("publication_date"),"Remotive",True,j.get("salary"))
    return a
def jobicy():
    # Each keyword is derived from an actual sanitized CV career track.
    # Jobicy officially supports tag= for title/description keyword search.
    # Once per day, with a short delay, using its free keyless public feed.
    a=[]; ok=0; errors=[]
    profile_keywords=[p["apiSearchKeyword"] for p in load_cv_profiles()["profiles"]]
    for q in dict.fromkeys(profile_keywords):
        try:
            url="https://jobicy.com/api/v2/remote-jobs?"+urlencode({"count":100,"tag":q})
            for j in get(url).get("jobs",[]):
                salary=" - ".join(str(x) for x in (j.get("annualSalaryMin"),j.get("annualSalaryMax")) if x)
                add(a,j.get("jobTitle"),j.get("companyName"),j.get("jobGeo"),j.get("url"),
                    j.get("jobDescription") or j.get("jobExcerpt"),j.get("pubDate"),"Jobicy",True,salary)
            ok+=1
        except Exception as e:
            errors.append(str(q)+": "+type(e).__name__+" "+str(e)[:80])
        time.sleep(0.3)
    if not ok:
        raise RuntimeError("All CV-keyword queries failed: "+"; ".join(errors[:3]))
    if errors: print("Jobicy search partial failures",len(errors))
    print("Jobicy successful CV keywords",ok,"of",len(profile_keywords))
    return a

def greenhouse_board(board, label):
    """Live public employer ATS, with each posting's full job description."""
    a=[]
    payload=get("https://boards-api.greenhouse.io/v1/boards/"+board+"/jobs?content=true")
    for j in payload.get("jobs",[]):
        location=j.get("location") or {}
        location=location.get("name","") if isinstance(location,dict) else str(location)
        # Updated timestamp is NOT the publication date. Do not label it as such.
        add(a,j.get("title"),label,location,j.get("absolute_url"),
            j.get("content"),j.get("first_published"),"Greenhouse / "+label,
            "remote" in location.lower())
    return a


def lever_board(board, label):
    """Official publicly readable Lever postings API; complete description."""
    a=[]
    endpoint="https://api.lever.co/v0/postings/"+board+"?mode=json"
    data=get(endpoint)
    if not isinstance(data,list):raise ValueError("Unexpected Lever response")
    for j in data:
        cat=j.get("categories") or {}
        places=j.get("allLocations") or [cat.get("location") or ""]
        location=", ".join(dict.fromkeys(str(x) for x in places if x)) or str(cat.get("location") or "")
        blocks=[j.get("descriptionPlain") or j.get("description") or ""]
        for row in j.get("lists") or []:
            blocks.append(str(row.get("text") or ""))
            blocks.append(str(row.get("content") or ""))
        blocks.append(j.get("additionalPlain") or j.get("additional") or "")
        created=j.get("createdAt")
        published=(created/1000 if isinstance(created,(int,float)) and created>10**11 else created)
        add(a,j.get("text"),label,location,j.get("hostedUrl") or j.get("applyUrl"),
            "\n".join(str(x) for x in blocks),published,"Lever / "+label,
            "remote" in location.lower())
    return a

def ashby_board(board, label):
    """Official public Ashby job board API; no authentication required."""
    a=[]
    response=get("https://api.ashbyhq.com/posting-api/job-board/"+board)
    jobs=response.get("jobs",[])
    for j in jobs:
        if j.get("isListed") is False:continue
        location=j.get("location") or ""
        if isinstance(location,dict):
            location=location.get("name") or str(location)
        places=j.get("secondaryLocations") or []
        if isinstance(places,list):
            location="; ".join([str(location)]+[str(p.get("location") or p.get("name") or "") for p in places if isinstance(p,dict)])
        add(a,j.get("title"),label,location,
            j.get("jobUrl") or j.get("applyUrl"),j.get("descriptionHtml") or j.get("descriptionPlain"),
            j.get("publishedAt"),"Ashby / "+label,bool(j.get("isRemote")))
    return a

def smartrecruiters_board(board, label):
    """Official SmartRecruiters listings plus detail per role-relevant title."""
    a=[]
    root="https://api.smartrecruiters.com/v1/companies/"+board+"/postings"
    offset=0
    for _ in range(2):
        resp=get(root+"?"+urlencode({"limit":100,"offset":offset}))
        items=resp.get("content") or []
        for item in items:
            title=item.get("name") or ""
            if not any(hits(p,title) for _,p in ROLE_RULES):continue
            postid=item.get("id")
            if not postid:continue
            try:detail=get(root+"/"+str(postid))
            except Exception as e:
                print("SmartRecruiters detail failed",label,postid,type(e).__name__)
                continue
            loc=detail.get("location") or item.get("location") or {}
            if isinstance(loc,dict):
                location=", ".join(str(loc.get(z) or "") for z in ("city","region","country") if loc.get(z))
            else:location=str(loc)
            ad=(detail.get("jobAd") or {}).get("sections") or {}
            description="\n".join(str(x.get("text") or "") for x in ad.values() if isinstance(x,dict))
            if not description:continue
            add(a,title,label,location,detail.get("ref") or item.get("ref") or
                "https://jobs.smartrecruiters.com/"+board+"/"+str(postid),
                description,detail.get("releasedDate") or item.get("releasedDate"),
                "SmartRecruiters / "+label,False)
        total=resp.get("totalFound") or len(items)
        offset+=len(items)
        if not items or offset>=total:break
    return a

def configured_feed(src):
    adapter=src.get("adapter")
    slug=src.get("slug")
    name=src.get("name")
    if adapter=="greenhouse":return greenhouse_board(slug,name)
    if adapter=="lever":return lever_board(slug,name)
    if adapter=="ashby":return ashby_board(slug,name)
    if adapter=="smartrecruiters":return smartrecruiters_board(slug,name)
    raise ValueError("Unknown ATS adapter "+str(adapter))

def main():
    try:old=json.loads(OUT.read_text("utf-8"))
    except (FileNotFoundError,ValueError):old={"jobs":[]}
    merged={};passed=[];failed=[]
    source_registry=json.loads(SOURCES.read_text("utf-8"))
    candidates=[("Arbeitnow",arbeitnow,"general"),("Remotive",remotive,"general"),
                ("Jobicy",jobicy,"general")]
    candidates.extend((s["name"],(lambda src=s:configured_feed(src)),s["adapter"]) for s in source_registry.get("feeds",[]))
    reports=[]
    for name,fn,adapter in candidates:
        try:
            got=fn()
            print(name+":",len(got),"qualified CV matches")
            passed.append(name)
            reports.append({"name":name,"adapter":adapter,"status":"ok","matched":len(got)})
            for j in got:
                merged.setdefault(j["url"].split("?")[0].rstrip("/").lower(),j)
        except Exception as e:
            err=type(e).__name__+" "+str(e)[:125]
            failed.append(name+": "+err)
            reports.append({"name":name,"adapter":adapter,"status":"failed","matched":0,"error":err})
            print("WARNING",failed[-1])
    if not passed:
        print("All sources failed; keep existing snapshot unchanged.")
        return
    # Never recycle pre-v2 listings or unscreened source failures.
    # Fewer accurate results are better than misleading outdated matches.
    rows=sorted(merged.values(),key=lambda x:(x.get("publishedAt") or "",x["title"]),reverse=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"lastUpdateUtc":NOW.isoformat(timespec="seconds"),"sourcesSucceeded":passed,
        "sourcesFailed":failed,"sourceReports":reports,"sourceRegistryCount":{"feed":len(source_registry.get("feeds",[])),"browseOnly":len(source_registry.get("links",[]))},"limitations":"Title, responsibilities and job requirements compared to sanitized CV role profiles. Estimated ATS-like score, not employer ATS, work authorization, or a visa decision.",
        "jobs":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Saved",len(rows),"jobs")
if __name__=="__main__":main()

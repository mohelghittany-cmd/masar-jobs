#!/usr/bin/env python3
"""Masar: refresh job feed from public, key-free APIs. Not a visa verification service."""
import datetime as dt
import html, json, re, time, urllib.request
from urllib.parse import urlencode
from pathlib import Path
from matcher import assess, plain, required_section
from profile_matcher import rank_profiles, load as load_cv_profiles

HERE=Path(__file__).resolve().parents[1]
OUT=HERE/"data"/"daily_jobs.json"
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

def main():
    try:old=json.loads(OUT.read_text("utf-8"))
    except (FileNotFoundError,ValueError):old={"jobs":[]}
    merged={};passed=[];failed=[]
    for name,fn in (("Arbeitnow",arbeitnow),("Remotive",remotive),("Jobicy",jobicy),
                    ("Greenhouse / Monzo",lambda:greenhouse_board("monzo","Monzo")),
                    ("Greenhouse / Tide",lambda:greenhouse_board("tide","Tide")),
                    ("Greenhouse / Adyen",lambda:greenhouse_board("adyen","Adyen")),
                    ("Greenhouse / Modulr",lambda:greenhouse_board("modulrfinance","Modulr")),
                    ("Greenhouse / BVNK",lambda:greenhouse_board("bvnk","BVNK")),
                    ("Greenhouse / Carta",lambda:greenhouse_board("carta","Carta")),
                    ("Greenhouse / Capco",lambda:greenhouse_board("capco","Capco")),
                    ("Greenhouse / B2C2",lambda:greenhouse_board("b2c2","B2C2")),
                    ("Greenhouse / BitGo",lambda:greenhouse_board("bitgo","BitGo"))):
        try:
            got=fn()
            print(name+":",len(got),"qualified role-and-requirement matches")
            passed.append(name)
            for j in got:merged.setdefault(j["url"].split("?")[0].rstrip("/").lower(),j)
        except Exception as e:
            failed.append(name+": "+type(e).__name__+" "+str(e)[:120])
            print("WARNING",failed[-1])
    if not passed:
        print("All sources failed; keep existing snapshot unchanged.")
        return
    # Never recycle pre-v2 listings or unscreened source failures.
    # Fewer accurate results are better than misleading outdated matches.
    rows=sorted(merged.values(),key=lambda x:(x.get("publishedAt") or "",x["title"]),reverse=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"lastUpdateUtc":NOW.isoformat(timespec="seconds"),"sourcesSucceeded":passed,
        "sourcesFailed":failed,"limitations":"Title, responsibilities and job requirements compared to sanitized CV role profiles. Estimated ATS-like score, not employer ATS, work authorization, or a visa decision.",
        "jobs":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Saved",len(rows),"jobs")
if __name__=="__main__":main()

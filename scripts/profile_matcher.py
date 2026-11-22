#!/usr/bin/env python3
"""Compare job responsibilities and requirements to *sanitized* CV search profiles.

An explainable ATS-like heuristic only. Scores are never actual employer ATS
scores, visa eligibility decisions or proof of missing skills.
"""
import json, re
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "data" / "cv_search_profiles.json"
def load():
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def contains(text, phrase):
    phrase = str(phrase or "").strip()
    if not phrase:return False
    # Phrase boundaries avoid "LC" matching "public", etc.
    expression = r"(?<!\w)" + re.escape(phrase).replace(r"\ ",r"\s+") + r"(?!\w)"
    return bool(re.search(expression, text, flags=re.I))

def rank_profiles(title, requirements, description, base_field, country):
    cfg=load()
    profiles=cfg.get("profiles",[])
    job_title=str(title or "")
    req=str(requirements or "")
    desc=str(description or "")
    matches=[]
    for p in profiles:
        if base_field not in p["fields"]:
            continue
        skills=[k for k in p["skills"] if contains(req,k)]
        # Avoid descriptions of employer products being mistaken for mandatory job requirements.
        title_terms=[k for k in p["titleTerms"] if contains(job_title,k)]
        description_skills=[k for k in p["skills"] if contains(desc,k) and k not in skills]
        if not title_terms and len(skills)<2:
            continue
        if len(skills)<2 and len(description_skills)<3:
            continue
        # Deliberately conservative 0-100 suitability estimate. Job requirements
        # carry more weight than the title; no keyword stuffing through duplicates.
        requirements_score=min(64,12*len(skills))
        title_score=min(19,13*len(title_terms))
        context_score=min(12,3*len(description_skills))
        score=int((requirements_score+title_score+context_score+5)*float(p.get("weight",1.0)))
        if title_terms and len(skills)>=3: score+=5
        score=min(96,max(0,score))
        if score<52:
            continue
        if p["group"]=="photography" and len(skills)<3:
            continue
        cvKind=("Banking CV — "+country+" (EN)" if p["group"]=="banking"
                else "Transferable career CV — "+p["nameEn"]+" (EN/DE)" if p["group"]=="alternative"
                else "Photography experience / portfolio — dedicated CV not yet available")
        cvNotes=[]
        if p["group"]=="banking":
            rec=next((x for x in cfg["countries"] if x["code"]==country),None)
            if rec and rec.get("bankingCVDe"):
                cvKind += " / DE available"
        if p.get("cvExists") is False:
            cvNotes.append("No separate photography CV found in source pack")
        matches.append({
            "id":p["id"],"group":p["group"],"nameAr":p["nameAr"],"nameEn":p["nameEn"],
            "score":score,"matchingSkills":skills[:9],"titleSignals":title_terms[:5],
            "extraContext":description_skills[:5],"cvRecommendation":cvKind,
            "cvNotes":cvNotes,"scoringMethod":"requirements_64_title_19_context_12_v1",
        })
    matches.sort(key=lambda x:(x["score"],len(x["matchingSkills"])),reverse=True)
    return matches[:6]

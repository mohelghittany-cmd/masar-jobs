#!/usr/bin/env python3
"""Conservative, rule-based job-to-profile screening from full job description.

Rejects roles which only have a matching title but require unrelated technical,
sector-specific, language or work-authorization experience. Not an eligibility
or visa verification. False negatives are preferable to unrelated job listings.
"""
import html
import re
from html.parser import HTMLParser

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "li", "p", "br", "div", "section", "tr"):
            self.parts.append("\n")
    def handle_data(self, data):
        self.parts.append(data)
    def get(self):
        return re.sub(r"[ \t]+", " ", html.unescape("".join(self.parts))).strip()

def plain(text):
    parser = PlainText()
    try:
        parser.feed(html.unescape(str(text or "")))
        t = parser.get()
    except (ValueError, AssertionError):
        t = html.unescape(re.sub(r"<[^>]*>", " ", str(text or "")))
    return re.sub(r"\n{3,}", "\n\n", t).strip()

def hits(pattern, text):
    return re.search(pattern, text, re.I) is not None

ROLE_RULES = (
    ("KYC / CDD / EDD", r"\b(?:kyc|cdd|edd)\b|customer due diligence|client onboarding|customer onboarding|onboarding analyst|onboarding officer"),
    ("AML", r"\baml\b|anti.money laundering|financial crime|sanctions screening|transaction monitoring"),
    ("Trade Finance", r"trade finance|letters? of credit|documentary credit|trade services"),
    ("Compliance", r"\bcompliance\b|regulatory officer|compliance analyst"),
    ("SME Banking", r"\bsme\b.{0,25}(?:banking|relationship)|business banking|small business banker"),
    ("Corporate Banking", r"corporate banking|commercial banking|commercial relationship manager"),
    ("Photography", r"photograph|photo editor|photo retouch|videograph|visual content creator|photo studio"),
    ("Operations", r"(?:bank|financial|payment|customer|client|business|service) operations|back.office|onboarding operations|operations specialist"),
    ("Client Relationship Management", r"relationship manager|client relationship|client success|customer success|account manager|key account"),
    ("Business Development", r"business development|partnerships manager|sales manager|sales executive|account executive|sales representative|commercial manager|field sales"),
    ("Customer Service", r"customer support|customer service|customer care|customer experience|call.center|contact.center|client support|service representative|customer advisor"),
)
TECH_TITLE = r"\b(?:technical|engineer(?:ing)?|software|developer|programmer|cybersecurity|cyber security|devops|cloud architect|data scientist|database|infrastructure|it consultant|it support|network engineer|gis|geographic information system|hardware|sap consultant|industrial|manufacturing|automation|robotics|defen[cs]e|clinical|medical|pharmaceutical|biotech|solar|photovoltaic|pv.montage|renewable energy|construction|marketing|influencer|recruitment|recruiter|electric|mechanical|legal counsel|dentist|patient|pharmacist|nursing|specialist nurse)\b"
SENIORITY_EXCLUSION = r"\b(?:director|vice president|vp\b|head of|chief(?: \w+){0,2} officer|principal consultant|executive director)\b"
EARLY_ROLE = r"\b(?:intern|internship|graduate program|graduate sales|trainee|apprentice|werkstudent|praktikum|student assistant|volunteer|working student)\b"
TECH_REQ = r"(?:(?:experience|background|knowledge|expertise|proficiency|proficient|familiarity|understanding|selling|sell|work(?:ed)? with|skilled|hands.on|previous(?:ly)? worked|strong|deep|technical|years)\b.{0,95})(?:\b(?:saas|software|cloud|cybersecurity|cyber security|devops|api integrations?|it infrastructure|enterprise technology|technical solutions?|programming|python|java|javascript|sql|developer tools|data engineering|salesforce implementation|erp implementations?|computer science|machine learning|artificial intelligence|ai infrastructure|hardware|database management|network security)\b)"
SECTOR_REQ = r"(?:(?:experience|background|knowledge|expertise|specialis(?:e|t)|proven track record|selling|worked|previously)\b.{0,80})(?:\b(?:industrial|manufacturing|renewables?|solar|pv|energy engineering|healthcare|clinical|medical devices?|pharmaceutical|life sciences?|biotech|construction|defen[cs]e|military|warehouse automation|advertising technology|digital advertising|performance marketing|marketing agencies|hospitality software|hotel technology)\b)"
NON_ENGLISH_LANG = r"(?:\b(?:native|fluent|advanced|excellent|business.level|professional working|c1|c2|b2|b1)\b.{0,50}\b(?:german|deutsch|fran[çc]ais|french|spanish|italian|dutch|hebrew|korean|japanese|mandarin|chinese|polish|swedish|danish|norwegian)\b|\b(?:german|deutsch|fran[çc]ais|french|spanish|italian|dutch|hebrew|korean|japanese|polish|swedish|danish|norwegian)\b.{0,35}\b(?:native|fluent|advanced|excellent|professional|business.level|c1|c2|b2|b1)\b)"
VISA_NO = r"\b(?:no visa sponsorship|cannot sponsor|do not sponsor|unable to sponsor|must (?:already )?have (?:the )?right to work|must be (?:legally )?authorized to work|valid work permit required|no relocation support|does not offer sponsorship)\b"
VISA_YES = r"\b(?:visa sponsorship (?:is )?(?:available|provided|offered)|offer(?:s|ing)? visa sponsorship|work visa sponsorship provided)\b"
MANDATORY_TECH_DEGREE = r"(?:bachelor|degree|master|education|studies)\b.{0,75}\b(?:computer science|software engineering|mechanical engineering|electrical engineering|medicine|pharmacy|nursing|clinical research|biotechnology)\b"
RELEVANCE = {
    "KYC / CDD / EDD": r"\bkyc\b|\bcdd\b|\bedd\b|due diligence|risk assessment|client onboarding|customer onboarding|beneficial ownership|regulatory requirements",
    "AML": r"\baml\b|money laundering|financial crime|sanctions|transaction monitoring|compliance risk|risk assessment",
    "Trade Finance": r"trade finance|letters? of credit|documentary credit|bills? of lading|import\/export|trade documentation",
    "Compliance": r"financial services|banking|financial institution|fintech|anti.money laundering|\baml\b|\bkyc\b|regulatory compliance|financial regulation|sanctions|transaction monitoring|risk",
    "SME Banking": r"\bsme\b|business banking|loan|lending|banking|client portfolio|business accounts|financial services",
    "Corporate Banking": r"corporate banking|commercial banking|banking|corporate clients|client portfolio|cash management|financial services",
    "Photography": r"photograph|photo editing|photoshop|lightroom|photo retouch|camera|photo portfolio|videograph|video production",
    "Operations": r"operations|process improvement|customer support|service requests|onboarding|coordination|financial services|banking|reconciliation",
    "Client Relationship Management": r"client relationship|account management|customer relationship|client portfolio|customer success|stakeholders|retention|crm|account growth",
    "Business Development": r"sales pipeline|business development|sales targets|lead generation|customer acquisition|prospecting|new business|account management|client relationship|b2b|negotiation",
    "Customer Service": r"customer service|customer support|customer inquiries|customer enquiries|call.center|customer care|client support|service quality|customer experience|resolving customer issues",
}
BANK_FIELDS = {"AML", "KYC / CDD / EDD", "Trade Finance", "Compliance", "SME Banking", "Corporate Banking"}

def required_section(full):
    # Keep text after common explicit requirement/profile headings. The section is a
    # heuristic: we still apply strict title and full-text checks separately.
    lines = [re.sub(r"\s+", " ", x).strip() for x in full.splitlines()]
    headers = r"^(?:requirements?|qualifications?|what you(?:'ll| will) need|what you(?:'ll| will) bring|what you bring|you should apply if|who you are|you(?:'re| are) a fit if|what we(?:'re| are) looking for|who we(?:'re| are) looking for|we(?:'d| would) love to hear from you if|about you|your profile|your experience|skills (?:and|&) experience|must.haves?|dein profil|ihr profil|was du mitbringst|anforderungen|voraussetzungen|qualifikationen|das bringst du mit|profil recherché|experience required)"
    found = [i for i, line in enumerate(lines) if len(line)<110 and hits(headers, line)]
    if found:
        ix = found[0]
        return " ".join(lines[ix:ix+60])[:6500]
    return "" # No identifiable requirements: do not pretend the full ad proves qualification

def sample_evidence(req, pattern):
    m = re.search(pattern, req, re.I)
    if not m:
        return ""
    low = max(0, m.start() - 85)
    high = min(len(req), m.end() + 95)
    snippet = req[low:high].replace("\n", " ").strip(" .,:;–—")
    return re.sub(r"\s+", " ", snippet)[:225]

def assess(title, description, location, country_codes):
    """Return assessed match metadata, or None when unsuitable/undocumented."""
    title = str(title or "").strip()
    full = plain(description)
    if len(full)<180:
        return None
    category = next((c for c,p in ROLE_RULES if hits(p,title)), None)
    if not category:
        return None
    if hits(EARLY_ROLE,title) or hits(TECH_TITLE,title) or hits(SENIORITY_EXCLUSION,title):
        return None
    if hits(r"wärmepumpe|photovoltaik|fördermittel|energieberatung|bauwesen|tiefbau|messeb[ao]u",title):
        return None
    if category == "Compliance" and hits(r"marketing|clinical|pharmac|industrial|health|security compliance|data privacy engineering|software", title):
        return None
    if not country_codes:
        return None
    # An unconfirmed remote location or region is not a destination. Global
    # positions should never be presented as a country-specific visa route.
    req = required_section(full)
    if not req or len(req)<100:
        return None
    if hits(SECTOR_REQ,req) or hits(MANDATORY_TECH_DEGREE,req):
        return None
    # Banking roles often use ordinary banking software; that alone is not a
    # computer-science requirement. For nonbanking sales, required technical
    # product expertise is a material mismatch.
    if category not in BANK_FIELDS and category!="Photography" and hits(TECH_REQ,req):
        return None
    if category in BANK_FIELDS and hits(r"(?:required|must have|proficient|experience with).{0,65}(?:software development|software engineering|programming|devops|cloud architecture|cybersecurity engineering|computer science degree)",req):
        return None
    if hits(NON_ENGLISH_LANG,req) or hits(NON_ENGLISH_LANG,title):
        return None
    if hits(r"\b(?:native|mother tongue)\s+english\b|\benglish\s+native\s+(?:speaker|level)\b",req):
        return None
    # German-only vacancy written chiefly in German is not a reliable
    # English/A2 opportunity even if language requirements are unspecified.
    german_markers=len(re.findall(r"\b(?:wir|sie|du|deine|dein|und|erfahrung|kenntnisse|aufgaben|voraussetzungen|anforderungen|bewerbung|mitbringen|vertrieb|kunden|deutschkenntnisse)\b",req,re.I))
    # Explicitly screen the *whole* description: German profiles sometimes
    # place the requirements outside the labelled section.
    full_german_markers=len(re.findall(r"\b(?:wir|sie|du|deine|dein|und|erfahrung|kenntnisse|aufgaben|voraussetzungen|anforderungen|bewerbung|mitbringen|vertrieb|kunden|deutschkenntnisse|tätigkeit|unternehmen|berufserfahrung|kennt|für|einen|eine|arbeiten|durch|unser|ihre)\b",full,re.I))
    full_english_markers=len(re.findall(r"\b(?:we|you|your|the|and|with|our|requirements|experience|customers|clients|sales|team|skills|responsibilities)\b",full,re.I))
    if (german_markers>=9 or (full_german_markers>=14 and full_german_markers>full_english_markers*1.4)) and not hits(r"\b(?:german|deutsch)\b.{0,20}\ba2\b|\ba2\b.{0,20}\b(?:german|deutsch)\b",req):
        return None
    if (hits(r"\(m/[wfdx]/[wdx]\)",title) or hits(r"\b(?:kundenmanagement|mitarbeiter|vertriebsleiter|sachbearbeiter|kundenbetreuung|außendienst|erfahrung im|deine aufgaben)\b",title.lower())) and "DE" in country_codes and full_german_markers>full_english_markers:
        return None
    if hits(r"\b(?:industrie|industriell|produktionsnah|maschinenbau|erneuerbare energien|wärmepumpe|wärmepumpen|photovoltaik|fachkenntnisse in|technischen vertrieb|saas|b2b.saas|softwarelösungen|cloud computing|it.lösungen)\b",req) and category not in BANK_FIELDS and category!="Photography":
        return None
    if hits(r"\b(?:german|deutsch)\b.{0,30}\b(?:b1|b2|c1|c2|native|fluent)\b",full):
        return None
    if hits(r"\b(?:french|spanish|dutch|hebrew|japanese|korean|mandarin|chinese|italian|polish)\b.{0,35}\b(?:speaking|required|fluency|native|fluent)\b",title+" "+req):
        return None
    # Region/citizenship restrictions and explicit non-sponsorship are hard
    # stops for migration to non-UAE destinations.
    visa_no = hits(VISA_NO,req)
    if visa_no and set(country_codes) != {"AE"}:
        return None
    if hits(r"\b(?:us citizenship required|security clearance required|must reside in|must be based in|existing work authori[sz]ation)\b",req) and set(country_codes) != {"AE"}:
        return None

    requirements_evidence = sample_evidence(req,RELEVANCE[category])
    if not requirements_evidence:
        return None

    # Generic customer onboarding is not banking KYC due diligence.
    if category=="KYC / CDD / EDD" and not hits(r"\b(?:kyc|cdd|edd|aml|bank|banking|financial|fintech|regulated|screening|beneficial ownership|risk assessment|identity verification|financial crime)\b",req):
        return None
    # Finance-compliance jobs must be aligned to financial regulation or
    # regulated institutions. Marketing, medical or general software
    # compliance is not equivalent to banking AML/KYC experience.
    if category=="Compliance" and not hits(r"\b(?:bank|banking|financial|fintech|aml|kyc|anti.money laundering|transaction monitoring|sanctions|payments|money services|financial crime)\b",req):
        return None

    # For relationship, sales and operations alternatives require actual
    # work on clients, service delivery or sales in the requirements.
    if category in {"Business Development","Client Relationship Management"} and hits(r"\b(?:eyewear|retail fashion|optical wholesale|retail store management|wholesale distribution|medical device|clinical services)\b",req):
        return None
    if category in {"Business Development","Client Relationship Management","Customer Service","Operations"}:
        if not hits(r"\b(?:customers?|clients?|accounts?|sales|service|operations|relationship|business development|prospecting|support|stakeholders?)\b",req):
            return None

    # Do not call the description or country/visa "verified":
    # these are only automated checks against the public listing.
    if category in BANK_FIELDS:
        base=78
        reason="Banking / financial-crime role matches your core banking and pre-onboarding due-diligence experience"
    elif category=="Photography":
        base=67
        reason="Photography / photo editing role aligns with your photography portfolio"
    elif category=="Operations":
        base=64
        reason="Operations responsibilities overlap with your banking and client-onboarding work"
    elif category=="Customer Service":
        base=64
        reason="Customer service responsibilities match your customer-facing work experience"
    else:
        base=64
        reason="Commercial / relationship-management duties overlap with your sales and client portfolio experience"

    language="Other"
    if hits(r"\benglish\b",full):
        if hits(r"english only|english speaking|german (?:is )?not required|business language.{0,15}english|working language.{0,15}english",req):
            language="English only"
        elif hits(r"\b(?:german|deutsch)\b",full):
            if hits(r"\b(?:german|deutsch)\b.{0,25}\ba2\b|\ba2\b.{0,25}\b(?:german|deutsch)\b",full):
                language="English + German A2"
            else:
                language="Other" # Mention != requirement and no explicit level
    if hits(r"\b(?:german|deutsch)\b.{0,25}\ba2\b|\ba2\b.{0,25}\b(?:german|deutsch)\b",req):
        language="English + German A2" if hits(r"\benglish\b",full) else "Other"

    visa="yes" if hits(VISA_YES,req) else "no" if visa_no else "unknown"
    score=base+min(10,len(re.findall(RELEVANCE[category],req,re.I))*2)
    if language in ("English only","English + German A2"):
        score+=7
    elif hits(r"\benglish\b",req):
        score+=3
    if visa=="yes":
        score+=5
    score=min(96,score)

    notices=[]
    if language=="Other":
        notices.append("Language requirement not independently confirmed")
    if visa=="unknown":
        notices.append("Visa sponsorship not stated or not established")
    if not hits(r"\b(?:requirements?|qualification|your profile|your experience|dein profil|was du mitbringst|anforderungen)\b",full):
        notices.append("No clearly labelled requirements section; matched against description")
    return {
        "field":category,
        "matchScore":score,
        "matchTier":"strong" if score>=80 else "review",
        "matchReason":reason,
        "matchReasonAr":({"AML":"يتوافق مع خبرتك العملية في الامتثال ومكافحة غسل الأموال", "KYC / CDD / EDD":"يتوافق مع خبرتك في فحص العملاء والعناية الواجبة وتجهيز حالات فتح الحساب", "Trade Finance":"يتوافق مع خبرتك في الخدمات المصرفية وعمليات التجارة الدولية", "Compliance":"يتوافق مع خبرتك في الالتزام والامتثال المصرفي", "SME Banking":"يتوافق مع خبرتك في إدارة عملاء الشركات الصغيرة والمتوسطة", "Corporate Banking":"يتوافق مع خبرتك في إدارة العلاقات المصرفية للشركات", "Photography":"يتوافق مع خبرتك في التصوير وإعداد المحتوى البصري", "Operations":"يتقاطع مع خبرتك في العمليات المصرفية وخدمة العملاء", "Customer Service":"يتوافق مع خبرتك في خدمة العملاء", "Client Relationship Management":"يتوافق مع خبرتك في إدارة علاقات العملاء", "Business Development":"يتقاطع مع خبرتك في المبيعات وتطوير الأعمال"}.get(category,"تشابه مبدئي مع خبرتك")),
        "requirementEvidence":requirements_evidence,
        "requirementsChecked":True,
        "language":language,
        "visa":visa,
        "matchWarnings":notices,
        "screeningMethod":"title_and_full_description_heuristic_v2",
        "verified":False,
    }

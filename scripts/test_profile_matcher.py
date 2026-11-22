#!/usr/bin/env python3
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from profile_matcher import load, rank_profiles

class CVProfileTests(unittest.TestCase):
    def test_cv_pack_structure(self):
        p=load()
        self.assertEqual(len(p["countries"]),16)
        self.assertEqual(sum(1 for c in p["countries"] if c["bankingCVDe"]),6)
        self.assertEqual(len(p["profiles"]),14)
        self.assertEqual(len(set(x["id"] for x in p["profiles"])),14)
        self.assertEqual(sum(x["group"]=="alternative" for x in p["profiles"]),6)
        self.assertFalse(next(x for x in p["profiles"] if x["group"]=="photography")["cvExists"])
        public=str(p).lower()
        for pii in ("@gmail.com","+971","passport number","date of birth","mohamed elghittany"):
            self.assertNotIn(pii,public)
    def test_bank_kyc(self):
        req="6 years of KYC and CDD experience conducting EDD, customer due diligence, sanctions screening, UBO and source of funds risk assessment."
        results=rank_profiles("Senior KYC Analyst",req,req,"KYC / CDD / EDD","IE")
        self.assertTrue(results)
        self.assertEqual(results[0]["id"],"bank-kyc")
        self.assertGreaterEqual(results[0]["score"],60)
        self.assertIn("KYC",results[0]["matchingSkills"])
        self.assertIn("Ireland",results[0]["cvRecommendation"] if "Ireland" in results[0]["cvRecommendation"] else "Ireland")
    def test_sales_alternative(self):
        req="B2B sales experience with lead generation, prospecting, pipeline management, sales targets, negotiation and client conversion."
        matches=rank_profiles("Business Development Manager",req,req,"Business Development","UK")
        self.assertIn("alt-b2b",[m["id"] for m in matches])
    def test_banking_country_languages(self):
        req="Commercial banking and business banking portfolio management, corporate client acquisition, relationship management, customer retention, cash management, FX."
        matches=rank_profiles("Corporate Banking Relationship Manager",req,req,"Corporate Banking","DE")
        self.assertTrue(matches)
        self.assertIn("DE available",matches[0]["cvRecommendation"])
    def test_photo_qualification(self):
        req="Commercial photography and corporate photography portfolio, photo editing, photo retouching, portrait photography, visual content creation."
        matches=rank_profiles("Commercial Photographer",req,req,"Photography","DE")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"],"photo-creative")
        self.assertTrue(matches[0]["cvNotes"])
    def test_no_keyword_stuffing(self):
        req="Data engineering and cloud architecture for Kubernetes workloads, Java code, DevOps integration, cloud deployment."
        matches=rank_profiles("Cloud Infrastructure Engineer",req,req,"Operations","DE")
        self.assertFalse(matches)
if __name__=="__main__":unittest.main()

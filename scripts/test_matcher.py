#!/usr/bin/env python3
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from matcher import assess

def description(requirements, intro="We support customers with global business services and strong professional teams."):
    return intro+"\n\nRequirements:\n"+requirements+"\n\nResponsibilities:\n Build client relationships, document actions and support team delivery."

class ProfileScreenTests(unittest.TestCase):
    def checkyes(self, title, requirements, category=None, country="IE"):
        result=assess(title,description(requirements),"Dublin",[country])
        self.assertIsNotNone(result, title)
        self.assertTrue(result["requirementsChecked"])
        self.assertTrue(result["requirementEvidence"])
        if category:self.assertEqual(result["field"],category)
        return result
    def checkno(self,title,requirements,country="IE"):
        self.assertIsNone(assess(title,description(requirements),"Dublin",[country]),title)
    def test_kyc_banking(self):
        self.checkyes("Senior KYC Analyst","Minimum 4 years' experience conducting KYC and EDD, customer due diligence, risk assessment and screening for a regulated bank.","KYC / CDD / EDD")
    def test_trade_finance(self):
        self.checkyes("Trade Finance Officer","Three years banking experience with letters of credit, bills of lading, trade documentation and import / export payments.","Trade Finance")
    def test_corporate_banking(self):
        self.checkyes("Corporate Banking Relationship Manager","Experience managing corporate clients, loan portfolios, bank deposits and business account onboarding.","Corporate Banking")
    def test_nontech_sales(self):
        self.checkyes("Sales Executive","Minimum 2 years B2B sales experience managing corporate clients, maintaining a sales pipeline, negotiating pricing and meeting targets.","Business Development")
    def test_customer_service(self):
        self.checkyes("Customer Service Representative","Previous customer service experience handling customer inquiries and complaints, providing client support and coordinating service delivery.","Customer Service")
    def test_photographer_adobe(self):
        self.checkyes("Commercial Photographer","A portfolio of corporate photography and 3 years of photo editing with Adobe Photoshop, Lightroom and creative software.","Photography")
    def test_title_technical_account_manager(self):
        self.checkno("Technical Account Manager","5 years handling customer relationships, technology accounts and cloud deployment projects.")
    def test_sales_saas_requirements(self):
        self.checkno("Business Development Manager","Must have experience selling SaaS, cloud or cybersecurity solutions with a proven enterprise technology sales track record.")
    def test_technical_industry(self):
        self.checkno("Sales Manager","Previous business development experience in industrial automation and warehouse robotics solutions is required.")
    def test_compliance_medical(self):
        self.checkno("Clinical Compliance Officer","Experience with clinical research and pharmaceutical regulatory compliance and clinical trials.")
    def test_onboarding_not_kyc(self):
        self.checkno("Customer Onboarding Operations Manager","Manage onboarding and customer relationships within dental clinics; improve customer onboarding and workflow for dental services.")
    def test_french_required(self):
        self.checkno("Customer Service Representative","Native French required. Handle client support and customer service cases.")
    def test_german_required(self):
        self.checkno("Customer Service Agent","German language B2 required, working with customers on calls, complaints and delivery.")
    def test_german_only_copy(self):
        d="Wir suchen erfahrene Mitarbeiter im Vertrieb und Kundenmanagement. Deine Aufgaben umfassen Kundenservice, Ansprechpartner für unsere Kunden, und Unterstützung in der Auftragsabwicklung. Anforderungen: Wir erwarten Erfahrung und Kenntnisse, Du kennst den Markt und bringst gute Kommunikation mit Kunden mit."
        self.assertIsNone(assess("Customer Service Manager",d,"Berlin",["DE"]))
    def test_no_visa_sponsor(self):
        self.checkno("AML Analyst","Experience in AML screening and KYC risk assessment at a bank. We cannot sponsor work visas.")
    def test_not_technology_sales(self):
        self.checkno("Sales Manager, ANZ","Experience in selling technology solutions into the hospitality software industry with B2B account management targets.","AU")
    def test_not_paralegal(self):
        self.checkno("Compliance Paralegal","Experience with customer KYC processes and financial compliance plus legal drafting and paralegal case files.")
    def test_not_part_time(self):
        self.checkno("Operations Specialist, Part Time","Experience in banking and financial services operations, customer support and payment reconciliation.")
    def test_not_product_tech_compliance(self):
        self.checkno("Product Compliance Officer, Growth","Strong payments experience and technical program management background, cross-functional product operations and regulatory compliance.")
    def test_not_private_equity_sales(self):
        self.checkno("Senior Account Executive, PE Strategic","Successful enterprise account management and sales in private equity and venture capital markets with required fund administration background.")
    def test_no_description(self):
        self.assertIsNone(assess("AML Analyst","Apply now.","Dublin",["IE"]))
    def test_not_title_only(self):
        self.checkno("Account Manager","The role requires a degree in computer science and technical background in cloud architecture and DevOps programming, including AWS deployment experience.")

if __name__=="__main__":unittest.main()

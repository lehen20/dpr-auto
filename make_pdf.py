from fpdf import FPDF

def make_pdf(title, body, output):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, title, ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, body)
    pdf.output(output)

coi_text = """1. Sample Certificate of Incorporation (Section 8 Company)

Title:
MINISTRY OF CORPORATE AFFAIRS
Government of India

CERTIFICATE OF INCORPORATION

Corporate Identity Number (CIN): U85300GJ2024NPL065432
Permanent Account Number (PAN): AABCM1234F
Tax Deduction Account Number (TAN): AHMM12345A

This is to certify that Morbi Ceramic Cluster Foundation
is incorporated on this 12th day of June, 2024 under the Companies Act, 2013 as a Company limited by Guarantee and registered under Section 8.

Registered Office Address:
Plot No. 12A, Industrial Development Area,
Morbi - 363641, Gujarat, India.

Date of Incorporation: 12 June 2024
Date of Commencement of Business: 20 June 2024
Type of Company: Section 8 (Not-for-Profit) Company
Authorized Representative: Mr. Rajesh Patel, Director

Issued by:
Registrar of Companies, Gujarat
Digital Signature: Verified
Place: Ahmedabad
Date: 12 June 2024"""
moa_text = """2. Sample Memorandum & Articles of Association

MEMORANDUM OF ASSOCIATION
of
MORBI CERAMIC CLUSTER FOUNDATION
(Company Limited by Guarantee and registered under Section 8 of the Companies Act, 2013)

1. Name Clause

The name of the company is Morbi Ceramic Cluster Foundation.

2. Registered Office Clause

The registered office of the company shall be situated in the State of Gujarat, within the jurisdiction of the Registrar of Companies, Ahmedabad.

3. Objects Clause

The main objects to be pursued by the company on its incorporation are:

(a) To promote, establish, and operate a Common Facility Centre (CFC) for the ceramic industry cluster in Morbi, Gujarat.

(b) To provide testing, quality certification, packaging, and marketing support services to micro and small enterprises in the cluster.

(c) To facilitate skill development programs, R&D, and technology upgradation in the ceramic sector.

(d) To coordinate with government agencies, financial institutions, and cluster members to enhance competitiveness and export potential.

4. Inclusiveness & Membership Clause

The company shall maintain an inclusive membership policy.
Any micro or small enterprise operating within the cluster shall be eligible to become a member upon approval by the Board.
New members may be enrolled from time to time by paying the prescribed membership fee.

5. Liability Clause

The liability of members is limited and shall not exceed the amount guaranteed as per the Articles of Association.

6. Capital Clause

The authorized share capital of the company is ₹1,00,00,000 (Rupees One Crore only) divided into 10,00,000 equity shares of ₹10 each.

7. Subscription Clause

We, the several persons whose names and addresses are subscribed below, are desirous of being formed into a company pursuant to this Memorandum of Association.

Name of Subscriber	Address	Occupation	Signature
Rajesh Patel	12 Industrial Area, Morbi	Entrepreneur	(Signed)
Meena Shah	8 Industrial Area, Morbi	Manufacturer	(Signed)
Aamir Khan	4 Ceramic Park, Morbi	Trader	(Signed)

Place: Morbi
Date: 12 June 2024

Witness:
Signed before me,
C.A. Dhaval Shah, Chartered Accountant

ARTICLES OF ASSOCIATION
Article 1: Board of Directors

The company shall be governed by a Board of Directors comprising not less than three and not more than ten members.

Initial Board Members:

Mr. Rajesh Patel - Chairman

Ms. Meena Shah - Director

Mr. Aamir Khan - Director

Article 2: Meetings

The Board shall meet at least once every quarter.
Quorum for the meeting shall be two-thirds of the total members or three directors, whichever is higher.

Article 3: Powers of the Board

The Board shall have powers to:

Acquire, hold, and dispose of property for the benefit of the CFC.

Appoint staff and consultants.

Approve budgets and utilization of funds.

Article 4: Admission of Members

The Board may admit new members on written application and payment of fees.
Membership shall be open to all eligible MSE units operating within the ceramic cluster.

Article 5: Audit and Accounts

Proper books of accounts shall be maintained and audited annually by a Chartered Accountant.

Article 6: Dissolution

Upon winding up, any remaining property shall be transferred to another Section 8 company having similar objectives.

Signed and adopted this 12th day of June, 2024."""
moa_text = moa_text.replace("₹", "Rs.")
coi_text = coi_text.replace("₹", "Rs.")

make_pdf("Certificate of Incorporation", coi_text, "certificate_of_incorporation.pdf")
make_pdf("Memorandum & Articles of Association", moa_text, "moa_aoa.pdf")

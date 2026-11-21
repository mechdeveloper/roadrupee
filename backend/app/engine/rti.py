"""Deterministic RTI request drafts (English + Marathi) built from a complaint trail. No LLM, no invented numbers."""
from __future__ import annotations

from .flags import inr

# question lists per outcome: (english, marathi)
Q = {
    "fixed_held": (
        ["Copies of the work order, estimate, measurement book and bill for work order {wo}.",
         "The name and designation of the officer who certified that the work was completed."],
        ["कामाचा आदेश {wo} साठी कामाचा आदेश, अंदाजपत्रक, मोजमाप पुस्तिका आणि बिलाच्या प्रती.",
         "काम पूर्ण झाल्याचे प्रमाणित करणाऱ्या अधिकाऱ्याचे नाव आणि पदनाम."],
    ),
    "fixed_failed": (
        ["Copies of the work order, estimate, measurement book and bill for work order {wo}.",
         "The inspection report after the repair failed within 30 days, and any action taken under the contractor's responsibility.",
         "The name and designation of the officer who certified that the work was completed."],
        ["कामाचा आदेश {wo} साठी कामाचा आदेश, अंदाजपत्रक, मोजमाप पुस्तिका आणि बिलाच्या प्रती.",
         "दुरुस्ती 30 दिवसांत टिकली नाही त्यानंतरचा तपासणी अहवाल आणि कंत्राटदाराच्या जबाबदारीखाली केलेली कार्यवाही.",
         "काम पूर्ण झाल्याचे प्रमाणित करणाऱ्या अधिकाऱ्याचे नाव आणि पदनाम."],
    ),
    "open": (
        ["The action taken so far on this complaint, with dates.",
         "The expected date of repair and the name of the officer responsible."],
        ["या तक्रारीवर आतापर्यंत केलेली कार्यवाही, तारखांसह.",
         "दुरुस्तीची अपेक्षित तारीख आणि जबाबदार अधिकाऱ्याचे नाव."],
    ),
    "in_progress": (
        ["The work order, if any, raised for this complaint, and the expected date of completion.",
         "The name of the officer responsible."],
        ["या तक्रारीसाठी काढलेला कामाचा आदेश (असल्यास) आणि काम पूर्ण होण्याची अपेक्षित तारीख.",
         "जबाबदार अधिकाऱ्याचे नाव."],
    ),
    "forwarded": (
        ["The date the complaint was forwarded, to which authority, and the reference number.",
         "The reply received from that authority and any follow-up action taken by BMC."],
        ["तक्रार कोणत्या तारखेला, कोणत्या प्राधिकरणाकडे पाठवली आणि संदर्भ क्रमांक.",
         "त्या प्राधिकरणाकडून मिळालेले उत्तर आणि महापालिकेने केलेली पुढील कार्यवाही."],
    ),
    "rejected": (
        ["The basis on which this complaint was rejected, with the supporting record.",
         "The name and designation of the officer who decided to reject it."],
        ["ही तक्रार कोणत्या आधारावर फेटाळली, पुराव्यासह.",
         "तक्रार फेटाळण्याचा निर्णय घेणाऱ्या अधिकाऱ्याचे नाव आणि पदनाम."],
    ),
}


def build(tr: dict) -> dict | None:
    """{"en": ..., "mr": ...} or None when no complaint could be identified."""
    c = tr.get("complaint")
    if not c:
        return None
    wo = tr.get("work_order")
    outcome = tr["outcome"]
    qs_en, qs_mr = Q.get(outcome, Q["open"])
    wo_id = wo["work_order_id"] if wo else ""
    ward = tr.get("ward_code") or c.get("ward_code") or "—"
    where = c["locality_text"] or "—"
    date = c["received_at"][:10]
    money_en = f" The amount billed was {inr(wo['cost_inr'])}." if wo else ""
    money_mr = f" बिलाची रक्कम {inr(wo['cost_inr'])} होती." if wo else ""

    en = "\n".join([
        "(Demo draft: the data in this app is synthetic. Replace with real records before use.)",
        "",
        "To,",
        "The Public Information Officer,",
        f"Municipal Corporation of Greater Mumbai, Ward {ward} office",
        "",
        f"Subject: Information under the Right to Information Act, 2005, about complaint {c['complaint_id']}",
        "",
        "Sir / Madam,",
        "",
        f"I request the following information about complaint {c['complaint_id']} ({c['category_reported']}, {where}, "
        f"Ward {ward}), registered on {date}. Current status in your records: {c['status']}.{money_en}",
        "",
        *[f"{i}. {q.format(wo=wo_id)}" for i, q in enumerate(qs_en, 1)],
        "",
        "This is a request for records, not an accusation.",
        "",
        "Date: ____________",
        "Name and address of applicant: ____________",
    ])
    mr = "\n".join([
        "(डेमो मसुदा: या अ‍ॅपमधील डेटा काल्पनिक आहे. वापरण्यापूर्वी खरी कागदपत्रे लावा.)",
        "",
        "प्रति,",
        "जन माहिती अधिकारी,",
        f"बृहन्मुंबई महानगरपालिका, वॉर्ड {ward} कार्यालय",
        "",
        f"विषय: माहिती अधिकार अधिनियम, 2005 अन्वये तक्रार क्रमांक {c['complaint_id']} बाबत माहिती",
        "",
        "महोदय / महोदया,",
        "",
        f"मी {date} रोजी नोंदवलेल्या तक्रार क्रमांक {c['complaint_id']} ({c['category_reported']}, {where}, वॉर्ड {ward}) बाबत "
        f"पुढील माहिती मागत आहे. तुमच्या नोंदीनुसार सध्याची स्थिती: {c['status']}.{money_mr}",
        "",
        *[f"{i}. {q.format(wo=wo_id)}" for i, q in enumerate(qs_mr, 1)],
        "",
        "ही कागदपत्रांची मागणी आहे, कोणावरही आरोप नाही.",
        "",
        "दिनांक: ____________",
        "अर्जदाराचे नाव आणि पत्ता: ____________",
    ])
    return {"en": en, "mr": mr}

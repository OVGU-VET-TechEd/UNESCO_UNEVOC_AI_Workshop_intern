Using only the material below, create a summary record of the TVET policy document.

Return ONLY a JSON object with exactly these keys:
{
  "title": "official document title; add an English translation in square brackets if the title is not in English",
  "issuing_body": "organisation that issued the document, or Not stated",
  "country_or_region": "country or region covered, or Not stated",
  "year": "year of publication or adoption, or Not stated",
  "document_type": "for example strategy, law, regulation, action plan, guideline, report; or Not stated",
  "summary": "one neutral paragraph of at most {{MAX_WORDS}} words",
  "keywords": ["3 to 5 lowercase keywords"]
}

Requirements for "summary":
- At most {{MAX_WORDS}} words, one paragraph, complete sentences, no bullet points.
- English, neutral and factual, third person. No praise, criticism, recommendations or speculation.
- Recommended order: document type, issuer and scope; main objectives; key measures;
  target groups, governance, funding or timeframe if stated.

Source file name: {{FILENAME}}
Material provided: {{MATERIAL_TYPE}}

<document>
{{TEXT}}
</document>

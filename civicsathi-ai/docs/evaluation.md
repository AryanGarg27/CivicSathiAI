# Evaluation protocol
Create labeled English, Hindi and Punjabi test cases. Record classification accuracy, missing-location detection, latency, duplicate precision/recall, and invalid output rate. Separate `open-weight` from `safe-fallback` samples. Compare with baseline and report all failures. Never fabricate benchmark results.

## Integration evidence — 23 October 2026

- 19 automated tests passed in the local Python virtual environment. API workflow tests use isolated databases/logs and mocked Google responses; they do not consume API quota.
- JavaScript syntax and Python module compilation checks passed.
- A real Gemma 4 / Gemini API request returned a validated `other` result for a blank synthetic image, with explicit uncertainty instead of an invented civic issue.
- Browser photo selection, consent, automatic image analysis and photo-only draft creation were also verified against the live provider. The unrelated image remained `other` with a missing location, requiring correction before submission.
- A real hosted text request categorized a streetlight complaint as `grievance` and extracted Sector 22.
- Browser verification created a clearly labeled demo case, signed into the staff dashboard, advanced received → under_review → in_progress → resolved, and confirmed the complete history in citizen tracking. The original pre-existing case remained present.
- No browser console errors were observed during that workflow.

## Image evaluation before judging

Use a held-out set of at least 30–50 consented images covering waste, road damage, water infrastructure, greenery, ambiguous scenes and unrelated images. Record ground-truth category, visible evidence, missing location, provider/model, response latency, API failure and whether human correction was needed. Measure per-category precision/recall and the rate of invented facts. Include blurry photos and daylight streetlights: visual presence alone does not prove malfunction. Evaluate Hindi/Punjabi text separately and do not claim translation or classification accuracy from integration smoke tests.

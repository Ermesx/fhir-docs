# Oracle-FHIR — PDF set for NotebookLM

**Status:** PASSED

## Limits check

| Check | Limit | Result | OK |
|---|---|---|---|
| Number of files | ≤ 50 | 5 | ✅ |
| Largest file size | ≤ 200 MB | 0.75 MB | ✅ |
| Largest word count (PDF text) | ≤ 500,000 | 86,392 | ✅ |
| Source pages covered | 191 | 191 | ✅ |

## Files

| # | File | Sections | Source pages | PDF pages | Words | MB |
|---|---|---|---|---|---|---|
| 1 | Oracle-FHIR_01_Guides.pdf | guides/01_api-access-and-fees.md – guides/09_smart-overview.md | 9 | 97 | 45,251 | 0.36 |
| 2 | Oracle-FHIR_02_R4-REST-API_part1-of-3.pdf | r4-rest-api-v32/index.html – r4-rest-api-v32/op-diagnosticreport-get.html | 64 | 387 | 86,392 | 0.73 |
| 3 | Oracle-FHIR_03_R4-REST-API_part2-of-3.pdf | r4-rest-api-v32/api-documentreference.html – r4-rest-api-v32/op-nutritionorder-id-get.html | 50 | 354 | 72,210 | 0.75 |
| 4 | Oracle-FHIR_04_R4-REST-API_part3-of-3.pdf | r4-rest-api-v32/api-observation.html – r4-rest-api-v32/op-structuredefinition-id-get.html | 59 | 429 | 80,730 | 0.7 |
| 5 | Oracle-FHIR_05_Bulk-Data.pdf | bulk-data-v10/index.html – bulk-data-v10/op-patient-export-post.html | 9 | 34 | 9,284 | 0.07 |
| | **Total** | | **191** | **1301** | **293,867** | **2.6** |

## Problems and warnings

None. All checks passed.

## Method

- Word cap used when planning: 100,000 extracted words per file (PDF text extraction counts a few percent more, so the final count is verified on the PDFs).
- Content is text only: navigation, headers/footers, scripts and images removed; tables kept as `cell | cell` lines, code kept in monospace.
- Each source page starts with its section number, title and original URL/path, and has a PDF bookmark.

# FHIR-STU3 — PDF set for NotebookLM

**Status:** PASSED

## Limits check

| Check | Limit | Result | OK |
|---|---|---|---|
| Number of files | ≤ 50 | 18 | ✅ |
| Largest file size | ≤ 200 MB | 1.83 MB | ✅ |
| Largest word count (PDF text) | ≤ 500,000 | 362,037 | ✅ |
| Source pages covered | 2555 | 2555 | ✅ |

## Files

| # | File | Sections | Source pages | PDF pages | Words | MB |
|---|---|---|---|---|---|---|
| 1 | FHIR-STU3_01_ch00-01_Front-Matter.pdf | toc.html – 1.9 | 9 | 210 | 82,744 | 0.42 |
| 2 | FHIR-STU3_02_ch02_Foundation-Module_part1-of-2.pdf | 2 – 2.32.2 | 64 | 324 | 191,657 | 0.9 |
| 3 | FHIR-STU3_03_ch02_Foundation-Module_part2-of-2.pdf | 2.32.3 – 2.48.8 | 112 | 292 | 171,105 | 0.68 |
| 4 | FHIR-STU3_04_ch03_FHIR-Linked-Data-Module.pdf | 3 – 3.3 | 4 | 12 | 13,185 | 0.04 |
| 5 | FHIR-STU3_05_ch04_Terminology-Module_part1-of-4.pdf | 4 – 4.2.13.510 | 710 | 551 | 362,037 | 1.59 |
| 6 | FHIR-STU3_06_ch04_Terminology-Module_part2-of-4.pdf | 4.2.13.511 – 4.3.1.371 | 320 | 675 | 361,924 | 1.83 |
| 7 | FHIR-STU3_07_ch04_Terminology-Module_part3-of-4.pdf | 4.3.1.372 – 4.3.2.40 | 319 | 576 | 352,655 | 1.68 |
| 8 | FHIR-STU3_08_ch04_Terminology-Module_part4-of-4.pdf | 4.3.2.41 – 4.11.9 | 231 | 358 | 282,758 | 1.13 |
| 9 | FHIR-STU3_09_ch05_Conformance-Module.pdf | 5 – 5.9.9 | 65 | 178 | 110,304 | 0.47 |
| 10 | FHIR-STU3_10_ch06_Security-and-Privacy-Module.pdf | 6 – 6.4.11 | 26 | 53 | 33,123 | 0.16 |
| 11 | FHIR-STU3_11_ch07_Implementation-Support-Module.pdf | 7 – 7.15.5 | 39 | 96 | 70,374 | 0.29 |
| 12 | FHIR-STU3_12_ch08_Administration-Module.pdf | 8 – 8.24.9 | 181 | 318 | 147,314 | 0.87 |
| 13 | FHIR-STU3_13_ch09_Clinical-Summary-Module.pdf | 9 – 9.11.11 | 88 | 137 | 78,643 | 0.4 |
| 14 | FHIR-STU3_14_ch10_Diagnostic-Medicine-Module.pdf | 10 – 10.8 | 86 | 261 | 172,500 | 0.76 |
| 15 | FHIR-STU3_15_ch11_Medications-Module.pdf | 11 – 11.8.3 | 61 | 101 | 56,738 | 0.29 |
| 16 | FHIR-STU3_16_ch12_Workflow-Module.pdf | 12 – 12.25.10 | 128 | 204 | 117,080 | 0.58 |
| 17 | FHIR-STU3_17_ch13_Financial-Module.pdf | 13 – 13.11.10 | 72 | 175 | 92,570 | 0.44 |
| 18 | FHIR-STU3_18_ch14_Clinical-Reasoning.pdf | 14 – 14.6.10 | 40 | 129 | 53,548 | 0.29 |
| | **Total** | | **2555** | **4650** | **2,750,259** | **12.8** |

## Problems and warnings

None. All checks passed.

## Method

- Word cap used when planning: 300,000 extracted words per file (PDF text extraction counts a few percent more, so the final count is verified on the PDFs).
- Content is text only: navigation, headers/footers, scripts and images removed; tables kept as `cell | cell` lines, code kept in monospace.
- Each source page starts with its section number, title and original URL/path, and has a PDF bookmark.

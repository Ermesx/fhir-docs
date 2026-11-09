# fhir-docs

FHIR documentation kept in one place: the official HL7 specification (per FHIR version) and implementation documentation published by EHR vendors (Epic, Meditech, Oracle Health and others). For each source the repo holds the original input and text-only PDFs generated from it, which are loaded into NotebookLM so the whole corpus can be queried like a wiki.

## Where to find the documentation

| Folder | Contents |
|--------|----------|
| `official-docs/` | Official HL7 FHIR documentation, one folder per FHIR version (e.g. `fhir-r4/`) |
| `vendor-docs/` | EHR vendor FHIR documentation, one folder per vendor and version |

Each source folder contains the original input (ZIP or other format), the generated PDFs, and a `REPORT.md` listing the PDFs with page and word counts.

## Ready-to-use notebooks

| Source | Notebook |
|--------|----------|
| FHIR R4 (v4.0.1) | [NotebookLM](https://notebook.google.com/notebook/dcef5592-1942-40e0-aa70-d0ecf271b001) |

## Adding a new source

See [AGENTS.md](AGENTS.md) for naming rules and how to generate the PDFs.

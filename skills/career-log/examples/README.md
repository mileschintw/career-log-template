# Examples

A fictional person, Alex Doe, recorded the way this skill records a real one. Everything here is invented: names, employers, numbers and links.

**This folder is not part of anyone's log.** No mode reads it as the user's facts, cites it, or copies a fact from it ([docs/adr/0002](../../../docs/adr/0002-examples-live-in-the-engine.md)). Use it only to:

- see what a finished entry, profile and direction look like before writing the user's own;
- build `resume.tex`, the setup check's resume ([SETUP.md](../../../SETUP.md) step 6).

A user's first resume starts from the blank layout [../assets/resume-blank.tex](../assets/resume-blank.tex), never from `resume.tex` here.

| File | Shows |
|---|---|
| [entries/2025-06-northwind-freight-internship.md](entries/2025-06-northwind-freight-internship.md) | A consolidated entry: provenance on every fact, attribution, a metric with its caveat, a `GAP:`, a conflict, past phrasings |
| [profile.md](profile.md) | Static facts with sources |
| [direction.md](direction.md) | Targets, constraints, languages and personal writing preferences |
| [resume.tex](resume.tex) | A one-page resume on the r/EngineeringResumes template that passes `tools/resume.py` |

Only one entry is included to keep the example short. In a real log, the resume's teaching-assistant and Tidepool lines would each trace to their own entry, as `profile.md`'s GAP notes.

# Academic profile update — v1.3

Date: 2026-10-01.

## Scope

- Use the author-confirmed Poster presentation category for NeurIPS 2026; retain the NeurIPS 2025 Spotlight distinction.
- Expand About into biography, education, selected publications, earlier research, selected honors, academic service, and public contact sections.
- Use the supplied older CV only as source material for selected historical details. Current education uses the author's newer information. Do not include the old CV file, its old contact details, obsolete in-progress appointments, review scores, or older publication list.
- Do not attach the anonymous conference manuscript. Retain the clearly labeled earlier public preprint.
- Keep preview mode and existing Pages deployment settings unchanged.

## Build and checks

Run `python3 tools/build.py` followed by `python3 tools/check_site.py`.
The shared builder is preserved in `tools/_site_builder.py`; `tools/build.py` remains the supported entry point and adds the profile from `content/profile.json` and `content/site.json`.

Local checks passed: 11 HTML pages, 219 local references, and 44 page/viewport combinations at 1440, 768, 390, and 320 pixels. No horizontal overflow or page-script errors were found. Checked the mobile menu and public contact links; confirmed no CV-download link was generated.

Visual checks used local Chromium with inlined copies of the site assets, not a live-site network test. Safari, physical devices, external destinations, and the public website were not tested in that browser session. GitHub deployment success must be checked separately after pushing.

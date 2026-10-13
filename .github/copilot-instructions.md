# AminoMatch project instructions

## Setup completed

- [x] Project instructions created.
- [x] Requirements: essential-amino-acid exploration, phases 1, 2 and 3.
- [x] Scaffold: Flask/Python, vanilla HTML/CSS/JavaScript, CSV dataset, unittest.
- [x] Customization: meal builder, food library, both algorithm labs and roadmap.
- [x] Extensions: no additional editor extensions required.
- [x] Verification: 29 automated tests pass; Python compilation and diagnostics clean.
- [x] Tasks: AminoMatch: Run and AminoMatch: Test created and executed.
- [x] Local browser checks: meal edits/undo, queue, expressions, tree traversal, binary search, BFS, food profiles and mobile overflow.
- [x] Documentation: setup, phase mapping, formulas, dataset contract and limitations in README.

## Development conventions

- Python entry point: app.py. Use .venv/Scripts/python.exe on this Windows workspace.
- Run tests with `python -m unittest discover -s tests -v` using the virtual environment.
- Keep the educational structures explicit in structures.py. Browser controls must invoke the Python algorithms, not simulate them in JavaScript.
- Keep nutrition validation and scoring in nutrition.py; route/session handling in app.py.
- Phase 3 includes linear search, stable merge sort for food analysis and an explicit max-heap priority queue with graphical traces. Phase 4 remains planned until requirements are provided.
- Starter nutrition data is illustrative, not verified. Keep that disclosure visible.
- Reference: WHO/FAO/UNU 2007 adult amino-acid scoring pattern, mg/g protein.
- Include cysteine/tyrosine in combined reference groups; exclude them from the nine-essential-amino-acid total.
- Never equate reference-pattern coverage with daily intake, digestibility, DIAAS or PDCAAS.
- Preserve atomic CSV imports, finite-number validation, escaped user text and no-eval arithmetic.
- State is browser-session-isolated and in-memory. Server restart clears it; no persistence is promised.
- Keep the development server local-only with debug mode off. No public deployment is configured.
- No Node build, external CDN, remote font or external image dependencies are needed.
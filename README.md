# AminoMatch

**Beyond the protein count.** A Python data-structures project that explores essential amino acids in individual foods and meals. Phases 1 and 2 are implemented; phases 3 and 4 are reserved for later requirements.

## Run locally

Requires Python 3.11+ (developed with Python 3.13). Flask serves both the website and API; no Node.js or frontend build is required.

1. Create a virtual environment with `python -m venv .venv`.
2. Install dependencies with `.venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows.
3. Start with `.venv\Scripts\python.exe app.py`.
4. Visit **http://127.0.0.1:5000**. Stop the server with Ctrl+C.

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

The current workspace already has a configured virtual environment. In VS Code, use **Terminal → Run Task → AminoMatch: Run**. The test task runs the standard-library unittest suite. No debugger or extra editor extensions are required.

## Website

- **Meal builder:** add edible serving weights, remove portions, undo changes, and inspect nine amino acid reference groups, limiting group, essential amino acid total and protein total.
- **Food library:** searchable/filterable individual food profiles, CSV template download and validated dataset replacement.
- **Linear structures:** linked-list nodes, stack-backed undo, FIFO meal analysis, infix/postfix conversion and iterative/recursive operation counts.
- **Structure visualizer:** editable singly linked practice list (append, indexed insert/delete, case-insensitive search, clear and restore), meal undo stack (push/pop), and meal analysis queue (enqueue/dequeue with front/rear markers).
- **Trees & graphs:** binary food hierarchy, three traversal orders, exact-name binary-search trace, adjacency lists and BFS.
- **Roadmap:** requirements mapping and clearly marked Phase 3/4 placeholders.
- **How it works:** formulas, adult reference values and limitations.

### A short demonstration

1. Select **Try lentils + brown rice**. This replaces the meal with 100 g of each and pushes the old meal to the undo stack.
2. Remove one portion and observe the lowest-coverage group. Use **Undo** to restore it.
3. Queue a meal, change it, and queue again. In Phase 1, process the jobs in order; each retains its original snapshot.
4. Convert `(9 + 2.6) * 2`: postfix `9 2.6 + 2 *`, result `23.2`.
5. In Phase 2, change traversal order and search for `Lentils (cooked)`. Change the BFS start node.
6. Download the CSV template, edit it and import it from the Food library. Invalid imports leave all previous state unchanged.

In **Structure visualizer**, select **Singly linked practice list** to run list operations. Indices start at zero; search returns the first match and highlights the visited nodes. Practice values are limited to 80 characters and the list to 250 nodes. This list starts with food names but is independent of the nutrition dataset. Clear affects only the practice list; restore reloads the current food names. A dataset replacement also resets the practice list.

Select **Meal undo stack** to add a 100 g portion and push the previous meal, then pop to restore it (LIFO). Select **Meal analysis queue** to enqueue the current meal snapshot, change the meal, and enqueue again. **Dequeue & analyze front** processes the oldest saved snapshot (FIFO); the result appears below the diagram. Queue capacity is 20 meals. All operations run in Python and remain isolated to the browser session.

## Phase requirements and implementations

| Phase | Requirement | Implementation |
| --- | --- | --- |
| 1 | Dataset input | UTF-8 CSV, strict schema and atomic validation in [nutrition.py](nutrition.py) |
| 1 | Linked list | `Node`, `LinkedList`; authoritative food storage |
| 1 | Stack | Linked `Stack`; meal history, operator stack and postfix value stack |
| 1 | Queue | Linked `Queue`; saved-meal FIFO analysis and BFS frontier |
| 1 | Infix / postfix | Shunting-yard conversion with token trace and postfix evaluation |
| 1 | Basic efficiency | Iterative and recursive sum, additions/calls and time/space explanation |
| 2 | Binary tree | `BinarySearchTree`, alphabetic food hierarchy |
| 2 | Tree traversal | Inorder, preorder, postorder |
| 2 | Binary search | Search a pre-sorted random-access array; low/mid/high trace |
| 2 | Graph representation | Undirected food-pair adjacency lists |
| 2 | One graph traversal | Breadth-first search; queue plus visited set |
| 3–4 | Not yet supplied | Roadmap placeholders only |

Algorithms are in [structures.py](structures.py), scoring and validation in [nutrition.py](nutrition.py), and API integration in [app.py](app.py). All demonstrations invoke Python endpoints; the browser renders the results.

### Complexity notes

- Linked append, linked stack push/pop and queue enqueue/dequeue: O(1). Food lookup: O(n).
- Practice-list insertion/deletion at the head: O(1); indexed insertion/deletion and linear search: O(n) worst case. Serializing or drawing a complete structure takes O(n), separate from pointer operations.
- Saving or restoring a meal state involves up to O(m) meal data, separate from stack pointer operations. History is capped at 200 edits.
- Meal analysis with linked-list food lookups: O(mn), where m is portions and n is foods; amino-acid count is fixed.
- Infix conversion/evaluation: O(t) time and O(t) space for t tokens. The displayed full output trace can occupy O(t²) space; expressions are capped at 200 characters.
- Iterative/recursive sum: O(n) time; O(1)/O(n) auxiliary space. Recursion uses an index, not repeated slicing. The CSV limit keeps recursion well below Python's usual stack limit.
- Binary search: O(log n) comparisons after O(n log n) sorting and O(n) array materialization. Searching the linked list directly would not provide efficient midpoint access.
- Median-first BST insertion produces a balanced initial hierarchy; it is not AVL/self-balancing. Construction is O(n log n), traversal O(n); ordinary BST insertion is O(h), worst-case O(n).
- Pair graph construction: O(n²). Edge rule: 100 g of each food together scores more than 5 percentage points above the weaker individual food. This does not guarantee mutual improvement or complete reference coverage.
- BFS: O(V + E) time, O(V) additional visited/queue space. Disconnected foods outside the starting component are not visited.

## Nutrition model and honesty

**The 12 starter foods contain plausible illustrative values, not verified food-composition measurements. Do not use them for dietary decisions.** Uploaded values are also not independently verified by the application.

Dataset quantities refer to **100 g edible food in the named preparation state**. Protein is in **grams**, amino acids in **milligrams**. Raw and cooked foods are not interchangeable.

- Serving amount (mg) = source amount (mg per 100 g) × serving weight (g) / 100.
- Group coverage (%) = total group amount (mg) / [total protein (g) × reference value (mg/g)] × 100.
- Pattern score = lowest group coverage. The “Meets the reference pattern” label requires every group to meet its target; a rounded displayed percentage does not determine the label.
- The essential amino acid total sums only the nine essential amino acids. Cysteine and tyrosine contribute to the two combined reference groups, but not to that total.

Reference: **WHO/FAO/UNU (2007), Protein and amino acid requirements in human nutrition, WHO Technical Report Series 935**, adult scoring pattern: histidine 15, isoleucine 30, leucine 59, lysine 45, methionine+cysteine 22, phenylalanine+tyrosine 38, threonine 23, tryptophan 6 and valine 39 mg/g protein.

This is **not** daily-intake coverage, DIAAS, PDCAAS, a digestibility measure, or a clinical assessment. Doubling the same food doubles its amino acid amounts but leaves its proportional score unchanged. Complementary foods do not necessarily need to be eaten in the same meal. Replace the illustrative dataset with verified measurements and retain source identifiers in a separate research record before scientific use.

### CSV input contract

Use the exact column names and ordering in [data/foods.csv](data/foods.csv). Fields: `id`, `name`, `category`, `protein_g`, followed by eleven `_mg` amino-acid fields (nine essential plus cysteine and tyrosine).

- Maximum 250 food rows and 1 MB request size.
- Unique lowercase alphanumeric/hyphen IDs (1–50 characters); unique case-insensitive food names (1–80); category (1–40).
- Protein greater than zero and no more than 100 g per 100 g food.
- All amino values present, finite and nonnegative; recorded zero is valid, missing data is not zero.
- Total recorded amino-acid mass must not exceed protein mass by more than 5%, allowing rounding.
- Invalid headers, duplicate foods, malformed rows and invalid UTF-8 are rejected.
- Imports **replace** the dataset and clear meal/history/queue only after successful validation; confirmation is requested first. The source CSV on disk is never overwritten.

## Test

Run `.venv\Scripts\python.exe -m unittest discover -s tests -v` or the **AminoMatch: Test** task.

Tests cover structural invariants, empty cases, expression errors, traversal order, binary search, cyclic/disconnected BFS, serving scaling, combined groups, CSV validation, API errors, undo, queue snapshots and browser-session isolation.

## Scope and persistence

This is a **local educational prototype**. Browser sessions hold separate in-memory datasets, meals, history and queues. Page refresh preserves a session while the server is running; restarting the server resets everything. Up to 64 recently used sessions are retained; the oldest is evicted at capacity. Clearing cookies also starts a fresh workspace. There is no database, authentication, background worker or deployment configuration. Queue jobs run when you press **Process next**, not automatically.

The Flask development server binds only to 127.0.0.1 with debug mode off. Do not expose it as a public production service. The frontend uses local CSS/JavaScript and CSS illustrations, without third-party CDNs or external image assets.
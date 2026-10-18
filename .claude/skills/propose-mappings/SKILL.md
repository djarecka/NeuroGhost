---
name: propose-mappings
description: Propose cross-schema mappings for the NeuroGhost registry with your own model, or review an existing mapping file (e.g. a "Propose Mappings" PR), and open/update a PR containing only the mappings the user approved. Use when the user wants to map/align terms between registered schemas ("map aind properties to bids", "find which dandiset classes match bbqs") or to review proposed mappings ("review the mappings in PR 130").
---

# Propose mappings (user-approved)

Produce a reviewed mapping file — `mappings/*.sssom.tsv`, format in
`neuro_ghost/mappings.py` — for two schemas already in the registry, judged by
you and **approved row by row by the user**, then open a PR with it. Every
row in the PR is a mapping the user accepted, recorded under their GitHub
login. Nothing is published until a maintainer merges the PR.

Work in batches and keep the user in control: you propose, they decide.

Two modes — ask which if it isn't clear:

- **New mappings** (sections 1–6): generate candidates, judge, approve,
  write a new file, open a PR.
- **Review a mapping file** (section 7): the rows already exist — typically
  a *Propose Mappings* PR, where every row is `PROPOSED` from embeddings —
  and you judge them, the user decides, and the same file is updated.

## 1. Set up

- Run from the repository root, on an up-to-date `main`
  (`git fetch upstream && git switch -c mappings/<short-name> upstream/main`, or
  `origin` if they work directly on sensein/NeuroGhost).
- `gh auth status` must show a logged-in account. Get the login with
  `gh api user --jq .login` — it is the `author_id` and `reviewer_id` of
  every row. Never type it in by hand or use anyone else's.
- Python with `requirements.txt` installed, plus `sentence-transformers`
  for the candidate step (`pip install sentence-transformers`; it isn't in
  `requirements.txt`). Check with
  `python -c "import sentence_transformers"` and install it if missing.
- Ask which **subject** and **object** schemas (source labels as in
  `data/registry.json` → `sources[].label`, e.g. `aind`, `bids`, `asset`;
  either may be `all`) and whether to map **properties**, **classes**, or
  **all**. Suggest starting small (one pair of schemas, classes first, or a
  subset of classes) — `all` can mean hundreds of rows to approve.

## 2. Candidates

Generate candidates with the free embedding model into a scratch file, not
into `mappings/`:

```bash
python neuro_ghost/propose_mappings.py <subject> <object> --kind <properties|classes> \
  --top-k 3 --min-score 0.5 --author "$LOGIN" --out /tmp/candidates.sssom.tsv
```

These are only leads. You may also add a better target from the object
schema that embeddings missed — look it up in `data/registry.json`.

## 3. Judge (you)

For each subject entity, read both sides' names and definitions in
`data/registry.json` (and the class they belong to), then decide:

- `skos:exactMatch` — same meaning, interchangeable
- `skos:closeMatch` — nearly the same; fine for most data translation
- `skos:broadMatch` / `skos:narrowMatch` — the object is broader / narrower
- `skos:relatedMatch` — related, not substitutable
- none — not a match (drop it; don't show it unless asked)

Give each a confidence (0–1) and **one sentence** of reasoning. Be strict:
same name with different meaning (e.g. `description` of a Dandiset vs of
an Activity) is not a match.

## 4. Approve (the user)

Show **at most ~10 rows at a time** as a compact table:
`# · subject · relation · object · confidence · reason`. Ask the user to
answer per row: **accept**, **reject**, **change relation**, or **skip**
(e.g. "1-4 accept, 5 reject, 6 narrowMatch, rest skip"). Continue until
the candidates are done or the user stops. Never mark a row accepted
without their explicit answer.

Include only accepted rows in the file. Rejected rows are included only if
the user asks for that (as `REJECTED`, which records "this is not a match").

## 5. Write the mapping file

`mappings/<YYYY-MM-DD>_llm_<subject>__<object>_<kind>.sssom.tsv`:

```
# mapping_set_id: <file name without .sssom.tsv>
# mapping_date: <YYYY-MM-DD>
# mapping_tool: llm/<your exact model id>
# mapping_justification: semapv:ManualMappingCuration
# author_id: <login>
subject_id	predicate_id	object_id	confidence	review_status	reviewer_id	review_date	comment
aind:Subject.sex	skos:exactMatch	bids:Columns.sex	0.95	ACCEPTED	<login>	<YYYY-MM-DD>	<your one-sentence reason>
```

Tab-separated; references are `source:Class` or `source:Class.prop`
exactly as the candidates file wrote them. Then validate:

```bash
python neuro_ghost/mappings.py validate mappings/<file>
```

Fix anything it reports before going on.

## 6. Open the PR — ask first

Show the user a summary (counts, the file path) and **ask before**
committing, pushing, or opening the PR. Then:

```bash
git add mappings/<file>
git commit -m "Mappings: <subject> → <object> (<kind>), approved by <login>"
git push -u origin <branch>
gh pr create --base main --title "Mappings: <subject> → <object> (<kind>)" --body "<summary: how many, method llm/<model>, all approved by <login>>"
```

(From a fork: `--repo sensein/NeuroGhost --head <login>:<branch>`.)

The PR's **Mapping Check** verifies the file, that every reference exists,
and that every accepted/rejected row names an author of the PR as reviewer.

## 7. Review mode: an existing mapping file

1. Get the file. For a PR: `gh pr checkout <number> --repo sensein/NeuroGhost`
   (find it with `gh pr list --repo sensein/NeuroGhost --search "Proposed mappings"`).
   For a file already on `main`, branch off `main` as in section 1.
2. Judge each `PROPOSED` row as in section 3 — including whether the
   predicate is right (embeddings always write `skos:closeMatch`).
3. Approve in batches as in section 4. For each answer, edit that row in
   place: `review_status` → `ACCEPTED` / `REJECTED`, `reviewer_id` → the
   login from `gh api user --jq .login`, `review_date` → today, `comment` →
   your one-sentence reason; a changed relation goes in `predicate_id`.
   Skipped rows stay `PROPOSED`. Don't touch rows that are already reviewed.
4. `python neuro_ghost/mappings.py validate <file>`, show the user a summary
   (accepted / rejected / still proposed), and **ask before** committing and
   pushing. Commit with their identity, then `git push`.
   - On a bot-opened PR this adds their commit to it; the Mapping Check
     accepts their reviews because they authored a commit in the PR.
   - If they can't push to that branch (no write access to
     sensein/NeuroGhost), push to a branch on their fork and open a new PR
     with the reviewed file instead.

# file: src/cli/dev/report/git_changes.notes.md
You are reviewing a Git repository's current changes through an interactive, multi-step report workflow (initial manifest first, followed by incremental file diff batches).

### Tasks

1. Analyze all modified, deleted, renamed, and untracked files.
2. Decide which files should be staged together.
3. Group files into logical commits.
4. Suggest a short, clear commit message for each commit.
5. Explain briefly why each group belongs together.
6. Identify unrelated changes that should be separated.
7. Generate stage + commit command blocks for each commit group.
8. Generate one final sequential command block that applies all commits in the correct order.

### Rules

* Do not modify files.
* Do not execute Git operations.
* Only analyze the provided repository state and generate a commit strategy.
* Do not invent files or changes that are not present in the report.
* Do not combine unrelated changes into the same commit.
* Prefer small, focused commits with meaningful commit messages.
* Preserve logical dependency order between commits when relevant.
* Include only files that belong to each commit group in its staging commands.
* The final command sequence must be directly pasteable into a terminal.
* **🚨 Unignored File Warning:** If you notice tracked or staged files that should clearly belong in `.gitignore` (e.g., `*.sqlite`, `.env`, logs), immediately **halt** the commit planning workflow, display a prominent **🚨 ALARM** warning, and **instruct the user to take control** (manually update `.gitignore` and untrack the file themselves) rather than attempting to modify files or decide for them.
* **Temporary Changes Check:** If temporary or testing changes are detected, ask the user whether to include or exclude them before generating the commit plan.
* **Do NOT generate the final COMMIT PLAN yet.** If you need to see more file diffs to understand the changes, reply ONLY with the comma-separated list of missing file IDs (e.g., `3,12,19`) and nothing else. Only generate the COMMIT PLAN when you have inspected all necessary files and explicitly state you are ready.

### Additional Guidance

* The initial report contains the unified file manifest. Request file IDs interactively from the script to load diffs step by step.
* Keep requests concise and focused on the active commit group.
* When specifying or suggesting file IDs for the CLI prompt, always provide them strictly as a clean, minimal comma-separated list of numbers (e.g., `1,5,8`).

* **File Status Legend:** `M` = Modified, `A` = Added, `D` = Deleted, `R` = Renamed, `U` = Untracked.

If information is insufficient:

* Do not guess.
* Ask only for the minimum missing file contents.
* Keep requests concise.

### Preferred Output

#### COMMIT PLAN

##### 1. <short commit message>

**Files**

* path/file.py
* path/file.py

**Reason**

<one concise sentence>

**Stage + Commit**

```bash
git add ... && \
git commit -m "..."
```
# Manifest and helper contract

Python 3.11+ and the standard library only. The helper never uses the network,
spawns a process, invokes Docker, downloads a JAR, or executes manifest strings.
The agent researches release notes using its own authorized tools and provides
the evidence. Start from [manifest-template.json](manifest-template.json) in this
installed skill. Its placeholders are intentionally blocked: replace them with
researched facts and actual pin snippets before use. `examples/manifest.json` in
the source repository is separate synthetic demonstration data, not a real
release recommendation.

## JSON schema, version 1

The root has exactly `schema_version: 1` and a nonempty `components` array. Each
component has these required fields; unknown fields are rejected to catch typos.

| Field | Meaning |
| --- | --- |
| `id` | Unique lowercase kebab-case identifier |
| `kind` | `minecraft-plugin` or `docker-image` |
| `current_version` / `candidate_version` | Exact upstream labels, not automatically compared or sorted |
| `artifact` | Candidate identity and integrity fields below |
| `review` | Research and decision fields below |
| `edits` | Nonempty array of `{ "path", "before", "after" }` exact-text edits |

For a plugin, `artifact` is `{ "url", "sha256", "verification", "evidence" }`.
URL must be HTTPS without embedded credentials; SHA-256 is 64 lowercase hex
characters. Both must appear in the proposed replacement text. Verify the
repository actually enforces its checksum pin.

For an image, `artifact` is `{ "reference", "platform", "digest_kind",
"verification", "evidence" }`. `reference` must end in `@sha256:<64 lowercase
hex>` and appear in replacement text. `platform` is explicit, e.g. `linux/amd64`
or `linux/arm64/v8`; `digest_kind` is `index` or `manifest`. The helper checks
shape only, not existence in a registry or full Docker reference grammar.

`verification` is `verified` or `unverified`; `evidence` describes the exact
verification and source. These are assertions by the researcher. Do not claim
that the helper authenticates them or that a hash alone proves trustworthiness.

`review` contains all of:

- `release_notes`: nonempty `[{ "url": "https://...", "summary": "..." }]`.
  Include intervening changes, source links, and important migration details.
- `compatibility`: nonempty `[{ "target": "...", "result": "pass|fail|unknown",
  "evidence": "..." }]`. Cover all relevant runtime and dependency checks.
- `breaking_changes`: string array; use `[]` only after reviewing the upgrade path.
- `migrations`: string array; required to be nonempty when breaking changes exist.
  Describe necessary work, its ordering, and whether it is already completed.
- `tests`: nonempty string array of checks and their actual status. Explicitly
  label planned/pending checks; the helper never runs them.
- `rollback`: nonempty string array including state backup/restore caveats.
- `decision`: `ready` or `blocked`, referring only to proposed local pin edits.
- `blockers`: string array of unresolved issues.

Unknown/failing compatibility, unverified artifacts, explicit blockers, a blocked
decision, or breaking changes without migrations produce a blocked plan. The
report and diff are still generated for review; applying it is refused. This is
a structural gate: the agent must judge whether the entries are meaningful and
whether migration work or pending tests should block the requested action.

## Exact edits

Use repo-relative POSIX paths, with each `before` matching exactly once in its
file. Include enough surrounding text to disambiguate repeated versions. Each
`after` must be uniquely reversible as well. Multiple nonoverlapping edits can
share a file. These snippets are literal text, not regex or executable code.
YAML/Compose/env/Dockerfile/JSON are handled as UTF-8 text without reformatting;
syntax-specific validation is the agent's responsibility. Binary JAR replacement
and automatic configuration/data migrations are deliberately unsupported.

The helper refuses absolute/traversing paths, VCS internals, symlink components,
hard-linked targets, binary/NUL-containing text, duplicate JSON keys, unknown
fields, ambiguous/overlapping/no-op replacements, and input or resulting target
files over 1 MiB (UTF-8 bytes). Plans must fit the 8 MiB JSON input limit; split
large batches into smaller plans.
It preserves bytes outside the edits, line endings, and file mode. File ownership,
ACLs, extended attributes, and hard links are not preserved by atomic replacement;
use it on ordinary repository files, never special/live system files.

## Commands and safety limits

```sh
python3 <skill-dir>/scripts/update.py plan --root <repo> --manifest <manifest.json> --out <new-plan.json>
python3 <skill-dir>/scripts/update.py apply --root <repo> --plan <plan.json>
python3 <skill-dir>/scripts/update.py rollback --root <repo> --plan <plan.json>
python3 <skill-dir>/scripts/update.py sha256 <local-file> --expected <sha256>
```

Plan creates two new files: the requested JSON and a same-stem `.md` report.
Existing outputs are never overwritten. Exit codes: `0` success/ready, `1`
validation or I/O error, `2` a successfully generated blocked plan. JSON and
reports contain URLs, evidence, and changed lines; keep them private if these
contain private project details. Full file contents are not stored, but a changed
line or chosen snippet can still contain a secret. Sanitize before publishing.

Apply/rollback revalidate the embedded manifest and verify whole-file SHA-256
before writing. Already-applied/reverted files are skipped. Files changed since
planning are refused, including unrelated edits. Regenerate the plan instead of
overwriting those changes. Atomic replacement protects each file individually;
there is no multi-file transaction, concurrent-writer lock, or hostile-filesystem
security boundary. Use a quiet, trusted checkout. After an interrupted write,
inspect all files; unchanged planned states can be safely re-run or reversed.
Rollback restores textual pins only, never databases, worlds, or volumes.

Plans are review artifacts, not signed approvals. Never execute a plan received
from an untrusted source without reviewing its exact target root and every edit.

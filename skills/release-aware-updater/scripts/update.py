#!/usr/bin/env python3
"""Offline, exact-text pin planning. No network, shell, package install, or deployment."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from urllib.parse import urlsplit

LIMIT = 1024 * 1024
JSON_LIMIT = 8 * LIMIT
HEX = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[^\s@]+@sha256:[0-9a-f]{64}\Z")


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def fields(obj, required, optional=()):
    require(isinstance(obj, dict), "expected an object")
    require(set(required) <= set(obj), f"missing fields: {sorted(set(required) - set(obj))}")
    require(set(obj) <= set(required) | set(optional), f"unknown fields: {sorted(set(obj) - set(required) - set(optional))}")


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty string required")
    require("\x00" not in value, f"{label}: NUL is not allowed")
    return value


def strings(value, label, nonempty=False):
    require(isinstance(value, list), f"{label}: array required")
    require(not nonempty or bool(value), f"{label}: at least one entry required")
    for item in value:
        string(item, label)


def https(value):
    string(value, "source URL")
    url = urlsplit(value)
    require(url.scheme == "https" and url.hostname and not url.username and not url.password,
            "source URLs must be HTTPS without embedded credentials")
    require(not any(c.isspace() for c in value), "source URL contains whitespace")


def relative(value):
    string(value, "path")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in value), "path contains control characters")
    p = PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts and "\\" not in value,
            "paths must be relative POSIX paths without traversal")
    require(p.parts and p.as_posix() == value and not any(":" in x for x in p.parts),
            "path must be normalized and portable")
    require(not any(x in {".git", ".hg", ".svn"} for x in p.parts), "VCS internals cannot be edited")
    return p


def validate(manifest):
    fields(manifest, {"schema_version", "components"})
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1, "unsupported manifest schema")
    components = manifest["components"]
    require(isinstance(components, list) and components, "components must be a nonempty array")
    ids, blockers = set(), []
    for c in components:
        fields(c, {"id", "kind", "current_version", "candidate_version", "artifact", "review", "edits"})
        name = string(c["id"], "id")
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), "id must use lowercase kebab-case")
        require(name not in ids, f"duplicate component: {name}")
        ids.add(name)
        for key in ("current_version", "candidate_version"):
            string(c[key], key)
        a = c["artifact"]
        if c["kind"] in ("artifact", "minecraft-plugin"):
            fields(a, {"url", "sha256", "verification", "evidence"})
            https(a["url"])
            require(isinstance(a["sha256"], str) and HEX.fullmatch(a["sha256"]), "artifact SHA-256 must be 64 lowercase hex characters")
            required_pins = [a["url"], a["sha256"]]
        elif c["kind"] == "docker-image":
            fields(a, {"reference", "platform", "digest_kind", "verification", "evidence"})
            require(isinstance(a["reference"], str) and IMAGE.fullmatch(a["reference"]), "Docker candidate must include @sha256:<64 lowercase hex>")
            require(a["digest_kind"] in {"index", "manifest"}, "digest_kind must be index or manifest")
            require(isinstance(a["platform"], str) and re.fullmatch(r"[a-z0-9]+/[a-z0-9_]+(?:/[a-z0-9]+)?", a["platform"]), "platform must be explicit, e.g. linux/amd64")
            required_pins = [a["reference"]]
        else:
            raise Invalid(f"unsupported kind: {c['kind']}")
        require(a["verification"] in {"verified", "unverified"}, "verification must be verified or unverified")
        string(a["evidence"], "artifact evidence")
        if a["verification"] != "verified":
            blockers.append(f"{name}: artifact integrity/source is unverified")
        r = c["review"]
        fields(r, {"release_notes", "compatibility", "breaking_changes", "migrations", "tests", "rollback", "decision", "blockers"})
        require(isinstance(r["release_notes"], list) and r["release_notes"], "release_notes must be nonempty")
        for note in r["release_notes"]:
            fields(note, {"url", "summary"})
            https(note["url"])
            string(note["summary"], "release-note summary")
        require(isinstance(r["compatibility"], list) and r["compatibility"], "compatibility must be nonempty")
        for check in r["compatibility"]:
            fields(check, {"target", "result", "evidence"})
            string(check["target"], "compatibility target")
            string(check["evidence"], "compatibility evidence")
            require(check["result"] in {"pass", "fail", "unknown"}, "compatibility result must be pass, fail, or unknown")
            if check["result"] != "pass":
                blockers.append(f"{name}: {check['target']} is {check['result']}")
        for key in ("breaking_changes", "migrations", "tests", "rollback", "blockers"):
            strings(r[key], key, nonempty=key in {"tests", "rollback"})
        if r["breaking_changes"] and not r["migrations"]:
            blockers.append(f"{name}: breaking changes need migration steps")
        require(r["decision"] in {"ready", "blocked"}, "decision must be ready or blocked")
        if r["decision"] == "blocked":
            blockers.append(f"{name}: reviewer decision is blocked")
        blockers.extend(f"{name}: {item}" for item in r["blockers"])
        require(isinstance(c["edits"], list) and c["edits"], "edits must be nonempty")
        for edit in c["edits"]:
            fields(edit, {"path", "before", "after"})
            relative(edit["path"])
            string(edit["before"], "before")
            string(edit["after"], "after")
            require(edit["before"] != edit["after"], "no-op edit")
        for pin in required_pins:
            require(any(pin in e["after"] for e in c["edits"]), "candidate artifact pins must appear in edits")
    return blockers


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path):
    require(path.stat().st_size <= JSON_LIMIT, "JSON file is too large")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_target(root, name):
    p = root
    for part in relative(name).parts:
        p = p / part
        require(not p.is_symlink(), f"symlink target refused: {name}")
    info = p.stat()
    require(stat.S_ISREG(info.st_mode), f"not a regular file: {name}")
    require(info.st_nlink == 1, f"hard-linked file refused: {name}")
    require(info.st_size <= LIMIT, f"target exceeds 1 MiB: {name}")
    data = p.read_bytes()
    require(b"\x00" not in data, f"binary file refused: {name}")
    data.decode("utf-8")
    return p, data, stat.S_IMODE(info.st_mode)


def replace_exact(text, edits, reverse=False):
    spans = []
    for e in edits:
        old, new = (e["after"], e["before"]) if reverse else (e["before"], e["after"])
        require(text.count(old) == 1, f"pin must match exactly once: {e['path']}")
        start = text.index(old)
        spans.append((start, start + len(old), new))
    spans.sort()
    for left, right in zip(spans, spans[1:]):
        require(left[1] <= right[0], "overlapping pin replacements")
    for start, end, new in reversed(spans):
        text = text[:start] + new + text[end:]
    return text


def grouped(manifest):
    groups = {}
    for c in manifest["components"]:
        for e in c["edits"]:
            groups.setdefault(e["path"], []).append(e)
    return dict(sorted(groups.items()))


def make_diff(name, before, after):
    lines = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                 fromfile=f"a/{name}", tofile=f"b/{name}", n=0)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def encode_plan(plan):
    text = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    require(len(text.encode("utf-8")) <= JSON_LIMIT, "generated plan exceeds 8 MiB; split into smaller plans")
    return text


def build_plan(root, manifest):
    blockers = validate(manifest)
    files = []
    for name, edits in grouped(manifest).items():
        _, old, _ = read_target(root, name)
        before = old.decode("utf-8")
        after = replace_exact(before, edits)
        require(len(after.encode("utf-8")) <= LIMIT, f"replacement exceeds 1 MiB: {name}")
        require(replace_exact(after, edits, reverse=True) == before, "replacement is not uniquely reversible")
        diff = make_diff(name, before, after)
        files.append({"path": name, "before_sha256": digest(old), "after_sha256": digest(after.encode("utf-8")), "diff": diff})
    plan = {"schema_version": 1, "status": "blocked" if blockers else "ready", "blockers": blockers,
            "manifest": manifest, "files": files}
    encode_plan(plan)  # A generated plan must fit the same limit used when loading it.
    return plan


def prose(value):
    # Render untrusted release-note content as text, not embedded HTML/images.
    value = "".join(c if ord(c) >= 32 and ord(c) != 127 else " " for c in value)
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", value)


def report(plan):
    lines = ["# Release-aware update plan", "", f"Status: **{plan['status']}**", "",
             "Readiness reflects supplied evidence, not independent verification or deployment approval.", ""]
    if plan["blockers"]:
        lines += ["## Blockers", *[f"- {prose(x)}" for x in plan["blockers"]], ""]
    for c in plan["manifest"]["components"]:
        r = c["review"]
        lines += [f"## {c['id']}", f"{prose(c['current_version'])} → {prose(c['candidate_version'])} ({c['kind']})", "",
                  "Artifact: " + prose(json.dumps(c["artifact"], ensure_ascii=False)), "", "### Release notes"]
        lines += [f"- {prose(n['url'])}: {prose(n['summary'])}" for n in r["release_notes"]]
        lines += ["", "### Compatibility"] + [f"- {prose(x['target'])}: {x['result']} — {prose(x['evidence'])}" for x in r["compatibility"]]
        for key in ("breaking_changes", "migrations", "tests", "rollback"):
            lines += ["", f"### {key.replace('_', ' ').title()}"]
            lines += [f"- {prose(x)}" for x in r[key]] or ["- None recorded"]
        lines.append("")
    for item in plan["files"]:
        fence = "`" * max(3, max((len(x) + 1 for x in re.findall(r"`+", item["diff"])), default=0))
        lines += [f"## Diff: {prose(item['path'])}", "", fence + "diff", item["diff"].rstrip(), fence, ""]
    return "\n".join(lines)


def save_new(path, data):
    # Exclusive create avoids clobbering existing reports or following a final symlink.
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(data)


def mutate(root, plan, reverse=False):
    fields(plan, {"schema_version", "status", "blockers", "manifest", "files"})
    require(type(plan["schema_version"]) is int and plan["schema_version"] == 1, "unsupported plan schema")
    blockers = validate(plan["manifest"])
    require(not blockers and plan["status"] == "ready" and plan["blockers"] == [], "blocked plan cannot be applied or rolled back")
    groups = grouped(plan["manifest"])
    require(isinstance(plan["files"], list), "plan files must be an array")
    require(len(plan["files"]) == len(groups), "plan file list does not match manifest")
    entries = {}
    for item in plan["files"]:
        fields(item, {"path", "before_sha256", "after_sha256", "diff"})
        require(item["path"] not in entries, "duplicate plan file")
        for key in ("before_sha256", "after_sha256"):
            require(isinstance(item[key], str) and HEX.fullmatch(item[key]), "invalid file hash")
        entries[item["path"]] = item
    require(set(entries) == set(groups), "plan file list does not match manifest")
    pending = []
    for name, edits in groups.items():
        p, old, mode = read_target(root, name)
        item = entries[name]
        start_hash, end_hash = (item["after_sha256"], item["before_sha256"]) if reverse else (item["before_sha256"], item["after_sha256"])
        # A repeated operation is a no-op, including recovery after a partial interruption.
        if digest(old) == end_hash:
            continue
        require(digest(old) == start_hash, f"stale or changed file: {name}; re-plan instead of overwriting")
        new = replace_exact(old.decode("utf-8"), edits, reverse=reverse).encode("utf-8")
        require(len(new) <= LIMIT, f"replacement exceeds 1 MiB: {name}")
        require(digest(new) == end_hash, f"plan content/hash mismatch: {name}")
        before, after = (new, old) if reverse else (old, new)
        require(make_diff(name, before.decode("utf-8"), after.decode("utf-8")) == item["diff"], f"plan diff/content mismatch: {name}")
        require(replace_exact(new.decode("utf-8"), edits, reverse=not reverse).encode("utf-8") == old, "not reversibly applicable")
        pending.append((name, p, old, new, mode))
    staged = []
    try:
        for name, p, old, new, mode in pending:
            fd, temp = tempfile.mkstemp(prefix=".release-aware-", dir=p.parent)
            staged.append((name, p, old, Path(temp)))
            with os.fdopen(fd, "wb") as handle:
                handle.write(new)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, mode)
        # Recheck every input before the first replace. Still not a multi-file transaction.
        for name, _, old, _ in staged:
            require(read_target(root, name)[1] == old, f"file changed during preparation: {name}")
        for name, p, old, temp in staged:
            require(read_target(root, name)[1] == old, f"file changed during write: {name}")
            os.replace(temp, p)
    finally:
        for _, _, _, temp in staged:
            temp.unlink(missing_ok=True)
    return len(pending)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="write a new JSON plan and Markdown report; never change targets")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path, help="new JSON plan path; adjacent .md report is also created")
    for name in ("apply", "rollback"):
        p = sub.add_parser(name, help="change local pin files from a reviewed plan; no deploy or commands")
        p.add_argument("--root", required=True, type=Path)
        p.add_argument("--plan", required=True, type=Path)
    p = sub.add_parser("sha256", help="hash a local artifact, optionally comparing a known expected SHA-256")
    p.add_argument("file", type=Path)
    p.add_argument("--expected")
    args = parser.parse_args(argv)
    try:
        if args.command == "sha256":
            if args.expected is not None:
                require(HEX.fullmatch(args.expected), "expected SHA-256 must be 64 lowercase hex characters")
            with args.file.open("rb") as f:
                value = hashlib.file_digest(f, "sha256").hexdigest()
            print(value)
            require(args.expected is None or value == args.expected, "artifact SHA-256 mismatch")
            return 0
        root = args.root.resolve(strict=True)
        require(root.is_dir(), "root must be a directory")
        if args.command == "plan":
            plan = build_plan(root, load(args.manifest))
            markdown = args.out.with_suffix(".md")
            require(args.out != markdown, "--out must not end in .md")
            require(not args.out.exists() and not args.out.is_symlink() and not markdown.exists() and not markdown.is_symlink(), "output already exists; choose new paths")
            save_new(args.out, encode_plan(plan))
            save_new(markdown, report(plan))
            print(f"{plan['status']}: {args.out} and {markdown}")
            return 2 if plan["blockers"] else 0
        count = mutate(root, load(args.plan), reverse=args.command == "rollback")
        print(f"{args.command}: {count} local file(s) changed; no runtime action taken")
        return 0
    except (Invalid, OSError, UnicodeError, ValueError, TypeError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

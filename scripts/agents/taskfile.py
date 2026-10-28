#!/usr/bin/env python3
"""Task file access for the AOH2 pipeline (library + CLI). No PyYAML needed.

A task file is YAML-ish frontmatter between two `---` lines followed by Markdown
sections (`## Name`). Frontmatter supports `key: value`, `key: [a, b]` and

    key:
      - a
      - b

Values keep their text; `get` returns strings, `getlist` returns lists.

CLI:
  taskfile.py get <file> <key> [<default>]
  taskfile.py getlist <file> <key>            one item per line
  taskfile.py set <file> key=value [key=value ...]
  taskfile.py incr <file> <key>
  taskfile.py section <file> "<Heading>"      body of `## Heading`
  taskfile.py verdict <file> <Review|QA>      APPROVE|REQUEST_CHANGES|PASS|FAIL|NONE
  taskfile.py id <file>                       id from frontmatter (falls back to file name)
"""
import os
import re
import sys

LIST_KEYS = {"allowed_paths", "depends_on", "tests"}
VERDICTS = {"Review": ("APPROVE", "REQUEST_CHANGES"), "QA": ("PASS", "FAIL")}


def _strip_comment(value: str) -> str:
    # `# comment` after a value; keep `#` inside quotes or anchors (`file.md#section`)
    out, in_q = [], None
    for i, ch in enumerate(value):
        if in_q:
            out.append(ch)
            if ch == in_q:
                in_q = None
            continue
        if ch in ("'", '"'):
            in_q = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or value[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).strip().strip('"').strip("'")


def _parse_inline_list(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if not inner else [_strip_comment(x) for x in inner.split(",") if x.strip()]
    return None


class TaskFile:
    def __init__(self, path: str, text: str = None):
        self.path = path
        if text is None:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        self.text = text
        self.lines = self.text.splitlines()
        self.fm_end = self._frontmatter_end()

    @classmethod
    def from_text(cls, text: str, path: str = "<text>"):
        """Parse without touching disk (e.g. `git show <branch>:tasks/x.md`). Writes are not allowed."""
        tf = cls(path, text=text)
        tf._save = lambda: (_ for _ in ()).throw(RuntimeError("read-only TaskFile"))  # type: ignore[method-assign]
        return tf

    def _frontmatter_end(self) -> int:
        if not self.lines or self.lines[0].strip() != "---":
            return -1
        for i in range(1, len(self.lines)):
            if self.lines[i].strip() == "---":
                return i
        return -1

    # ---- reading -------------------------------------------------------
    def frontmatter(self) -> dict:
        data, key_list = {}, None
        if self.fm_end < 0:
            return data
        for line in self.lines[1:self.fm_end]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if key_list and line.strip().startswith("- "):
                data[key_list].append(_strip_comment(line.strip()[2:]))
                continue
            key_list = None
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
            if not m:
                continue
            key, raw = m.group(1), m.group(2)
            lst = _parse_inline_list(_strip_comment(raw) if raw.strip().startswith("[") else "")
            if lst is not None:
                data[key] = lst
            elif raw.strip() == "" or _strip_comment(raw) == "":
                if key in LIST_KEYS:
                    data[key] = []
                    key_list = key
                else:
                    data[key] = ""
                    key_list = key if key in LIST_KEYS else None
            else:
                data[key] = _strip_comment(raw)
        return data

    def get(self, key: str, default=""):
        v = self.frontmatter().get(key, default)
        return v if isinstance(v, str) else (", ".join(v) if isinstance(v, list) else v)

    def getlist(self, key: str):
        v = self.frontmatter().get(key, [])
        if isinstance(v, list):
            return v
        return [x.strip() for x in str(v).split(",") if x.strip()] if v else []

    def getint(self, key: str, default=0) -> int:
        try:
            return int(str(self.get(key, default)).strip() or default)
        except ValueError:
            return default

    def getbool(self, key: str, default=False) -> bool:
        v = str(self.get(key, "")).strip().lower()
        return default if v == "" else v in ("true", "yes", "1", "on")

    def section(self, heading: str) -> str:
        body, inside = [], False
        for line in self.lines[self.fm_end + 1:] if self.fm_end >= 0 else self.lines:
            if line.startswith("## "):
                if inside:
                    break
                inside = line[3:].strip().lower() == heading.lower()
                continue
            if inside:
                body.append(line)
        return "\n".join(body).strip()

    def verdict(self, which: str) -> str:
        text = self.section(which)
        for line in text.splitlines():
            s = line.strip().lstrip("*#> ").upper()
            if not s or s.startswith("(") or s.startswith("<!--"):
                continue
            for v in VERDICTS.get(which, ()):
                if s.startswith(v):
                    return v
            return "NONE"
        return "NONE"

    def task_id(self) -> str:
        tid = self.get("id", "").strip()
        if tid:
            return tid
        m = re.match(r"^(\d+[a-z]?)", os.path.basename(self.path))
        return m.group(1) if m else os.path.basename(self.path)

    # ---- writing -------------------------------------------------------
    def set(self, key: str, value) -> None:
        """Replace a scalar or a list in the frontmatter, keeping everything else."""
        if self.fm_end < 0:
            raise ValueError(f"{self.path}: no frontmatter")
        is_list = isinstance(value, (list, tuple))
        new_lines = [f"{key}:"] + [f"  - {v}" for v in value] if is_list else [f"{key}: {value}"]
        i = 1
        while i < self.fm_end:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", self.lines[i])
            if m and m.group(1) == key:
                j = i + 1
                while j < self.fm_end and self.lines[j].strip().startswith("- "):
                    j += 1
                self.lines[i:j] = new_lines
                self.fm_end += len(new_lines) - (j - i)
                self._save()
                return
            i += 1
        self.lines[self.fm_end:self.fm_end] = new_lines
        self.fm_end += len(new_lines)
        self._save()

    def incr(self, key: str) -> int:
        n = self.getint(key, 0) + 1
        self.set(key, n)
        return n

    def _save(self) -> None:
        self.text = "\n".join(self.lines) + "\n"
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(self.text)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd, path = argv[1], argv[2]
    tf = TaskFile(path)
    if cmd == "get":
        print(tf.get(argv[3], argv[4] if len(argv) > 4 else ""))
    elif cmd == "getlist":
        print("\n".join(tf.getlist(argv[3])))
    elif cmd == "set":
        for kv in argv[3:]:
            k, _, v = kv.partition("=")
            tf.set(k, v)
    elif cmd == "incr":
        print(tf.incr(argv[3]))
    elif cmd == "section":
        print(tf.section(argv[3]))
    elif cmd == "verdict":
        print(tf.verdict(argv[3]))
    elif cmd == "id":
        print(tf.task_id())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

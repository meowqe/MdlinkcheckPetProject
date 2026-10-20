#!/usr/bin/env python3
"""mdlinkcheck: проверка ссылок в Markdown-файлах."""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

__version__ = "0.1.0"

INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_PREFIXES = ("mailto:", "tel:", "#")


def find_links(text):
    """Возвращает список (номер_строки, ссылка). Блоки и инлайн-код пропускаются."""
    links = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = INLINE_CODE_RE.sub("", line)
        for match in LINK_RE.finditer(line):
            links.append((number, match.group(1)))
    return links


def check_local(md_file, link):
    """Проверяет, что локальный файл существует. Якорь (#...) отбрасывается."""
    target = link.split("#", 1)[0]
    if not target:
        return True, "ok"
    path = (md_file.parent / target).resolve()
    return (path.exists(), "ok" if path.exists() else "файл не найден")


def check_url(url, timeout):
    """Проверяет внешнюю ссылку. Сначала HEAD, при 405 повторяет через GET."""
    headers = {"User-Agent": f"mdlinkcheck/{__version__}"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return True, str(response.status)
        except urllib.error.HTTPError as error:
            if error.code == 405 and method == "HEAD":
                continue
            return False, str(error.code)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            return False, str(getattr(error, "reason", error))
    return False, "неизвестная ошибка"


def collect_files(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.is_file():
            files.append(path)
    return files


def run(files, timeout, ignore, offline):
    results = []
    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        for line, link in find_links(text):
            if link.startswith(SKIP_PREFIXES) or any(i in link for i in ignore):
                continue
            if link.startswith(("http://", "https://")):
                if offline:
                    continue
                ok, detail = check_url(link, timeout)
            else:
                ok, detail = check_local(md_file, link)
            results.append(
                {"file": str(md_file), "line": line, "link": link, "ok": ok, "detail": detail}
            )
    return results


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mdlinkcheck",
        description="Проверяет ссылки в Markdown-файлах и находит битые.",
    )
    parser.add_argument("paths", nargs="+", help="файлы или папки для проверки")
    parser.add_argument("--timeout", type=int, default=10, help="таймаут запроса, сек (по умолчанию 10)")
    parser.add_argument("--ignore", action="append", default=[], metavar="TEXT",
                        help="пропускать ссылки, содержащие TEXT (можно указать несколько раз)")
    parser.add_argument("--offline", action="store_true", help="проверять только локальные ссылки")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="формат вывода")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    files = collect_files(args.paths)
    if not files:
        print("Ошибка: Markdown-файлы не найдены.", file=sys.stderr)
        return 2
    results = run(files, args.timeout, args.ignore, args.offline)
    broken = [r for r in results if not r["ok"]]
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in broken:
            print(f"{r['file']}:{r['line']}  {r['link']}  ->  {r['detail']}")
        print(f"\nПроверено ссылок: {len(results)}, битых: {len(broken)}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

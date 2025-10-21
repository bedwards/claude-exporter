#!/usr/bin/env python

import os # type: ignore
import re # type: ignore
import sys # type: ignore
from typing import Literal # type: ignore
from pprint import pprint # type: ignore
from markdown_it import MarkdownIt # type: ignore
from markdown_it.token import Token # type: ignore

path_pattern = re.compile(r'^[.A-Za-z][/\-_A-Za-z]*(\.[a-z]+)*$')
split_pattern = re.compile(r'^// ', re.M)

def is_path(p: str) -> bool:
    return ('.' in p or p == 'LICENSE') and bool(path_pattern.match(p))


def write_file(path: str, content: str) -> None:
    dirs = '/'.join(path.split('/')[:-1])
    if dirs:
        os.makedirs(dirs, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


def pass_01_a(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    for t2, _, t in zip(tokens, tokens[1:], tokens[2:]):
        if t.type == 'fence' and t.info not in ['markdown', '']:
            assert t.markup == '```'
            if t2.type == 'inline':
                path = t2.content
                if is_path(path):
                    write_file(path, t.content)
                    paths.append(path)

    return paths


def pass_01(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    for t in tokens:
        if t.type == 'fence' and t.info == 'markdown' and t.markup == '````':
            md = MarkdownIt()
            tokens = md.parse(t.content)
            paths.extend(pass_01_a(tokens))
    return paths


def main() -> None:
    with open(sys.argv[1]) as f:
        src = f.read()
    md = MarkdownIt()
    tokens = md.parse(src)
    paths: list[str] = []
    paths.extend(pass_01(tokens))
    print('-' * 67)
    for path in sorted(paths):
        print(path)


if __name__ == "__main__":
    main()

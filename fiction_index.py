#!/usr/bin/env python

import os
import re
import sys
from typing import Literal
from pprint import pprint # type: ignore
from markdown_it import MarkdownIt
from markdown_it.token import Token

path_pattern = re.compile(r'^[.A-Za-z][/\-_A-Za-z]*(\.[a-z]+)*$')
split_pattern = re.compile(r'^// ', re.M)


def is_path(p: str) -> bool:
    return ('.' in p or p == 'LICENSE') and bool(path_pattern.match(p))


def is_fence_code_block(t: Token,
                        markup: Literal['```', '````'],
                        info: Literal['markdown', 'typescript'] | None = None) -> bool:
    if info is not None and t.info != info:
        return False
    return (t.type == 'fence' and
            t.tag == 'code' and
            t.block and
            t.markup == markup and
            not t.hidden)


def write_file(path: str, content: str) -> None:
    dirs = '/'.join(path.split('/')[:-1])
    if dirs:
        os.makedirs(dirs, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


# # postcss.config.js


#                            !!! does not close ```` !!!!
# ---
# PROJECT_SUMMARY.md


def pass_01_fence_md_h1(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    path = None
    skip = False
    content_prefix = ''
    h1_is_content = False
    content_lines: list[str] = []

    for t, t_next in zip(tokens, tokens[1:]):
        if skip:
            skip = False
            continue

        elif (t.type == 'heading_open' and t.tag == 'h1'):
            assert t_next.type == 'inline'
            if h1_is_content:
                content_prefix = '# '
                continue
            else:
                skip = True
                if path is not None:
                    content = '\n'.join(content_lines).strip() + '\n'
                    write_file(path, content)
                    paths.append(path)
                    path = None
                content_lines = []
                p = t_next.content.split()[0]
                if is_path(p):
                    path = p
                    h1_is_content = True
                continue

        elif path is None:
            continue

        if t.type.startswith('hr'):
            h1_is_content = False
            continue

        elif t.type.endswith('_open') and t.type != 'paragraph_open':
            content_prefix = t.markup + ' '
            continue
        elif t.type == 'inline':
            content_lines.append(content_prefix + t.content)
            content_prefix = ''
            continue
        elif t.type == 'fence':
            h1_is_content = False
            indent = ' ' * t.level * 2
            content_lines.append(f'{indent}{t.markup}{t.info}')
            for line in t.content.splitlines():
                content_lines.append(f'{indent}{line}')
            content_lines.append(f'{indent}{t.markup}')
            content_prefix = ''
            continue            
        elif t.type == 'heading_close':
            content_lines.append('')
            continue
        elif t.type == 'paragraph_close' and not t_next.type.endswith('close') and not t_next.type == 'fence':
            content_lines.append('')
            continue
        elif (t.type == 'list_item_close' and
                t_next.type in ['heading_open', 'bullet_list_close', 'ordered_list_close']):
            content_lines.append('')
            continue

    if path is not None:
        content = '\n'.join(content_lines).strip() + '\n'
        write_file(path, content)
        paths.append(path)

    return paths


def pass_01_fence_md_h3(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    skip = False
    path = None
    for t, t_next in zip(tokens, tokens[1:]):
        if skip:
            skip = False
            continue

        elif (t.type == 'heading_open' and t.tag == 'h3'): 
            assert t_next.type == 'inline'
            if is_path(t_next.content):
                skip = True
                path = t_next.content
            continue

        elif path is not None and is_fence_code_block(t, '```'):
            write_file(path, t.content)
            paths.append(path)
            path = None
            continue
    return paths


def pass_01(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    for t in tokens:
        if is_fence_code_block(t, '````', 'markdown'):
            md = MarkdownIt()
            tokens = md.parse(t.content)
            paths.extend(pass_01_fence_md_h1(tokens))
            paths.extend(pass_01_fence_md_h3(tokens))
            continue
    return paths


def pass_02_fence_ts(chunks: list[str]) -> list[str]:
    paths: list[str] = []
    for chunk in chunks:
        path, content = chunk.split('\n', 1)
        if is_path(path):
            write_file(path, content)
            paths.append(path)
            continue
    return paths
            

def pass_02(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    for t in tokens:
        if is_fence_code_block(t, '````', 'typescript'):
            chunks = split_pattern.split(t.content)[1:]
            paths.extend(pass_02_fence_ts(chunks))
            continue
    return paths


def main() -> None:
    with open(sys.argv[1]) as f:
        src = f.read()

    md = MarkdownIt()
    tokens = md.parse(src)
    paths: list[str] = []
    paths.extend(pass_01(tokens))
    paths.extend(pass_02(tokens))
    print('-' * 67)
    for path in sorted(paths):
        print(path)


if __name__ == "__main__":
    main()

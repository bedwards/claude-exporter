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
    return '.' in p and bool(path_pattern.match(p))


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


def pass_01_fence_md(tokens: list[Token]) -> list[str]:
    paths: list[str] = []
    skip = False
    path = None
    for t, t_next in zip(tokens, tokens[1:]):
        if skip:
            skip = False
            continue

        elif (t.type == 'heading_open' and 
                t.tag == 'h3' and
                t_next.type == 'inline' and
                is_path(t_next.content)):
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
            paths.extend(pass_01_fence_md(tokens))
            continue
    return paths


# **Database Schema & Migrations (Drizzle)**
# ````typescript
# // src/db/schema.ts

# **React Application Implementation**
# ````typescript
# // src/main.tsx

# **Page Components & Cloudflare Workers**
# ````typescript
# // src/pages/Home.tsx


# **Test Suite & GraphQL Definitions**
# ````typescript
# // tests/setup.ts

# **Utility Files & Project Summary**
# ````typescript
# // src/lib/utils.ts
#                             // Typed storage keys  !!!
# 

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


# **Configuration & Documentation Files**
# ````markdown
# # LICENSE (MIT License)
# ---
# # CONTRIBUTING.md
# # .env.example
# # .gitignore
# # .vscode/extensions.json
# # .vscode/settings.json
# # docker-compose.yml (for local development)
# # Dockerfile.dev
# # .github/ISSUE_TEMPLATE/bug_report.md
# # .github/ISSUE_TEMPLATE/feature_request.md
#                                             literal --- !!!
# # .github/PULL_REQUEST_TEMPLATE.md
# # tailwind.config.js
# # tsconfig.node.json
# # postcss.config.js


#                            !!! does not close ```` !!!!
# ---
# PROJECT_SUMMARY.md





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

#!/usr/bin/env python

import os
import sys
from pprint import pprint # type: ignore
from markdown_it import MarkdownIt
from markdown_it.token import Token

def to_project_structure(tokens: list[Token]):
    path = None
    for t in tokens:
        content = t.content.strip()
        if t.type == 'inline' and t.content.startswith('**') and t.content.endswith('**'):
            path = content.replace('**', '').split(' - ')[0]
            dir = '/'.join(path.split('/')[:-1])
            if dir:
                os.makedirs(dir, exist_ok=True)
        if t.type == 'fence' and t.tag == 'code':
            if path is not None:
                with open(path, 'w') as f:
                    f.write(content)
            

def main():
    with open(sys.argv[1]) as f:
        src = f.read()

    md = MarkdownIt()
    tokens = md.parse(src)
    to_project_structure(tokens)


if __name__ == "__main__":
    main()

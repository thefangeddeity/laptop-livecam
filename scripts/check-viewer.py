#!/usr/bin/env python3
"""Reject a rendered viewer whose structure is broken.

Why this exists: removing a button also removed the <script> tag that opened
the block below it -- the regex that deleted the function ended at its closing
brace, and the tag was on the line above. The page then printed its own source
as text, and it was committed and deployed to two nodes before anyone looked.
Python edits were checked with ast.parse all along; HTML was checked with
nothing.

Counted with html.parser, NOT a regex. Two regex attempts at this failed on
the same class of thing: <script> and <style> appear in PROSE in this file --
in a CSS comment, a JS block comment and a JS line comment -- so a pattern
that counts tags also counts the writing about tags. A parser knows the
difference, and it also knows that everything inside <script> is CDATA, so a
tag mentioned in a string or a comment is not a tag.
"""
import sys
from html.parser import HTMLParser

# Only elements whose mismatch actually breaks the page.
WATCH = ('script', 'style', 'head', 'body', 'html')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.unmatched_end = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        pass                      # self-closing: opens and closes at once

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return
        self.unmatched_end.append((tag, self.getpos()[0]))


def check(path):
    src = open(path, encoding='utf-8').read()
    bad = []

    p = Structure()
    p.feed(src)
    p.close()

    for tag, line in p.stack:
        if tag in WATCH:
            bad.append('<%s> opened at line %d and never closed' % (tag, line))
    for tag, line in p.unmatched_end:
        if tag in WATCH:
            bad.append('</%s> at line %d closes nothing' % (tag, line))

    left = sorted({t for t in __import__('re').findall(r'@[A-Z_]{3,}@', src)})
    if left:
        bad.append('unreplaced placeholders: %s' % ', '.join(left))

    for need in ('id="video"', 'id="settingsPanel"'):
        if need not in src:
            bad.append('missing required element: %s' % need)

    return bad


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: check-viewer.py <rendered.html> [...]', file=sys.stderr)
        raise SystemExit(2)
    failed = False
    for path in sys.argv[1:]:
        problems = check(path)
        if problems:
            failed = True
            print('FAIL %s' % path, file=sys.stderr)
            for b in problems:
                print('     %s' % b, file=sys.stderr)
        else:
            print('ok   %s' % path)
    raise SystemExit(1 if failed else 0)

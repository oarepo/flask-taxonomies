import json
import re
import shlex
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import pytest


class CURLExample:
    def __init__(self, lineno, params, headers, content):
        self.params = params
        self.headers = headers
        self.content = content
        self.lineno = lineno
        self.method = 'GET'
        self.request_payload = None
        self.request_headers = {}
        self.url = None
        self.parse_params()

    def parse_params(self):
        params = iter(self.params)
        while True:
            try:
                param = next(params)
            except StopIteration:
                break
            if param == '-i':
                continue
            if param == '-H' or param == '--header':
                header = [x.strip() for x in next(params).split(':', maxsplit=1)]
                self.request_headers[header[0]] = header[1]
                continue
            if param.startswith('http://') and self.url is None:
                self.url = param
                continue
            if param == '-X':
                self.method = next(params)
                continue
            if param == '--data-raw':
                self.request_payload = next(params)
                continue

            raise ValueError('Parameter %s not found at line %s' % (param, self.lineno))

    @property
    def path(self):
        return urlparse(self.url).path

    @property
    def query(self):
        return urlparse(self.url).query or None

    @property
    def status_code(self):
        if not self.headers:
            return 200
        return int(self.headers[0].split()[1])

    def check_headers(self, resp):
        response_headers = resp.headers
        print(response_headers)
        for hdr in self.headers[1:]:
            name, value = [x.strip() for x in hdr.split(':', maxsplit=1)]
            print(name, value)
            if name not in response_headers:
                raise ValueError('%s header is expected but not found in response headers' % name)

    def run(self, client):
        resp = client.open(path=self.path, query_string=self.query, method=self.method,
                           content_type=self.request_headers.get('Content-Type', None),
                           headers=self.request_headers,
                           data=self.request_payload or None)
        try:
            assert resp.status_code == self.status_code
            if self.headers:
                self.check_headers(resp)
            if self.content:
                joined_content = ''.join(self.content)
                if '...' in joined_content:
                    joined_content = '.*'.join(re.escape(x.replace(' ', '')) for x in joined_content.split('...'))
                    actual_content = json.dumps(resp.json, sort_keys=True).replace(' ', '')
                    print('Matching regex')
                    print(joined_content)
                    print(actual_content)
                    assert re.fullmatch(joined_content, actual_content)
                else:
                    expected_json = json.loads(joined_content)
                    actual_json = resp.json
                    assert expected_json == actual_json
            else:
                assert not resp.data
        except:
            print('Exception in test on line %s. Query:' % self.lineno)
            print('    ', ' '.join(x if ' ' not in x else '"' + x + '"' for x in self.params or []))
            print('Expected response: ')
            for h in self.headers or []:
                print('    ', h)
            print()
            for b in self.content or []:
                print('    ', b)
            print()
            print('Actual response: ')
            for h in resp.headers or []:
                print('    ', h)
            print()
            for b in resp.data.decode('utf-8').split('\n'):
                print('    ', b)
            raise


def read_console_content(first_lineno, lines):
    ret = []
    while True:
        lineno, l = next(lines)
        l = l.strip()
        if l.startswith('```'):
            break
        ret.append(l)
    if not ret[0].startswith('$ curl'):
        return None
    ret[0] = ret[0][len('$ curl'):].strip()
    accumulator = ''
    all_params = []
    while ret:
        l = ret.pop(0)
        if not l:
            continue
        has_more_lines = l[-1] == '\\'
        if has_more_lines:
            l = l[:-1]
        accumulator += l
        try:
            l = shlex.split(accumulator, posix=True)
        except ValueError as e:
            continue
        all_params.extend(l)
        accumulator = ''
        if not has_more_lines:
            break
    if accumulator:
        raise ValueError('Lexing error at line %s, content %s' % (first_lineno + 1, accumulator))

    parts = []
    while ret:
        while ret and ret[0] == '':
            ret.pop(0)
        parts.append([])
        while ret and ret[0] != '':
            parts[-1].append(ret.pop(0))

    if not parts:
        raise ValueError('No reply at line %s' % (first_lineno + 1))
    if len(parts) == 1:
        if parts[0][0].startswith('HTTP/'):
            return CURLExample(first_lineno + 1, all_params, parts[0], None)
        else:
            return CURLExample(first_lineno + 1, all_params, None, parts[0])
    if len(parts) == 2:
        return CURLExample(first_lineno + 1, all_params, parts[0], parts[1])
    raise ValueError('Too many parts at line %s' % (first_lineno + 1))


def readme_examples_test(api, client, country_taxonomy):
    with open(Path(__file__).parent.parent / 'README.md') as f:
        lines = f.readlines()
    lines = iter(enumerate(lines))
    examples = []
    while True:
        try:
            lineno, l = next(lines)
        except StopIteration:
            break

        if l.startswith('```console'):
            cc = read_console_content(lineno, lines)
            if cc:
                examples.append(cc)

    for ex in examples:
        ex.run(client)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
# .........../\./\...___......|\.|..../...\........#
# ........../..|..\/\.|.|_|._.|.\|....|.c.|........#
# ........./....../--\|.|.|.|i|..|....\.../........#
#        Mathtin (c)                              #
###################################################
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2021 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import os

from typing import List, Generator

LICENSE_FILE = 'LICENSE'


def sources(skip_line, path: str) -> Generator[str, None, None]:
    with open(path, 'r') as f:
        lines = f.readlines()
    # skip header
    it = iter(lines)
    for line in it:
        if skip_line in line:
            break
    # pick first non-empty line
    for line in it:
        if line:
            yield line.replace("\r", "")
            break
    # continue yielding
    for line in it:
        yield line.replace("\r", "")


def list_files(ext: str, directory: str) -> List[str]:
    return [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if
            os.path.splitext(f)[1].lower() == f'.{ext}']


def license_py_file(path: str) -> None:
    prefix = ["#!/usr/bin/env python3\n", "# -*- coding: utf-8 -*-\n", "\n", '"""\n']
    suffix = ['"""\n', '\n', f'__author__ = "{__author__}"', '\n']
    with open(LICENSE_FILE, 'r') as f:
        license_lines = f.readlines()
    tail_content = list(sources('__author__', path))
    new_content = prefix + license_lines + suffix + tail_content
    with open(path, 'w') as f:
        f.writelines(new_content)


def main():
    # License py files in src
    for file in list_files('py', 'src'):
        license_py_file(file)


if __name__ == '__main__':
    main()

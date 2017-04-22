#!/usr/bin/python2.7

import readline
import sys
import os

sys.dont_write_bytecode = True

class Completer(object):
    def _listdir(self, root):
        res = []
        for name in os.listdir(root):
            if name[:1] == '.':
                continue
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            elif not name.endswith('.torrent'):
                continue
            res.append(name)
        return res

    def _complete_path(self, path=None):
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
                for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or not os.path.exists(path):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        # exact file match terminates this completion
        return [path + ' ']

    def complete(self, text, state):
        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer()
        if not line:
            return (self._complete_path('.') + [None])[state]
        return (self._complete_path(line) + [None])[state]

def raw_path(text):
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(Completer().complete)
    return raw_input(text)

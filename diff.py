#! /usr/bin/python
# -*- coding: utf-8 -*-


__modulename__ = "diff"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"


import tempfile
import random
import string
import os.path
import os
import subprocess
import codecs
import types
from StringIO import StringIO
from collections import namedtuple

import lxml.html as lh

# import chardet - character encoding auto-detection system
try:
    import chardet
    _detector = chardet
except ImportError:
    _detector = None


class _DiffTmpFiles(object):
    """
    Private context manager class for creating two temporary files in the
    /tmp/ directory and returning it's names. At the __exit__ it will delete
    these files.
    """
    def __init__(self, obj1, obj2):
        self.fn1 = self.get_unique_tmpfilename()
        self.fn2 = self.get_unique_tmpfilename()
        with codecs.open(self.fn1, encoding='utf-8', mode='wb') as f1:
            f1.write(obj1)
            if obj1[-1] != '\n':
                f1.write('\n')
        with codecs.open(self.fn2, encoding='utf-8', mode='wb') as f2:
            f2.write(obj2)
            if obj2[-1] != '\n':
                f2.write('\n')

    def __enter__(self):
        return (self.fn1, self.fn2)

    def __exit__(self, type, value, traceback):
        os.unlink(self.fn1)
        os.unlink(self.fn2)
        return False # delegate exceptions

    def randomchar(self):
        return (string.ascii_letters + string.digits)[random.randint(0,61)]

    def randomhash(self):
        return ''.join([self.randomchar() for _ in range(20)])

    def get_unique_tmpfilename(self):
        fn = '/tmp/monitor.%s.tmp' % self.randomhash()
        while os.path.isfile(fn):
            fn = '/tmp/monitor.%s.tmp' % self.randomhash()
        return fn


class DocumentDiff(object):
    """
    Zakladni interface sjednocujici pristup k diffovani dokumentu.

    Zdedena trida musi implementovat tridu diff, ktera se stara o diffnuti
    dvou dokumentu stejnych typu.
    """
    @classmethod
    def diff(cls, obj1, obj2):
        raise NotImplementedError("Interface DocumentDiff needs to be implemented")


class PlainTextDiff(DocumentDiff):
    """
    This class is a diff wrapper around classical gnu diff. Using this differ
    we can process every text documents (plaintext, html, css etc.)
    """
    @classmethod
    def diff(cls, obj1, obj2):
        """
        @param obj1: first text to be diffed
        @type obj1: string or unicode
        @param obj2: second text to be diffed
        @type obj2: string or unicode
        @returns: unicode diff
        @rtype: unicode
        """
        if not isinstance(obj1, basestring) or not isinstance(obj2, basestring):
            raise TypeError("Diffed objects have to be strings or unicode.")
        tmp = tempfile.TemporaryFile(suffix='', prefix='tmp')
        devnull = open("/dev/null")
        with _DiffTmpFiles(obj1, obj2) as (fn1, fn2):
            subprocess.call(["diff", fn1, fn2], stdout=tmp, stderr=devnull)
        devnull.close()
        tmp.seek(0)
        output = tmp.read().decode('utf-8')
        tmp.seek(0, os.SEEK_END)
        tmp.close()
        return output


class BinaryDiff(DocumentDiff):
    """
    Tato trida bude diffovat binarni dokumenty - prevazne pdf, odt, doc atp.
    """
    @classmethod
    def diff(cls, obj1, obj2):
        raise NotImplementedError()


class HtmlDiff(DocumentDiff):
    """
    Html diff, which shows pieces of code, which was added to the page.
    Uses output of GNU diff and its interface PlainTextDiff.
    
    Returns generator object HtmlDiffChunk
    Usage:
    >>> # r is resource
    >>> d = r.get_diff(-2,-1) #get diff of last two versions
    >>> print d.next()
    HtmlDiffChunk(position=u'line_info_from_diff', removed=u'this was removed',added=u'this was added')

    """
    _possible_encodings = ('ascii', 'utf-8', 'cp1250', 'latin1', 'latin2', 'cp1251')

    @classmethod
    def _preformat_html(cls, html):
        class __Buf(object):
            def __init__(self):
                self.__buf = ['']

            def append(self, char):
                if not (char in ('\n','\r', '\t', ' ') and self.__buf[-1] in ('\n','\r')):
                    self.__buf.append(char)

            def flush(self):
                return ''.join(self.__buf)
        parsed = lh.fromstring(html)
        repaired_html = lh.tostring(parsed)
        s = StringIO(repaired_html)
        buf = __Buf()
        state = 2
        # FSM for reading (not parsing!!!) HTML
        # 1 = reading tag name and atrs, 2 = reading text inside tag
        # 3 = reading closing tag
        while s.pos != s.len:
            char = s.read(1)
            if state == 1:
                if char == '>':
                    state = 2
                    buf.append(char)
                elif char == '/':
                    buf.append(char)
                    char = s.read(1)
                    if char == '>':
                        buf.append(char)
                        buf.append('\n')
                        state = 2 
                    else:
                        buf.append(char)
                else:
                    buf.append(char)
            elif state == 2:
                if char == '<':
                    char = s.read(1)
                    if char == '/': #closing tag
                        buf.append('</')
                        state = 3
                    else:
                        buf.append('\n')
                        buf.append('<%s' % char)
                        state = 1
                else:
                    buf.append(char)
            elif state == 3:
                if char == '>':
                    buf.append('>')
                    buf.append('\n')
                    state = 2 
                else:
                    buf.append(char)
        return buf.flush()

    @classmethod
    def _solve_encoding(cls, html):
        global _detector
        _guess = False
        if _detector is not None:
            d = _detector.detect(html)
            encoding = d['encoding']
            if encoding is None:
                _guess = True
        else:
            _guess = True
        if _guess:
            for e in cls._possible_encodings:
                try:
                    html.decode(e)
                    encoding = e
                    break
                except: pass
        # convert it into unicode
        try:
            return unicode(html, encoding)
        except (UnicodeDecodeError, ValueError, LookupError):
            raise RuntimeError("Wrong encoding guessed: %s" % encoding) #delete!!
            return html

    @classmethod
    def htmldiff(cls, raw_diff):
        HtmlDiffChunk = namedtuple('HtmlDiffChunk', 'position, removed, added')
        # chunk = (line, removed, added)
        _chunk = None
        for line in raw_diff.splitlines():
            if line[0] in string.digits:
                if _chunk is not None:
                    yield HtmlDiffChunk(position=_chunk[0], removed=_chunk[1], added=_chunk[2])
                _chunk = [line, u'', u'']
            elif line.startswith("<"): # removed
                _chunk[1] += line[2:]
            elif line.startswith(">"): # added
                _chunk[2] += line[2:]
            elif line.startswith("-"): # delimiter ---
                pass
            else:
                raise RuntimeError("What was there? THIS: %s" % line)
        yield HtmlDiffChunk(position=_chunk[0], removed=_chunk[1], added=_chunk[2])

    @classmethod
    def _added_text(cls, chunk):
        # NOT USED YET
        if not chunk[1]: # if no removed text, all is added
            return chunk[2]
        # generate diff
        for i, char in enumerate(chunk[2]):
            if chunk[1][i] != char:
                for j, char in enumerate(reversed(chunk[2])):
                    if chunk[1][-j-1] != char:
                        if j != 0:
                            return chunk[2][i:-j]
                        else:
                            return chunk[2][i:]

    @classmethod
    def diff(cls, obj1, obj2):
        f1 = cls._preformat_html(obj1)
        f2 = cls._preformat_html(obj2)
        diff = PlainTextDiff.diff(f1, f2)
        return cls.htmldiff(diff)


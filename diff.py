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
        @param obj2: first text to be diffed
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

# Zde je mozne implementovat dalsi typy diffu specializovane (pozdeji) pro nektery
# ucel - napr. se muze objevit diff, ktery je velmi pomaly na doc, ale velmi
# rychly na PDF. Interface pro tento algoritmus se pak implementuje ZDE.

#! /usr/bin/python
# -*- coding: utf-8 -*-

__modulename__ = "diff"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"


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
    Tato trida bude diffovat textove dokumenty (plaintext, html, css, jakykoliv
    kod krome binarniho).
    """
    @classmethod
    def diff(cls, obj1, obj2):
        raise NotImplementedError()


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
#! /usr/bin/python
# -*- coding: utf-8 -*-

__modulename__ = "resolver"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"


from model import HttpHeaderMeta, Storage

class Resolver(object):
    """
    System pro zajisteni funkcionality "zmenilo se neco na dane URL?". Zde se
    bude osetrovat mnoho vyjimek s http hlavickami, s md5, content-length atp.

    Implikace:
    changed(HTTP:content-length) -> content changed
    changed(HTTP:md5) -> content changed
    changed(HTTP:response code) -> it depends..
    changed(HTTP:last-modified) -> doesn't matter
    """
    def __init__(self, storage):
        # Storage
        self._storage = storage
        # GridFS
        self._filesystem = storage.filesystem
        # Collection "httpheader"
        self._headers = storage._headermeta

        # FIXME: smazat
        self._base = ""
        self._counter = 0

    def resolve(self, url):
        # Tady bude asi ta nejvetsi magie z celeho systemu

        #Musi zajistit, ze se spravne updatuje databaze, pokud se neco zmenilo.
        #Pokud byl proveden redirect, pak musi do Content.urls = [] ulozit obe
        #dve URL adresy (puvodni a redirectnutou).

        #FIXME: prozatimni - smazat!!
        self._base += "random data" + str(self._counter)
        self._counter += 1
        self._filesystem.put(self._base, filename=url, content_type="text/plain")


class Rule(object):
    """
    Pravidlo pro resolver.
    """
    def __call__(self):
        """
        Pokud __call__ vraci true, pak rule matchl.
        """
        pass
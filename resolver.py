#! /usr/bin/python
# -*- coding: utf-8 -*-

__modulename__ = "resolver"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"



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
        # are large documents allowed?
        self._allow_large = self._storage.allow_large
        # GridFS
        self._filesystem = storage.filesystem
        # Collection "httpheader"
        self._headers = storage._headermeta

    def resolve(self, url):
        # Tady bude asi ta nejvetsi magie z celeho systemu

        #Musi zajistit
        # - ze se posle pozadavek na server
        # - ze se spravne updatuje databaze, pokud se neco zmenilo.
        # - pokud byl proveden redirect, pak musi do Content.urls = [] ulozit obe
        # dve URL adresy (puvodni a redirectnutou)
        # a plno dalsich veci..
        pass
        


class Rule(object):
    """
    Pravidlo pro resolver. Mozna se bude hodit nejake takove rozdeleni
    tech pravidel... proste rozdel a panuj.
    """
    def __call__(self):
        """
        Pokud __call__ vraci true, pak rule matchl.
        """
        pass
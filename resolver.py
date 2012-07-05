#! /usr/bin/python
# -*- coding: utf-8 -*-

__modulename__ = "resolver"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"

import _http

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
#?        self._storage = storage
        # are large documents allowed?
#?        self._allow_large = self._storage.allow_large
        # GridFS
#?        self._filesystem = storage.filesystem
        # Collection "httpheader"
#?        self._headers = storage._headermeta
        pass

    def resolve(self, url):
        # Tady bude asi ta nejvetsi magie z celeho systemu

        #Musi zajistit
        # - ze se posle pozadavek na server
        # - ze se spravne updatuje databaze, pokud se neco zmenilo.
        # - pokud byl proveden redirect, pak musi do Content.urls = [] ulozit obe
        # dve URL adresy (puvodni a redirectnutou)
        # a plno dalsich veci..

#pseudocode
        # fetch last from DB
        # ask HEAD

        # decide whether a change occured
        #   if so -> download
        #   if can't be told so, download
        #       and compute our md5 and check based on it
        #   if certainly not (md5, etag) say "nothing changed"

        # for downloaded, get diff, store it into the DB
        # and store the recieved headers as well
# pseudocode end
        db_metainfo = _get_metainfo_from_db(url):
        print db_metainfo

        pass


    def _get_metainfo_from_db(self, url)
    """
    Returns last metainfo upon the given url stored in the DB.
    """
        mockup = {
            filename : 'http://www.aquafortis.cz/trenink.html',
            md5 : "abcdef123456789",
            sha1 : "12345678890abcde",
            content_type : "idk",
            length : 1274
            urls : ['http://www.aquafortis.cz/trenink.html']
        }

        return mockup

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

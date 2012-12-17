#! /usr/bin/python
# -*- coding: utf-8 -*-

__modulename__ = "resolver"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$25.6.2012 12:12:44$"

import _http
import hashlib
import model

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
    def __init__(self, storage, timeout = 10):
        # Storage
        self._storage = storage
#?        print "RESOLVER: STORAGE: ",self._storage
        # are large documents allowed?
        self._allow_large = self._storage.allow_large
        # GridFS
        self._filesystem = storage.filesystem
        # Collection "httpheader"
        self._headers = storage._headermeta
        # Timeout for checking pages
        self._timeout = timeout
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
        decision = self._make_decision(url)
        #print(decision)
        self._store_into_db(decision,url)

    def _make_decision(self, url):
        self.db_metainfo = self._get_metainfo_from_db(url)
        conn_proxy = _http._HTTPConnectionProxy(url,self._timeout)
        self.web_metainfo = conn_proxy.send_request("HEAD",url)
        
        store_decision = (0,"Store both header and content")

        print "Resolver: _make_decision: db_metainfo",self.db_metainfo
#?        print self.web_metainfo

        if self.web_metainfo == None:
            store_decision = (3, "Timeouted")
            return store_decision

        try:
            if self.db_metainfo['etag'] == self.web_metainfo[1]['etag']:
                store_decision = (1, "Store only header (based on etags equality)")
        except KeyError:
            pass

        try:
            if self.web_metainfo[1]['content-md5'] == self.db_metainfo['content']['md5']:
                store_decision = (1, "Store only header (based on recieved content-md5 equality)")
        except KeyError:
            pass

        if store_decision[0] != 0:
            return store_decision

        # etag and content-md5 are the only authoritave evidents of 'it has not changed'
        # therefore, now is the time to download the content

        self._web_full_info = conn_proxy.send_request("GET",url)
        
        if self._web_full_info == None:
            return "Pruuser, HEAD prosel, GET uz ne"

#?        print "header: " + self._web_full_info[1]['content-length'] + ", len(): " + str(len(self._web_full_info[2]))
#?        print "_web_full_info[0]: ",self._web_full_info[0]
#?        print "_web_full_info[1]: ",self._web_full_info[1]        
#?        print "_web_full_info[2]: ",self._web_full_info[2] # this is the full html code of the page
#?        print "_web_full_info[3]: ",self._web_full_info[3]

        mdfiver = hashlib.md5()
        mdfiver.update(self._web_full_info[2])
        self._md5 = mdfiver.hexdigest()
#?        print "md5: " + self._md5

        shaoner = hashlib.sha1()
        shaoner.update(self._web_full_info[2])
        self._sha1 = shaoner.hexdigest()
#?        print "sha1: " + self._sha1

        if self._md5 == self.db_metainfo['content']['md5'] and self._sha1 == self.db_metainfo['content']['sha1']:
            store_decision(1, "Store only header (based on computed md5 and sha1 equality)")
#?        print "store_decision: ",store_decision
        return store_decision


    def _store_into_db(self, store_decision, url):
        """
        Stores metainfo (and content) in the storage.
        """
       
#?        print "In Resolver._store_into_db: store_decision: ",store_decision
        web_full_info_cat = ""
        for i in range(4):
            web_full_info_cat += str(self._web_full_info[i])
        #print web_full_info_cat
        if store_decision[0] == 0:
            # store both headers and content
            self._headers.save_header(url,self._web_full_info[0], self._web_full_info[1], 'content_id')
            # TODO: store data in GridFS... need to be consistent with the expectations of the other modules
            self._filesystem.put(web_full_info_cat,filename=url) # ..something like this, but not exactly
        elif store_decision[0] == 1:
            # store headers only
            self._headers.save_header(url,self._web_metainfo[0], self._web_metainfo[1], None)
        elif store_decision[0] == 3:
            # store information about the timeout
            self._headers.save_header(url,None, 'Timeouted', None)
        else:
            # this NEVER happens
            print "Dafuq?"
#?        print "self._headers:", self._headers
        return

    def _get_metainfo_from_db(self, url):
        """
        Returns last metainfo upon the given url stored in the DB.
        """
        mockup_content = {
            'filename': "http://www.aquafortis.cz/trenink.html",
            'md5': '233fde7ca8a474f4cc7a198ba87822ff',
            'sha1': 'b2e4bce03a0578da5fd9e83b28acac819f365bda',
            'content_type': '',
            'length': 1347,
            'urls' : ['http://www.aquafortis.cz/trenink.html']
        }

        mockup_header = {
          'timestamp': 1341161610.287,
          'response_code': 200,
          'last_modified': 'cosi',
          'etag': '"928169-543-4c46b09cfca00"',
          'uid': "rrs_university",
          'url': "http://www.cosi.cz",
          'content': mockup_content  # object_id
        }
        #q = {'url':url}
	#print "METAINFO FROM DB:",self._headers.objects.find(q)
        #for item in self._headers.objects.find(q):
        #    print "get_metainfo_from_db: ",item #self._headers.objects.find(q)
        #return self._headers.objects.find(q)[0]

#        mockup_content = {
#            'filename': "http://www.fit.vutbr.cz",
#            'md5' : '233fde7ca8a474f4cc7a198ba87822ff',
#            'sha1': 'b2e4bce03a0578da5fd9e83b28acac819f365bda',
#            'content_type': 'text/html',
#            'length': 1347,
#            'urls' : ['http://www.fit.vutbr.cz']
#        }

#        mockup_header = {
#            'timestamp': 1341161610.287,
#            'response_code': 200,
#            'last_modified': 'cosi',
#            'uid': "rrs_university",
#            'url': "http://www.fit.vutbr.cz",
#            'content': mockup_content
#        }

        return mockup_header

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

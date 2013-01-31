#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Changemonitor -- monitoring changes on web

TODO: docstring.
1) koncepce, casti (checking, availability, versioning, differ)
2) user-view vs global-view
3) usage

The very basic and most probable usage:
    >>> from rrslib.web.changemonitor import Monitor
    >>> monitor = Monitor(user_id="rrs_university")
    >>> resource = monitor.get("http://www.google.com")
    >>> # if the page changed
    >>> if resource.check():
    >>>     print res.get_diff(start='last', end='now')


"""

__modulename__ = "changemonitor"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__  = "$21.6.2012 16:08:11$"

from urlparse import urlparse

from gridfs.errors import NoFile
from pymongo import Connection

from model import HttpHeaderMeta, Content, Storage, File
from resolver import Resolver
from _http import HTTPDateTime
from errors import *

import diff

__all__ = ["Monitor", "MonitoredResource", "HTTPDateTime"]

# constant defining the size of file, which is supposed to be "large"
# for more info see Monitor.allow_large_docuements.__doc__
LARGE_DOCUMENT_SIZE = 4096


class MonitoredResource(object):
    """
    Monitored resource (URL). The ressource is generally any document in any
    format, but most often it will be HTML code.

    This class wraps the URL content and metadata.

    The contents can be manipulated within the time so it can provide information
    about how the content changed in different versions of the document.

    Warning:
    Application developers should generally not need to instantiate this class
    directly. The only correct way how to get this object is through
    Monitor.get() method.

    Design pattern: Active Record

    Example of checking new version of document:
        >>> from rrslib.web.changemonitor import Monitor
        >>> monitor = Monitor(user_id="myuid")
        >>> monitor
        Monitor(conn=Connection('localhost', 27017), dbname='webarchive', uid='myuid')
        >>> resource = monitor.get("http://www.myusefulpage.com/index.html")
        >>> resource
        <MonitoredResource(url='http://www.myusefulpage.com/index.html', uid='myuid') at 0xb7398accL>
        >>> resource.check()
        True
        >>> # the resource has changed

    Checking availability of the document on the URL
        >>> from rrslib.web.changemonitor import HTTPDateTime
        >>> resource = monitor.get("http://www.nonexistentpage.com")
        >>> resource.available()
        False
        >>> resource = monitor.get("http://www.myusefulpage.com/index.html")
        >>> resource.available(HTTPDateTime(2012, 6, 30, 15, 34))
        True

    Example of getting last available version of the document on the URL
        >>> resource = monitor.get("http://www.myusefulpage.com/index.html")
        >>> content = resource.get_last_version()
        >>> print content.data
        <html><head>
        ...
        >>> resource = monitor.get("http://www.crazynonexistentpage.com")
        >>> content = resource.get_last_version()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        DocumentNotAvailable: The content of this URL is not available and it
        is not in the storage.

    Example of getting version of the document in exact time
        >>> resource = monitor.get("http://www.myusefulpage.com/index.html")
        >>> content = resource.get_version(HTTPDateTime(2012, 6, 30, 15, 34))

    Getting the last time when the document was checked:
        >>> resource = monitor.get("http://www.crazynotexistentpage.com")
        >>> resource.last_checked()
        HTTPDateTime(Thu, 01 Jan 1970 00:00:00 GMT)
    """
    def __init__(self, url, uid, storage):
        """
        @param url: monitored URL
        @type url:  basestring (str or unicode)
        @param uid: user identifier. This ID has to be unique for each one,
                    who is using changemonitor.
        @type uid: str
        @param storage: storage of monitored-resource data
        @type storage: model.Storage
        """
        # resource data
        self.url = url
        self.uid = uid

        # models
        self.storage = storage
        self.headers = storage._headermeta

        # resolver
        self.resolver = Resolver(storage)
        self._checked = False
        # file
        try:
            self.file = self.storage.get(url)
        except DocumentNotAvailable:
            # if the file is not in the storage, resolver has to check
            # the url and load actual data into the storage
            self.resolver.resolve(url)
            self._checked = True
            try:
                self.file = self.storage.get(url)
            except DocumentNotAvailable:
                raise DocumentNotAvailable("Resource '%s' is not available." % url)


    def check(self):
        """
        Check the resource URL and load the most recent version into database.

        TODO: consider using @lazy decorator. Most of use cases use this method
        so we have to insure that it will be called only once.

        @raises: DocumentTooLargeException
        @returns: True if the document has changed since last check.
        """
        # bude vyuzivat resolveru pro checknuti URL a ziskani informace o tom,
        # jestli byl dokument zmenen. Mozna bude take dobre nahrat rovnou do
        # self.file nejnovejsi verzi, ale o tom je potreba jeste pouvazovat.

        # urcite je potreba pred kazdym checkem refreshout file cache
        self.file.refresh_cache()

        if not self._checked: # use resolver to get most recent version if not yet checked
            self.resolver.resolve(self.url)
            self._checked = True
            try:
                self.file = self.storage.get(self.url)
            except DocumentNotAvailable:
                raise DocumentNotAvailable("Resource '%s' is not available." % self.url)
        
        # and determine return value
        try:
        # time of last check
            _now = self.headers.get_by_version(self.url,-1,True)['timestamp'] 
            _now = HTTPDateTime().from_timestamp(_now)
        # time of previous check
            _prev = self.headers.get_by_version(self.url,-2,True)['timestamp']
            _prev = HTTPDateTime().from_timestamp(_prev)
        except TypeError: # this is first time document is checked
            return True

        d = self.get_diff(_prev,_now)
        
        if d is None: return False
        if isinstance(d, basestring) and len(d)==0: return False
        try: # d is htmldiff output
            chunk = d.next()
            if len(chunk.added)==0 and len(chunk.removed)==0:
                return False
        except (StopIteration, TypeError): # if can't get d.next(), then d is probably empty -> no change
            return False
        
        return True
        
    def get_last_version(self):
        """
        Get last available content of the document. If the document is available
        at this time, returns most recent version which is on the web server.

        @returns: Last available content of this resource.
        @rtype: Content
        @raises: DocumentNotAvailable if no content available (resource does not
        exist on the URL and never existed within the known history)
        """
        self.resolver.resolve(self.url)
        self._checked = True
        try:
            self.file = self.storage.get(self.url)
            return self.file.get_last_version()
        except NoFile: # FIXME tady to prece nemuze byt??!
            raise DocumentNotAvailable("Resource '%s' is not available." % self.url)


    def get_version(self, time_or_version):
        """
        Get content of this document in specified time or version. If the
        document was not available in given time, returns last available content.
        If there is no available content until given time, raises exception.

        @param time_or_version: Time or version of the content we want to retrieve.
            Version numbering is a convenience atop the GridFS API provided
            by MongoDB. version ``-1`` will be the most recently uploaded
            matching file, ``-2`` the second most recently uploaded, etc.
            Version ``0`` will be the first version
            uploaded, ``1`` the second version, etc. So if three versions
            have been uploaded, then version ``0`` is the same as version
            ``-3``, version ``1`` is the same as version ``-2``, and
            version ``2`` is the same as version ``-1``.
        @type time_or_version: HTTPDateTime or int
        @raises: DocumentHistoryNotAvailable if there is no available content until
        given time or version
        """
        if isinstance(time_or_version, HTTPDateTime):
            return self.file.get_version(time_or_version.to_timestamp())
        elif isinstance(time_or_version, int):
            return self.file.get_version(time_or_version)
        else:
            raise TypeError("Version time has to be type HTTPDateTime or GridFS version (int).")


    def get_diff(self, start, end):
        """
        @param start: start time or version to be diffed
        @type start: HTTPDateTime or int
        @param end: end time or version to be diffed
        @type end: HTTPDateTime or int
        @returns: either textual or binary diff of the file (if available).
                  If contents are equal (document did not change within this
                  time range) returns None.
        @rtype: unicode
        @raises: DocumentHistoryNotAvaliable if the storage doesn't provide
                 enough data for computing the diff.
        """
        content_start = self.get_version(start)
        content_end = self.get_version(end)
        if content_start == content_end:
            return None
        return content_start.diff_to(content_end)


    def available(self, httptime=None):
        if (not isinstance(httptime, HTTPDateTime)) and (httptime is not None):
            raise TypeError("Time of availability has to be type HTTPDateTime.")
        # Pokud je httptime=None, pak se jedna o dostupnost v tomto okamziku
        raise NotImplementedError()


    def last_checked(self):
        """
        Get information about the time of last check of this resource.

        @returns: time of last check or None if the resource was never checked
                  (or the HTTP requests timed out)
        @rtype: HTTPDateTime or None
        """
        return self.headers.last_checked(self.url)


    def __repr__(self):
        return "<MonitoredResource(url='%s', uid='%s') at %s>" % \
            (self.url, self.uid, hex(id(self)))

    __str__ = __repr__

    

class Monitor(object):
    """
    Monitor is main class representing web change monitor. It serves
    as factory for creating MonitoredResource objects.

    Usage:
        >>> from rrslib.web.changemonitor import Monitor
        >>> monitor = Monitor(user_id="rrs_university")
        >>> resource = monitor.get("http://www.google.com")
        >>> # if the page changed
        >>> if resource.check():
        >>>     print res.get_diff(start='last', end='now')
    """
    def __init__(self, user_id, db_host="localhost", db_port=27017, db_name="webarchive", http_proxy=None):
        """
        Create a new monitor connected to MongoDB at *db_host:db_port* using
        database db_name.

        @param user_id: identification string of user/module who uses monitor.
                        If user_id is given None, the monitor switches to
                        `global-view` mode and all requests to storage don't
                        care about >>who checked this resource<<. On the other
                        hand, if user_id is given a string, the monitor switches
                        to `user-view` mode and all operations are oriented
                        to the user. Most of the reasonable use cases are
                        using user_id, because a user/module almost everytime
                        ask about >>what changed since I have been here for the
                        last time<<, not >>what changed since somebody has been
                        here for the last time<<...
        @type user_id: str or None
        @param db_host: (optional) hostname or IP address of the instance
                        to connect to, or a mongodb URI, or a list of
                        hostnames / mongodb URIs. If db_host` is an IPv6 literal
                        it must be enclosed in '[' and ']' characters following
                        the RFC2732 URL syntax (e.g. '[::1]' for localhost)
        @param db_port: (optional) port number on which to connect
        @type db_port: int
        @param db_name: name of database which is used to store information about
                        monitored documents and their versions.
        @type db_name: str
        @param http_proxy: (FUTURE USE) proxy server where to send requests
        @type http_proxy: unknown
        """
        if not isinstance(user_id, basestring) and user_id is not None:
            raise TypeError("User ID has to be type str or None.")
        # save user id
        self._user_id = user_id
        # for future use
        if http_proxy is not None:
            raise NotImplementedError("HTTP proxy not supported yet.")
        # initialize models
        self._init_models(db_host, db_port, db_name, user_id)


    def _init_models(self, host, port, db, uid):
        self._conn = Connection(host, port)
        self._storage = Storage(self._conn, uid, db)
        self._dbname = db
        self._dbport = port
        self._dbhost = host
        

    def get(self, url):
        """
        Creates new MonitoredResource instance which represents document on
        *url*.
        
        @param url: URL of monitored resource
        @type url: str
        @returns: monitored resource object bound to URL *url*.
        @rtype: MonitoredResource
        
        Design pattern: factory method.
        """
        # test the url validity
        parse_result = urlparse(url)
        if parse_result.netloc == '':
            raise ValueError("URL '%s' is not properly formatted: missing netloc." % url)
        if parse_result.scheme == '':
            raise ValueError("URL '%s' is not properly formatted: missing scheme." % url)
        # return monitored resource object
        return MonitoredResource(parse_result.geturl(), self._user_id, self._storage)


    def allow_large_documents(self):
        """
        Allow large objects to be stored in the storage. Large document is
        defined as file larger than 4096KB. Tis constant is defined in this
        module named as LARGE_DOCUMENT_SIZE representing size of the file
        in kilobytes.
        """
        try:
            # just delegate to storage model
            self._storage.allow_large_documents()
        except AttributeError:
            raise RuntimeError("Models arent initialized. Something went to hell...")
        

    def check_uid(self):
        """
        Check if user id given in constructor is a valid user id within
        the Monitor storage system. If the UID is occupied, returns False,
        True otherwise.

        If user_id is None, an exception UidError is raised.
        
        @returns: True if the UID is free
        @rtype: bool
        """
        if self._user_id is None:
            raise UidError("Cannot check uid=None. Monitor is switched to global-view mode.")
        return self._storage.check_uid()


    def check_multi(self, urls=[]):
        """
        Check list of urls, start new thread for each one.
        @param urls:
        @type urls: list
        @returns: list of MonitoredResource objects, each with actual data
        @rtype: list<MonitoredResource>
        """
        # TODO: zkontrolovat, jestli vsechny prvky v urls jsou validni URL adresy
        raise NotSupportedYet()


    def __repr__(self):
        return "Monitor(conn=%s, dbname='%s', uid='%s')" % \
            (self._conn.connection, self._dbname, self._user_id)


    __str__ = __repr__


if __name__ == "__main__":
    m = Monitor(user_id='rrs',db_port=27018) # testing on port 27018... 
                                             # USE db_port=27017 for normal use, that's the default for mongodb
#    print m
#    print "MONITOR: STORAGE: ",m._storage
#    print "MONITOR: STORAGE: HEADERS: ",m._storage._headermeta
#    print "MONITOR: STORAGE: GRIDFS: ",m._storage.filesystem    
    
    #r = m.get("http://www.fit.vutbr.cz")
    #r = m.get("http://www.google.com")
    #r = m.get("http://cs.wikipedia.org/wiki/Hlavní_strana")
    #r = m.get("http://en.wikipedia.org") 
    r = m.get("http://localhost/api.pdf")

    print "resource:",r,"\n"
#    print "checked: ", r._checked
#    print "last version: ",r.get_last_version()  # works 
#    print "last checked: ",r.last_checked(),"\n"      # works
#    print "check: ",r.check(),"\n"    
#    print "checked: ", r._checked

    # use actual times when testing!!! 
    #   otherwise will get exception DocumentHistoryNotAvailable 
#    print "by time: 2013-01-27 14:00",r.get_version(HTTPDateTime(2013,1,27,14,00)),"\n"
#    print "by time: 2013-01-30 22:00",r.get_version(HTTPDateTime(2013,1,30,22,00)),"\n"
#    print "by time: 2013-01-21 21:38",r.get_version(HTTPDateTime(2013,1,21,21,38)),"\n"
#    print "by time: 2013-01-18 23:34",r.get_version(HTTPDateTime(2013,1,18,23,34)),"\n"

#    print "by version: version 0: ",r.get_version(0) # doesn't work for version 0
#    print "by version: version 2: ",r.get_version(2)
#    print "by version: version 4: ",r.get_version(4)
    c = r.get_version(-1)
    print "by version: version -1: ", c, c.upload_date, c._differ
#    c = r.get_version(-2)
#    print "by version: version -2: ", c, c.upload_date
#    c = r.get_version(-3)
#    print "by version: version -3: ", c, c.upload_date
#    c = r.get_version(-4)
#    print "by version: version -4: ", c, c.upload_date

#    d = r.get_diff(HTTPDateTime(2013,1,30,22,00),-1)
#    print "DIFF\n"

    # EXAMPLE OF GETTING AND PRINTING A DIFF OF TWO VERSIONS
    version1 = HTTPDateTime(2013,1,30,22,00)
    version2 = -1
    c1 = r.get_version(version1)
    c2 = r.get_version(version2)
    d = r.get_diff(version1,version2)
    if d is None: 
        print "Versions ",version1," and ",version2," are equal.\n"
    elif issubclass(c1._differ,(diff.PlainTextDiff)):
        print d
    elif issubclass(c1._differ,(diff.HtmlDiff)):
        try:
            while(True):
                chunk = d.next() # htmldiff outputs a generator object
                print "pos: ",chunk.position,"\nadded: ",chunk.added,"\nremoved: ",chunk.removed,"\n----\n"
        except StopIteration: # got to last chunk generated by d
            pass 
        except TypeError: # d is not a generator object
            if d is not None: print d # htmldiff sometimes gives a basestring output...
    elif issubclass(c1._differ,(diff.BinaryDiff)):
        print "used binary diff"
        # visualisation of BinaryDiff output/metadata comes here
        print d['metainfo']
        # d['diff'] # contains the actual compressed binary delta, not human-readable 
    else:
        raise RuntimeError()

    # THIS IS ANOTHER WAY OF PRINTING THE DIFF OF TWO VERSIONS (BinaryDiff not considered here)
#    if isinstance(d, basestring): # text/plain
#        print "diff -2,-1: ",d.encode('utf-8')
#    elif d is None: 
#        print "d is None"#pass
#    else: # text/html, d should be generator object
#        try:
#            while(True):
#                chunk = d.next()
#                print "diff -2,-1: \n position: ",chunk.position,"\n added: ",chunk.added,"\n removed: ",chunk.removed
#                print "----------"
#        except (StopIteration, TypeError):
#            pass

#    print "diff times: ",r.get_diff(HTTPDateTime(2013,1,21,22,00),HTTPDateTime(2013,1,21,21,38))
#    c = r.get_version(-1) # works
#    print c.tell(), c.length
#    print c, c.read()


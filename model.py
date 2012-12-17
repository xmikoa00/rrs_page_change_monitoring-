#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Model for changemonitor -- interface for accessing the data

This module creates abstraction layer between data storage implementation
(SQL/NoSQL database/filesystem).
"""

__modulename__ = "model"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__  = "$23.6.2012 16:33:31$"

import time

from pymongo import Connection, ASCENDING, DESCENDING
from bson import ObjectId
from gridfs import GridFS
from gridfs.grid_file import GridOut

from diff import PlainTextDiff, BinaryDiff, HtmlDiff
from errors import *
from _http import HTTPDateTime


class BaseMongoModel(object):
    """
    Serves as base class, which is inherited by every model class.
    """
    pass


class Storage(BaseMongoModel):
    """
    Abstraction of the storage. The purpose of this class is to create abstraction
    layer, which provides database-independent API for manipulation in the
    filesystem. The only requirement on the filesystem is that it has to support
    file versioning (or some workaround which implements versioning within the
    fs which does not support versioning natively).

    The implementation is nowadays built on MongoDB.

    Usage:
        >>> from pymongo import Connection
        >>> from model import Storage
        >>> store = Storage(Connection(), "myuid", "webarchive")
        >>> file = store.get("http://www.myfancypage.com/index.html")
        >>> # get last version of the file, which is available in the storage
        >>> c = file.get_last_content()
        >>> # get the raw data
        >>> c.data
        "<html>
        ...
        >>> # content type and content length
        >>> print c.content_type, c.length
        'text/html' 29481

    Design pattern: Factory
    """

    def __init__(self, connection, uid, database="webarchive"):
        """
        Initializes storage.

        @param connection: database connection
        @type connection: pymongo.Connection
        @param uid: user id (see Monitor.__doc__ for more info)
        @type uid: str
        @param database: if the storage is based on database, this param
                         represents the name of database to be used within
                         this instance.
        @type database: str
        """
        if not isinstance(connection, Connection):
            raise TypeError("connection must be instance of pymongo.Connection.")
        self._connection = connection
        self._database = database
        self._uid = uid
        # instance of HTTP header model
        self._headermeta = HttpHeaderMeta(connection, uid, database)
        # filesystem interface
        self.filesystem = GridFS(self._connection[database], "content")
#?        print "STORAGE: FILESYSTEM: ",self.filesystem
        # flag representing possibility to save large objects into storage
        self.allow_large = False

    def allow_large_documents(self):
        """
        Allow large objects to be stored in the storage.
        """
        self.allow_large = True

    def get(self, filename):
        """
        Get file object by filename.

        @param filename: name of the file. In this case, it will be URL.
        @type filaname: str
        @returns: File object representing file in many versions
        @rtype: File
        @raises: DocumentNotAvailable if document doesnt exist in the storage
        """
#?        print "In Storage.get(): resource ",filename
        if not self.filesystem.exists(filename=filename):
            raise DocumentNotAvailable("File does not exist in the storage.")
        return File(filename, self.filesystem, self._headermeta)


    def check_uid(self):
        return self._headermeta.check_uid()


class _ContentCache(object):
    """
    A small app-specific key-value cache for storing readable objects.

    Main feature:
        - iterable read(): when getting the stored object from the cache,
                           it will check if the readable object is at the end.
                           If yes, seeks to the beginning.
        - refreshable: calling refresh() method deletes all integer-key values
                       from the cache.
    """
    def __init__(self):
        self.__contents = {}

    def __getitem__(self, key):
        try:
            c = self.__contents[key]
        except KeyError:
            raise LookupError("No such content in the cache.")
        # if fd is at the end, seek to beginning
        if c.tell() == c.length:
            c.seek(0)
        return c

    def __setitem__(self, key, value):
        self.__contents[key] = value

    def __contains__(self, key):
        return key in self.__contents

    def __iter__(self):
        for x in self.__contents:
            yield x

    def refresh(self):
        for version in filter(lambda x: isinstance(x, int), self.__contents.keys()):
            del self.__contents[version]

    def purge(self):
        self.__contents = {}


class File(object):
    """
    One file in filesystem. A file can contain more contents in various
    versions. Main purpose of this class is to get rid of GridFS
    and GridOut instances and replace it with file-like wrapper.

    MongoDB record:
    content = {
        filename: URL
        md5: str
        sha1: str
        content_type: str
        length: int
        urls = []
    }

    Design pattern: Active Record
    """
    # Zde se jedna v podstate o obal GridFS a GridOut
    #
    def __init__(self, filename, fs, headermeta):
        """
        Create new file instance.

        @param filename: name of the file
        @type filename: basestring (str or unicode)
        @param fs: filesystem object
        @type fs: GridFS
        @param headermeta: http header metadata
        @type headermeta: HttpHeaderMeta

        WARNING:
        Application developers should generally not need to instantiate this class
        directly. The only correct way how to get this object is using Storage.get()
        method.
        """
        self.filename = filename
        # GridFS
        self._filesystem = fs
        # Collection "httpheader"
        self._headers = headermeta

        # ulozeno vzdy jednak pod _id a po verzemi -1,-2,-3 pokud se uzivatel
        # ptal  na verzi
        self.content = _ContentCache()

    def purge_cache(self):
        """
        Cleans the whole content cache.
        """
        self.content.purge()

    def refresh_cache(self):
        """
        Refreshes part of cache, which can potentionally change (version pointers).
        This is very useful if we expect the File object to live during more than
        one check() call. If so, the information about version has to be updated
        in the cache (version -1 becomes -2 etc.).
        
        This method should be called after every check() call!
        """
        self.content.refresh()

    def get_version(self, timestamp_or_version):
        """
        Get content of the file in specific version. Version can be specified
        by version number (convenience atop the GridFS API by MongoDB) or
        unix timestamp.

        @param timestamp_or_version: version or timestamp of version which we
                                     want to retrieve.
        @type timestamp_or_version: int
        @return: content of the file in specified time/version
        @rtype: Content
        @raises: DocumentHistoryNotAvaliable if no such version in database
        """
        if not isinstance(timestamp_or_version, (int, float)):
            raise TypeError("timestamp_or_version must be float or integer")

        # version
        if timestamp_or_version < 10000:

            # try to get content from cache by version
            if timestamp_or_version in self.content:
                return self.content[timestamp_or_version]

            h = self._headers.get_by_version(self.filename, timestamp_or_version,
                                             last_available=True)
            if h is None:
                raise DocumentHistoryNotAvaliable("Version %s of document %s is"\
                    " not available." % (timestamp_or_version, self.filename))
            print "Document: ",h
            # try to get content from cache by content ID
            content_id = h['content'] # ObjectiId
            if content_id in self.content:
                return self.content[content_id]
            print "Content_id: ",h['content']
            # otherwise load content from db
            #g = self._filesystem.get(content_id) # GridOut
            g = self._filesystem.get_version(filename=self.filename,version=timestamp_or_version)
            # cache it
            r = self.content[content_id] = self.content[timestamp_or_version] = Content(g)

        # timestamp
        else:
            h = self._headers.get_by_time(self.filename, timestamp_or_version,
                                          last_available=True)
            print "Document: ",h
            if h is None:
                t = HTTPDateTime().from_timestamp(timestamp_or_version)
                raise DocumentHistoryNotAvaliable("Version of document %s in time"\
                " %s is not available." % (self.filename, t.to_httpheader_format()))
            
            # try to get content from cache by content ID
            content_id = h['content'] # ObjectiId
            if content_id in self.content:
                return self.content[content_id]

            # otherwise load content from db
            content_id = h['content'] # ObjectiId
            print "Content_id: ",h#['content']
            #g = self._filesystem.get(content_id) # GridOut
            g = self._filesystem.get_version(filename=self.filename,version=-1) # this gets the last version... FIX
            r = self.content[content_id] = Content(g) # cache it
        
        # return the content, which was requested
        return r

    def get_last_version(self):
        """
        Loads the last version of the file which is available on the storage.
        If the monitor is in user-view mode, loads last version, which was
        checked by specified user.

        @returns: most recent content of the file which is on the storage.
        @rtype: Content
        """
        return self.get_version(-1)


class Diffable(object):
    """
    Interface-like class. A class, which inherites this interface, has to
    implement the method for diffing two objects and choose of a diff
    algorithm.
    """
    def diff_to(self, obj):
        raise NotImplementedError("Interface Diffable needs to be implemented")


class Content(Diffable):
    """
    Content of web document in one version.

    Implements Diffable interface to get possibility to diff contents to each
    other. Differ algorithm is choosen automatically.

    Implementation detail: wrapper of GridOut instance.
    """
    def __init__(self, gridout):
        """
        Create new instance of content.

        WARNING: Do not instantiate this class by yourself, this is done by
                 File methods.
        @param gridout: gridout instance which was retrieved by GridFS.
        @type  gridout: gridfs.grid_file.GridOut
        """
        if not isinstance(gridout, GridOut):
            raise TypeError("gridout has to be instance of GridOut class.")
        self._gridout = gridout
        self._differ = self._choose_diff_algorithm()
        
    def __getattr__(self, name):
        try:
            return getattr(self._gridout, name)
        except AttributeError:
            raise AttributeError("Content object has no attribute %s" % name)

    def diff_to(self, other):
        """
        Creates diff of self and given Content object and returns unicode string
        representing the computed diff:
        $ diff-algo self obj
        @param other: diffed content
        @type other: Content
        @returns: computed diff
        @rtype: unicode
        """
        if not isinstance(other, Content):
            raise TypeError("Diffed object must be an instance of Content")
        return self._differ.diff(self.read(), other.read())

    def _choose_diff_algorithm(self):
        """
        Choose appropriate algorithm for diffing this content.
        @returns: algorithm-class wrapper, which will serve for diffing
        @rtype: subclass of diff.DocumentDiff (see diff.py for more)
        """
        # bude navracet PlainTextDiff, BinaryDiff atp.
        print "self._gridout.content_type: ",self._gridout.content_type
        assert '/' in self._gridout.content_type
        type_, subtype = self._gridout.content_type.split('/')
        if type_ == 'text':
            if subtype == 'html':
                return HtmlDiff
            else:
                return PlainTextDiff
        else:
            return BinaryDiff

    def __repr__(self):
        return "<Content(_id='%s', content_type='%s', length=%s) at %s>" % \
                (self._id, self.content_type, self.length, hex(id(self)))

    __str__ = __repr__


class HttpHeaderMeta(BaseMongoModel):
    """
    Model for HTTP header metadata.

    header = {
      timestamp: 1341161610.287
      response_code: 200
      last_modified: cosi
      etag: P34lkdfk32jrlkjdfpoqi3
      uid: "rrs_university"
      url+index: "http://www.cosi.cz"
      content: object_id
    }

    """

    def __init__(self, connection, uid, database):
        self._connection = connection
        # type pymongo.Collection
        self.objects = self._connection[database].httpheader
        # user id
        self.uid = uid

    def get_by_time(self, url, timestamp, last_available=False):
        """
        @TODO: docstring
        Get record of 'url' with 'timestamp' from HeaderMeta database
        @param url: url of resource to search for
        @type url: string
        @param timestamp:
        @type timestamp: int  
        @param last_available:
        @type last_available: Bool
        @returns: http header metadata of 'url'/None if not found  
        @rtype:
        """
        q = {"url": url, "timestamp":{"$lt": timestamp}}
        if self.uid is not None:
            q["uid"] = self.uid
        if last_available:
            q["response_code"] = {"$lt":400}
            q["content"] = {"$exists" : True}
        try:
            return self.objects.find(q).sort('timestamp',DESCENDING)[0]
        except IndexError:
            print "in httpheader:getversion: IndexError"
            return None

    def get_by_version(self, url, version, last_available=False):
        """
        @TODO: docstring
        Get 'version' of 'url' from HeaderMeta database 
        @param url: url of resource to get from db
        @type url: string
        @param version: version number of record, ...TODO: x,-x,1,0,-1
        @type version: int
        @param last_available:
        @type last_available: bool
        @returns: http header metadata of 'url'/None if not found
        @rtype:
        """
        q = {"url": url}
        if self.uid is not None:
            q["uid"] = self.uid
        if last_available:
            q["response_code"] = {"$lt":400}
            q["content"] = {"$exists" : True}
        try:
            c = self.objects.find(q).sort('timestamp', ASCENDING).count()
            skip_ = c+version if version < 0 else c-version
            return self.objects.find(q).sort('timestamp', ASCENDING).skip(skip_).limit(1)[0]
        except IndexError:
            return None

    def save_header(self, url, response_code, fields, content_id):
        """
        Save http header into HttpHeaderMeta database
        @param url: url of checked resource
        @param response_code: response code of web server
        @param fields: fields of http response
        @param content_id: content-id field of http response
        @returns: saved object
        """
        h = {
            "timestamp": time.time(),
            "url": url,
            "response_code": int(response_code),
            "uid": self.uid
        }
        if content_id is not None:
            print "save_header: content_id: ",content_id
            h['content'] = content_id
        for f in fields:
            if f.lower() in ('etag', 'last-modified'):
                h[f.lower().replace("-", "_")] = fields[f]
        return self.objects.save(h)

    def last_checked(self, url):
        """
        Get time when 'url' was last checked
        WARNING! 
          if None is returned, then 'url' was never checked
          that should never happen, as 'url' is always checked 
          in constructor of MonitoredResource
          but it's possible that the header is not saved 
          because of an error, eg. timeout or other
        @param url: url of resource checked
        @type url: string
        @returns: time of last check
        @rtype: HTTPDateTime
        """
        # Pokud vrati None, pak tento zdroj nebyl NIKDY checkovan, coz by se
        # nemelo moc stavat, protoze vzdy je checknut na zacatku v konstruktoru
        # MonitoredResource POZOR! je ale mozne, ze se header neulozi, protoze
        # treba vyprsi timeout.
        r = self.get_by_time(url, time.time(), last_available=False)
        if r is None:
            return None
        return HTTPDateTime().from_timestamp(r['timestamp'])

    def check_uid(self):
        assert self.uid is not None
        return self.objects.find_one({"uid": self.uid}) is not None


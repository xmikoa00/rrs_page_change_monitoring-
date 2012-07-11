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
from gridfs import GridFS
from gridfs.grid_file import GridOut

from diff import PlainTextDiff, BinaryDiff
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
        if not self.filesystem.exists(filename=filename):
            raise DocumentNotAvailable("File does not exist in the storage.")
        return File(filename, self.filesystem, self._headermeta)


    def check_uid(self):
        return self._headermeta.check_uid()


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

        # TODO: mozna slovnik contentu v ruznych verzich
        # Ukladat se bude vzdycky jen content podle jeho _id, coz uspori to,
        # ze nebudeme muset z databaze tahat vzdycky cely content, ale staci ziskat
        # jen z headers info o tom, ktery _id mame tahat. Pokud toto _id uz budeme
        # mit nacachovane, nemusime ho tahat z db.
        self.content = None

    def get_content(self):
        """
        @TODO: docstring
        """
        if self.content is None:
            raise ValueError("File has no content.")
        return self.content

    def get_version(self, timestamp_or_version):
        """
        @TODO: docstring
        """
        if not isinstance(timestamp_or_version, (int, float)):
            raise TypeError("timestamp_or_version must be float or integer")
        # version
        if timestamp_or_version < 10000:
            h = self._headers.get_by_version(self.filename, timestamp_or_version,
                                             last_available=True)
            if h is None:
                raise DocumentHistoryNotAvaliable("Version %s of document %s is"\
                    " not available." % (timestamp_or_version, self.filename))
        # timestamp
        else:
            h = self._headers.get_by_time(self.filename, timestamp_or_version,
                                          last_available=True)
            if h is None:
                t = HTTPDateTime().from_timestamp(timestamp_or_version)
                raise DocumentHistoryNotAvaliable("Version of document %s in time"\
                " %s is not available." % (self.filename, t.to_httpheader_format()))
        # GridOut
        g = self._filesystem.get(h['content'])
        self.content = Content(g)
        return self.content

    def get_last_version(self):
        """
        Loads the last version of the file which is available on the storage.

        @returns: most recent content of the file which is on the storage.
        @rtype: Content
        """
        g = self._filesystem.get_last_version(self.filename)
        self.content = Content(g)
        return self.content

    def get_older_version(self):
        raise NotSupportedYet()

    def get_newer_version(self):
        raise NotSupportedYet()


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

    def __getattr__(self, name):
        try:
            return getattr(self._gridout, name)
        except AttributeError:
            raise AttributeError("Content object has no attribute %s" % name)

    def diff_to(self, obj):
        """
        Creates diff of self and given Content object and returns unicode string
        representing the computed diff:
        $ diff-algo self obj

        @param obj: diffed content
        @type obj: Content
        @returns: computed diff
        @rtype: unicode
        """
        if not isinstance(obj, Content):
            raise TypeError("Diffed object must be an instance of Content")
        raise NotImplementedError()

    def _choose_diff_algorithm(self):
        """
        Choose appropriate algorithm for diffing this content.
        @returns: algorithm-class wrapper, which will serve for diffing
        @rtype: subclass of diff.DocumentDiff (see diff.py for more)
        """
        # bude navracet PlainTextDiff, BinaryDiff atp.
        raise NotImplementedError()

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
            return None

    def get_by_version(self, url, version, last_available=False):
        """
        @TODO: docstring
        """
        q = {"url": url}
        if self.uid is not None:
            q["uid"] = self.uid
        if last_available:
            q["response_code"] = {"$lt":400}
            q["content"] = {"$exists" : True}
        try:
            return [x for x in self.objects.find(q).sort('timestamp',ASCENDING)][version]
        except IndexError:
            return None

    def save_header(self, url, response_code, fields, content_id):
        """
        @TODO: docstring
        """
        h = {
            "timestamp": time.time(),
            "url": url,
            "response_code": int(response_code),
            "content": content_id,
            "uid": self.uid
        }
        for f in fields:
            if f.lower() in ('etag', 'last-modified'):
                h[f.lower().replace("-", "_")] = fields[f]
        return self.objects.save(h)

    def last_checked(self, url):
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



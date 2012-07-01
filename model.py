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


from pymongo import Connection
from gridfs import GridFS
from gridfs.grid_file import GridOut

from diff import PlainTextDiff, BinaryDiff
from errors import *


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
        self._allow_large = False

    def allow_large_documents(self):
        """
        Allow large objects to be stored in the storage.
        """
        self._allow_large = True

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
        # content: instance of Content
        # TODO: mozna slovnik contentu v ruznych verzich (jak to ukladat? podle
        # cisla verze nebo jak?)
        self.content = None

        # TODO: rovnou v konstruktoru volat get_last_version?? Asi ne, radeji lazy
        
        # TODO: ukladat do objektu informaci o tom, kdy naposledy se tato URL
        # kontrolovala? Treba na zaklade toho potom rejectovat dotazy mladsi nez
        # 10 sekund

    def get_content(self):
        if self.content is None:
            raise ValueError("File has no content.")
        return self.content

    def get_version(self, timestamp_or_version):
        # TODO: check typu timestamp a version

        # TODO: jak to bude s userem tady??
        # Use cases co se tyce uzivatele: (parove, rozdelit na user-view a global-view)
        # 1u) Chci vedet, co se zmenilo od toho, kdy jsem tu byl naposledy
        # 1g) Chci vedet, co se zmenilo od doby, kdy tu nekdo byl
        # 2u) Chci vedet, jestli se neco zmenilo od doby, kdy jsem to checkoval naposledy
        # 2g) Chci vedet, jetsli se neco zmenilo od doby, to bylo naposledy (nekym) kontrolovano
        # =====> Pokud user_id v konstruktoru je None, pak se bere global-view

        h = self._headers.get_by_time(self.filename, timestamp, last_available=True)
        if h is None:
            raise DocumentHistoryNotAvaliable("Document %s was not available in time %s" %
                (self.filename, timestamp))
        g = self._filesystem.get(_id=h['_id']) # GridOut
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
        raise NotSupportedYet()

    def _choose_diff_algorithm(self):
        """
        Choose appropriate algorithm for diffing this content.
        @returns: algorithm-class wrapper, which will serve for diffing
        @rtype: subclass of diff.DocumentDiff (see diff.py for more)
        """
        # bude navracet PlainTextDiff, BinaryDiff atp.
        pass

    def __repr__(self):
        return "<Content(_id='%s', content_type='%s', length=%s) at %s>" % \
                (self._id, self.content_type, self.length, hex(id(self)))

    __str__ = __repr__


class HttpHeaderMeta(BaseMongoModel):
    """
    TODO: docstring
    
    header = {
      timestamp: 13452345646
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
        if last_available:
            return self.objects.find_one({"url": url, "uid": self.uid,
                                          "timestamp":{"$gt": timestamp},
                                          "response_code":{"$lt":400}})
        else:
            return self.objects.find_one({"url": url, "uid": self.uid,
                                          "timestamp":{"$gt": timestamp}})

    def check_uid(self, uid):
        pass

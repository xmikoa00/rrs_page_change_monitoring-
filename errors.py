#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Exceptions raised by rrslib.web.changemonitor package
"""

__modulename__ = "errors"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__  = "$22.6.2012 13:01:57$"


class ChangeMonitorError(Exception):
    """
    Base error class for all exceptions within this package.
    """
    pass

class DocumentTooLarge(ChangeMonitorError):
    """
    Raised when monitored document's size exceeds the LARGE_DOCUMENT_SIZE
    constant.
    """
    pass

class DocumentNotAvailable(ChangeMonitorError):
    """
    Raised when document is not available on the URL or on the storage.
    """
    pass

class DocumentHistoryNotAvaliable(ChangeMonitorError):
    """
    Raised when trying to get version or diff of document, which version
    history is not stored in the storage.
    """
    pass

class NotSupportedYet(ChangeMonitorError):
    """
    Raised when the method/class/function is not supported in this
    implementation.
    """
    pass

class UidError(ChangeMonitorError):
    """
    Raised when some error connected with user id occured.
    """
    pass

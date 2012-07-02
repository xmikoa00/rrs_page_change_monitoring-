#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Maly privatni modul zajistujici HTTP pozadavky pro changemonitor.
Obsahuje maly middleware, ktery slouzi k odstineni changemonitoru od nizsi
vrstvy HTTP a ktery poskytne moznost pohodlnejsiho testovani nebo cachovani.

"""

__modulename__ = "_http"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__  = "$22.6.2012 13:01:57$"

from datetime import datetime
import time
import httplib
from urlparse import urlsplit

class _HTTPRequestProxy(object):
    """
    Mezivrstva pro pristup k internetu.
    Zde je nutne implementovat:
        - zakladni pripojeni a poslani requestu
        - moznost pridani ruznych hlavicek (v konstruktoru)
        - moznost nastaveni timeoutu
        - handlery pro presmerovani
        - handlery pro cookies

    Zde je mozne implementovat:
        - pristup k rrs_proxy (soucast reresearch)
        - zjednoduseni testovani: misto posilani pozadavku do site nejaky
        druh asociativni pameti ktery bude posilat testovaci a navracet data
        - malou pomocnou cache, ktera by redukovala velke mnozstvi stejnych
        pozadavku na databazi

    Navrhovy vzor: Proxy pattern.
    """
    def __init__(self, method, url, headers, timeout):
        """
        @param method: HTTP method (GET/HEAD...)
        @type method: str
        @param url: requested URL
        @type url: basestring (str or unicode)
        @param headers: sent HTTP headers
        @type headers: dict
        @returns: new instance
        """
        pass

    def send(self):
        """
        Send this request and return HTTP response.
        """
        #splitted_url = urlsplit(url)
        #conn = httplib.HTTPConnection(splitted_url.netloc, timeout=timeout)
        # user agent has to be some valid web browser
        # thus we lie about ourselves, but it is the only way how to get results
        #_ua = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2010040116 Ubuntu/9.04 (jaunty) Firefox/3.0.19'
        #headers = {"Connection": "close",
        #           "User-Agent": _ua}
        #req_url = splitted_url.path
        #if splitted_url.query:
        #    req_url += '?' + splitted_url.query
        #try:
        #    conn.request("HEAD", req_url, headers=headers)
        #    # get headers from response
        #    return conn.getresponse().getheaders()
        #except socket.timeout:
        #    return None
        #except IOError:
        #    return None


class HTTPDateTime(object):
    """
    Datetime class for manipulating time within HTTP enviroment.

    Usage:
    >>> h = HTTPDateTime()
    >>> h
    HTTPDateTime(Thu, 01 Jan 1970 00:00:00 GMT)
    >>> h.now()
    >>> h
    HTTPDateTime(Sat, 30 Jun 2012 16:09:43 GMT)
    >>> h.to_httpheader_format()
    'Sat, 30 Jun 2012 16:09:43 GMT'

    FIXME: solve the problem with GMT:
    >>> h = HTTPDateTime()
    >>> h.to_timestamp()
    -7200.0
    # WTF?
    """
    def __init__(self, year=1970, month=1, day=1, hour=0, minute=0, second=0, microsecond=0):
        self._datetime = datetime(year, month, day, hour, minute, second, microsecond)

    def to_httpheader_format(self):
        """
        Converts this object into date and time in HTTP-header format.

        @returns: date and time in HTTP format, i.e. 'Wed, 31 Aug 2011 16:45:03 GMT'.
        @rtype: str
        """
        return self._datetime.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def from_httpheader_format(self, timestr):
        """
        Parse http header datetime format and save into this object.

        @param timestr: date and time in format which is used by HTTP protocol
        @type timestr: str
        @returns: HTTPDateTime object equivalent to date and time of the timestr
        @rtype: HTTPDateTime
        """
        ts = time.strptime(timestr, "%a, %d %b %Y %H:%M:%S GMT")
        self.from_timestamp(time.mktime(ts))
        return self

    def to_timestamp(self):
        """
        Convert into UNIX timestamp. (seconds since start of the UNIX epoch).

        @returns: unix timestamp
        @rtype: float
        """
        ts = time.strptime(str(self._datetime.year) + '-' + str(self._datetime.month) + \
            '-' + str(self._datetime.day) + 'T' + str(self._datetime.hour) + ':' + \
            str(self._datetime.minute) + ':' + str(self._datetime.second) + \
            " GMT" , '%Y-%m-%dT%H:%M:%S %Z')
        return time.mktime(ts) - 3600 + (self._datetime.microsecond / 1000000.0)

    def from_timestamp(self, timestamp):
        """
        Set date and time from timestamp.

        @param timestamp: time since start of the unix epoch
        @type timestamp: float
        @returns: HTTPDateTime object representing date and time of the timestamp
        @rtype: HTTPDateTime
        """
        self._datetime = datetime.fromtimestamp(timestamp)
        return self

    def to_datetime(self):
        """
        Convert the date and time from this object into python's datetime.datetime.

        @returns: datetime object equivalent to date and time of this object
        @rtype: datetime.datetime
        """
        return self._datetime

    def from_datetime(self, datetimeobj):
        self._datetime = datetimeobj
        return self

    def now(self):
        """
        Set the time of this object as current time (time.time())

        @returns: HTTPDateTime object representing current date and time.
        @rtype: HTTPDateTime
        """
        self.from_timestamp(time.time())
        return self

    def __repr__(self):
        return "HTTPDateTime(%s)" % self.to_httpheader_format()


if __name__ == "__main__":
    h = HTTPDateTime()
    print h
    print h.to_timestamp()
    s = time.time()
    print h.from_timestamp(s)
    print h.to_timestamp(), s
    l = h.to_httpheader_format()
    print l
    h.from_httpheader_format(l)
    print h.to_httpheader_format()


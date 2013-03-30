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
import socket
from threading import Semaphore


class _HTTPConnectionProxy(object):
    """
    Mezivrstva pro pristup k internetu.
    Zde je nutne implementovat:
        - zakladni pripojeni a poslani requestu
        - moznost pridani ruznych hlavicek
        - moznost nastaveni timeoutu
        - handlery pro presmerovani
        - handlery pro cookies

    Zde je mozne nekdy v budoucnu implementovat:
        - pristup k rrs_proxy (soucast reresearch)
        - zjednoduseni testovani: misto posilani pozadavku do site nejaky
        druh asociativni pameti ktery bude posilat testovaci a navracet data
        - malou pomocnou cache, ktera by redukovala velke mnozstvi stejnych
        pozadavku na databazi

    Navrhovy vzor: Proxy pattern.
    """

    # pretending a proper web browser
    # 1-1 copy of headers sent by Google Chrome run on Ubuntu Linux
    # only 'accept-encoding' was changed in order not to be bothered with decompression
    default_header = {
            "connection":"keep-alive",
            "cache-control":"max-age=0",
            "user-agent":"Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0",
            "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-encoding":"identity",
            "accept-language":"en-US,en;q=0.8",
            "accept-charset":"ISO-8859-1;q=0.7,*;0.3"
        }

    default_max_redirects = 10

    def __init__(self,url,timeout=None):
        """
        @param url: requested URL (only server name is taken in account now)
        @type url: basestring
        @param timeout: timeout applied to requests in this connection (None sets default from httplib/socket)
        @type timeout: number
        """
        self.netloc = urlsplit(url).netloc
        self.timeout = timeout



    def send_request(self, method, url, headers=default_header, max_redirects=default_max_redirects):
        """
        @param method: HTTP method (GET/HEAD...)
        @type method: str
        @param url: requested URL (net location must not differ from the one passed to the constructor)
        @type url: basestring (str or unicode)
        @param headers: sent HTTP headers (defaults to pretending a web browser)
        @type headers: dict
        @param max_redirects: sets the maximum number of redirects to be followed
        @type max_redirects: number (only non-negative integers make sense here)
        @returns: 4-tuple of (response code recieved from the (last in case\
of redirection) server) and (dictionary of retrieved headers or None if none\
arrived) and (string containing body of the response -- empty for HEAD\
requests) and (final URL).
        """
        actual_url = url
        num_redirects = 0

        # loop handling redirects
        while True:
            splitted_url = urlsplit(actual_url)

            # we only check url against the one got from constructor before redirects
            if num_redirects == 0 and splitted_url.netloc != self.netloc:
                raise ValueError("Net location of the query doesn't match the one this connection was established with")

            # we are making connection for every single request to avoid
            # problems with reuse. Actually it is neccessary for following
            # redirects.
            if self.timeout != None:
                conn = httplib.HTTPConnection(splitted_url.netloc, timeout=self.timeout)
            else:
                conn = httplib.HTTPConnection(splitted_url.netloc)

            # build a path identifying a file on the server
            req_url = splitted_url.path
            if splitted_url.query:
                req_url += '?' + splitted_url.query

            try:
                conn.request(method, req_url, headers=headers)
            except socket.timeout as e:
#?                print "Timeout (%s)" % (e)
                return None
            except socket.error as e:
#?                print "A socket error(%s)" % (e)
                return None
            response = conn.getresponse()

            # get headers from response and build a dict from them
            retrieved_headers = {}
            for header_tuple in response.getheaders():
                retrieved_headers[header_tuple[0]] = header_tuple[1]

            if response.status >= 400:
                return (response.status, retrieved_headers, response.read(), actual_url)


            # following redirections
            if response.status in [301,302,303]:
                if 'location' in retrieved_headers and num_redirects < max_redirects:
                    actual_url = retrieved_headers['location']
                    num_redirects += 1
                    continue
                else:
                    return (response.status, retrieved_headers, response.read(), actual_url)

            # only "succesful" exit point of the loop and thus of the whole method
            if response.status == 200:
                return (response.status, retrieved_headers, response.read(), actual_url)

            # an unknown response code
            return (response.status, retrieved_headers, response.read(), actual_url)


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
    strptime_lock = Semaphore() # lock for time.strptime method

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
        self.__class__.strptime_lock.acquire()
        ts = time.strptime(timestr, "%a, %d %b %Y %H:%M:%S GMT")
        self.__class__.strptime_lock.release()

        self.from_timestamp(time.mktime(ts))
        return self

    def to_timestamp(self):
        """
        Convert into UNIX timestamp. (seconds since start of the UNIX epoch).

        @returns: unix timestamp
        @rtype: float
        """
        timestr = (str(self._datetime.year) + '-' + str(self._datetime.month) + \
            '-' + str(self._datetime.day) + 'T' + str(self._datetime.hour) + ':' + \
            str(self._datetime.minute) + ':' + str(self._datetime.second) + \
            " GMT")
        self.__class__.strptime_lock.acquire() 
        ts = time.strptime(timestr, '%Y-%m-%dT%H:%M:%S %Z')
        self.__class__.strptime_lock.release()

#        return time.mktime(ts) - 3600 + (self._datetime.microsecond / 1000000.0)
        return time.mktime(ts) + (self._datetime.microsecond / 1000000.0)

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

    def from_gridfs_upload_date(self, upload_date):
        """
        Convert the date and time from grid_file.update_date string 
        to HTTPDateTime object.

        @param update_date: time string from grid_file.update_date
        @returns: HTTPDateTime object representing date and time of update_date
        @rtype: HTTPDateTime
        """
        self.__class__.strptime_lock.acquire()
        ts = time.strptime((str(upload_date))[:18],"%Y-%m-%d %H:%M:%S")
        self.__class__.strptime_lock.release()

        self.from_timestamp(time.mktime(ts))
        return self

    def now(self):
        """
        Set the time of this object as current time (time.time())

        @returns: HTTPDateTime object representing current date and time.
        @rtype: HTTPDateTime
        """
        self._datetime = datetime.now()
        return self

    def __repr__(self):
        return "HTTPDateTime(%s)" % self.to_httpheader_format()

    def __lt__(self, other):
        return self._datetime.__lt__(other._datetime)

    def __le__(self, other):
        return self._datetime.__le__(other._datetime)

    def __eq__(self, other):
        return self._datetime.__eq__(other._datetime)

    def __ne__(self, other):
        return self._datetime.__ne__(other._datetime)

    def __gt__(self, other):
        return self._datetime.__gt__(other._datetime)

    def __ge__(self, other):
        return self._datetime.__ge__(other._datetime)


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


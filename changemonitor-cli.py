#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Command line interface to changemonitor module
"""

# author: Albert Mikó, xmikoa00@stud.fit.vutbr.cz

import sys
from changemonitor import Monitor


def main():
    """
    TODO: docstring
    """
    # process cmd arguments

    # init Monitor
    m = Monitor(user_id=uid)
    
    # do something useful based on cmd arguments
    pass

def test_check_multi():
    """
    Test function for Monitor.check_multi() method
    """
    m = Monitor(user_id='rrs')

    url_list = []
#    url_list.append("http://www.google.com")
    url_list.append("http://www.fit.vutbr.cz")
#    url_list.append("http://en.wikipedia.org")

    r_list = m.check_multi(url_list)
    
    for r in r_list:
        r.check()
        print r.url,":",r.last_checked()


    exit(0)


if __name__ == "__main__":
    # main()
    test_check_multi()

#EOF

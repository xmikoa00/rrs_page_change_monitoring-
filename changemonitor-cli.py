#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Command line interface to changemonitor module
"""

# author: Albert Mikó, xmikoa00@stud.fit.vutbr.cz

import sys
from changemonitor import Monitor


def main():
    pass

def test_check_multi():
    m = Monitor(user_id='rrs')

    url_list = []
    url_list.append("http://localhost/1.txt")
    url_list.append("http://localhost/2.txt")

    r_list = m.check_multi(url_list)

    exit(0)


if __name__ == "__main__":
    # main()
    test_check_multi()

#EOF

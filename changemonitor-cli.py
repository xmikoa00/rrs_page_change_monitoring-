#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Command line interface to changemonitor module
"""

# author: Albert Mikó, xmikoa00@stud.fit.vutbr.cz

import sys
import argparse
from changemonitor import Monitor

def init_monitor(args):
    """
    initialize Monitor object
    set uid, db name and port
    @return Monitor object
    """
    pass

def url_check(args,monitor):
    """
    check functionality
    """
    pass

def url_diff(args,monitor):
    """
    diff of two versions of the same url
    """
    pass

def url_print(args,monitor):
    """
    print contents of url, version in db or given by time
    """
    pass

def url_available(args,monitor):
    """
    check availability of url at given time
    @return True/False
    """
    pass



def parse_args():
    """
    parse command line arguments
    @return argparse.Namespace object
    """
    parser = argparse.ArgumentParser(
        description="RRS changemonitor commandline interface",
        add_help=True
        )
    # specify global values
    parser.add_argument("--uid",default="rrs",help="user id")
    parser.add_argument("--db",default="webarchive",help="name of database")
    parser.add_argument("--port",default=27017,type=int,help="port of database server")

    # specify url(s) to perform action on
    url_list = parser.add_mutually_exclusive_group(required=True)
    url_list.add_argument("--url",help="specify a single url")
    url_list.add_argument("--list",help="specify a file with urls to check")

    #subparsers for individual actions
    subparsers = parser.add_subparsers(title="subcommands",dest="action")

    # check if version in database is up to date, and actualize if necessary
    parser_check = subparsers.add_parser("check",
        help="check documents at specified url(s)")
    parser_check.add_argument("--force",action="store_true",
        help="force download of content")
    parser_check.set_defaults(func=url_check)

    # find differences between versions A and B of the same document
    parser_diff = subparsers.add_parser("diff",
        help="diff of versions of document at given url")
    parser_diff_v_or_t = parser_diff.add_mutually_exclusive_group(required=True)
    parser_diff_v_or_t.add_argument("-v",nargs=2,type=int,
        help="version by version numbers")
    parser_diff_v_or_t.add_argument("-t",nargs=2,help="version by timestamps")
    #parser_diff.add_argument("A",help="specify first version of document")
    #parser_diff.add_argument("B",help="specify second version of document")
    parser_diff.set_defaults(func=url_diff)

    # print out the contents of document saved in database
    parser_print = subparsers.add_parser("print",
        help="output document at url from database")
    parser_print_v_or_t = parser_print.add_mutually_exclusive_group()
    parser_print_v_or_t.add_argument("-v",help="version by version numbers")
    parser_print_v_or_t.add_argument("-t",help="version by timestamps")
    parser_print.set_defaults(func=url_print)

    # check if document at url was available at the specified time
    parser_available = subparsers.add_parser("available",
        help="check if document at url was available at given time")
    parser_available.add_argument("-t",help="specify time")    
    parser_available.set_defaults(func=url_available)

    return parser.parse_args()

def main():
    """
    TODO: docstring
    """
    # process cmd arguments
    print "parsing arguments: ",sys.argv
    args = parse_args()

    # init Monitor
#    monitor = init_monitor(args)    
    
    # do something useful based on cmd arguments
#    args.func(args,monitor)

if __name__ == "__main__":
    main()

#EOF

#!/usr/bin/env python

# -*- encoding: utf-8 -*-
import pickle
import argparse
import sys

import eventlet
from keystoneclient.v2_0 import client as ksclient

sys.path.append("../")
from common.utils import get_config
from sync.filler import (load_index, load_containers_index,
                         create_swift_account, fill_swift,
                         delete_account_content, delete_account)


def main():
    parser = argparse.ArgumentParser(prog='swift-filler', add_help=True)
    parser.add_argument('--delete',
                        action='store_true',
                        help='Suppress created accounts/users')
    parser.add_argument('--create',
                        action='store_true',
                        help='Create account/users/containers/data')
    parser.add_argument('-l',
                        action='store_true',
                        help='Load previous indexes and append newly'
                        ' created to it')
    parser.add_argument('-a',
                        help='Specify account amount')
    parser.add_argument('-u',
                        help='Specify user amount by account')
    parser.add_argument('-c',
                        help='Specify container amount by account')
    parser.add_argument('-f',
                        help='Specify file amount by account')
    parser.add_argument('-s',
                        help='Specify the MAX file size. Files '
                        'will be from 1024 Bytes to MAX Bytes')
    args = parser.parse_args()

    concurrency = int(get_config('filler', 'concurrency'))
    pile = eventlet.GreenPile(concurrency)
    pool = eventlet.GreenPool(concurrency)

    client = ksclient.Client(username=get_config('filler', 'a_username'),
                             password=get_config('filler', 'a_password'),
                             auth_url=get_config('filler', 'auth_url'),
                             tenant_name=get_config('filler', 'a_tenant'))

    if not args.create and not args.delete:
        parser.print_help()
        sys.exit(1)
    if args.create and args.delete:
        parser.print_help()
        sys.exit(1)

    if args.l:
        index = load_index()
        index_containers = load_containers_index()
    else:
        index = {}
        index_containers = {}
    if args.create:
        if args.a is None or not args.a.isdigit():
            print("Provide account amount by setting '-a' option")
            sys.exit(1)
        if args.u is None or not args.u.isdigit():
            print("Provide user by account amount by setting '-u' option")
            sys.exit(1)
        if args.s is None:
            fmax = 1024
        else:
            if args.s.isdigit():
                fmax = max(1024, int(args.s))
            else:
                fmax = 1024
        created = create_swift_account(client, pile,
                                       int(args.a),
                                       int(args.u), index=index)
        if args.f is not None and args.c is not None:
            if args.f.isdigit() and args.c.isdigit():
                fill_swift(pool, created, int(args.c),
                           int(args.f), fmax,
                           index_containers=index_containers)
            else:
                print("'-c' and '-f' options must be integers")
                sys.exit(1)
        index_path = get_config('filler', 'index_path')
        index_containers_path = get_config('filler', 'index_containers_path')
        pickle.dump(index, file(index_path, 'w'))
        pickle.dump(index_containers, file(index_containers_path, 'w'))
    if args.delete:
        index = load_index()
        for k, v in index.items():
            user_info_list = [user[1] for user in v]
            # Take the first user we find
            delete_account_content(client, k, v[0])
            delete_account(client, user_info_list, k)
            del index[k]
        pickle.dump(index, file(index_path, 'w'))

if __name__ == '__main__':
    main()

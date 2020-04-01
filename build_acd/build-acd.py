#!/usr/bin/python3 -tt

import sys

if __name__ == '__main__':
    if sys.version_info < (3, 8):
        print('Needs Python 3.8 or later')
        sys.exit(1)

    from ansible_infra.cli import main

    sys.exit(main(sys.argv))

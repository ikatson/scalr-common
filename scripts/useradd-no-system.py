#!/usr/bin/env python

import os
import subprocess
import sys


def main():
    """Call real useradd but remove --system argument.

    Our LDAP integration does not like system users.
    """
    program, args = sys.argv[0], sys.argv[1:]
    program = os.path.basename(program)
    args = [a for a in args if a not in ('-r', '--system')]

    process = subprocess.Popen(['/sbin/%s_real' % program] + args, shell=False)
    process.communicate()
    sys.exit(process.returncode)


if __name__ == '__main__':
    main()

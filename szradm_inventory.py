#!/usr/bin/env python

"""Convert szradm output into ansible inventory.

Usage:
  szradm_inventory.py --list

Supported environment variables:

- MERGE_INVENTORY_JSON_FILE
- SZRADM_OUTPUT_FILE
- ANSIBLE_SSH_USER
- ANSIBLE_USE_EXTERNAL_IP
- USE_BASTION_HOST

"""

import json
import subprocess
import os

import sys


def is_this_machine_the_one_owning_ip(ip_addr):
    ip_addr = ip_addr.replace('.', '\.')
    try:
        subprocess.check_call('ip -o a | grep -q "%s"' % ip_addr, shell=True)
    except subprocess.CalledProcessError:
        return False
    return True


def get_szradm_output():
    envvar = 'SZRADM_OUTPUT_FILE'
    if envvar in os.environ:
        with open(os.environ[envvar]) as f:
            return json.load(f)

    output = subprocess.check_output(['szradm', 'queryenv', '--format=json', 'list-roles'])
    return json.loads(output)


def substitute_environment_variables(obj):
    if isinstance(obj, list):
        return map(substitute_environment_variables, obj)
    elif isinstance(obj, dict):
        return {k: substitute_environment_variables(v) for k, v in obj.iteritems()}
    elif not isinstance(obj, basestring):
        return obj
    if obj.startswith('${') and obj.endswith('}'):
        envvar_name = obj[2:-1]
        try:
            default = envvar_name.split(':-')[1]
        except IndexError:
            return os.environ[envvar_name]
        else:
            return os.environ.get(envvar_name, default)
    return obj


def get_merge_inventory():
    envvar = 'MERGE_INVENTORY_JSON_FILE'
    if envvar not in os.environ:
        return {}
    with open(os.environ[envvar]) as f:
        inventory = json.load(f)
    inventory = substitute_environment_variables(inventory)
    return inventory


# http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge
def merge_dicts(a, b, path=None):
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def convert_szradm_output_into_inventory(output):
    meta_hostvars = {}
    inventory = {
        '_meta': {
            'hostvars': meta_hostvars
        },
        'all': {
            'vars': {}
        },
    }
    for role in output['roles']:
        ansible_role_name = role['alias']
        hosts = role['hosts']
        for host in hosts:
            private_ip = host['internal-ip']
            inventory_hostname = '%s_%s' % (ansible_role_name, private_ip)
            inventory.setdefault(ansible_role_name, []).append(inventory_hostname)

            this_host_vars = meta_hostvars[inventory_hostname] = {
                'scalr_index': host['index'],
                'ansible_ssh_host': private_ip,
                'private_ip': private_ip,
                'ansible_become': 'true',
            }

            if os.environ.get('ANSIBLE_SSH_USER'):
                this_host_vars['ansible_ssh_user'] = os.environ['ANSIBLE_SSH_USER']

            if os.environ.get('ANSIBLE_USE_EXTERNAL_IP'):
                this_host_vars['ansible_ssh_host'] = host['external-ip']

            if is_this_machine_the_one_owning_ip(private_ip):
                this_host_vars['ansible_connection'] = 'local'
                this_host_vars.pop('ansible_ssh_host')

    bastion_host = os.environ.get('USE_BASTION_HOST')
    if bastion_host:
        tmpl = '-o ProxyCommand="ssh -W %h:%p -q {bastion_host} -o StrictHostKeyChecking=no"'
        # noinspection PyTypeChecker
        inventory['all']['vars'].update({
            'ansible_ssh_common_args': tmpl.format(
                bastion_host=bastion_host
            )
        })

    return inventory


def main():
    roles = get_szradm_output()

    generated_inventory = convert_szradm_output_into_inventory(roles)
    merge_inventory = get_merge_inventory()

    inventory = merge_dicts(generated_inventory, merge_inventory)

    print json.dumps(inventory, indent=4)


if __name__ == '__main__':
    if '--list' not in sys.argv:
        print __doc__
        sys.exit(1)
    main()

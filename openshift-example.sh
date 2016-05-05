#!/bin/bash

set -ex
yum install -y ansible expect git jq

export ANSIBLE_SSH_USER=ec2-user
export ANSIBLE_HOST_KEY_CHECKING=False
export MERGE_INVENTORY_JSON_FILE=inventory_mix
export SZRADM_OUTPUT_FILE=szradm_hosts

szradm queryenv --format=json list-roles > "${SZRADM_OUTPUT_FILE}"

cat "${SZRADM_OUTPUT_FILE}" | jq -r '.roles | map(select(.alias == "openshift-lb"))[0].hosts[0]."internal-ip"' > lb_hostname
export OPENSHIFT_MASTER_CLUSTER_HOSTNAME="$(cat lb_hostname)"

curl -O https://raw.githubusercontent.com/ikatson/scalr-common/master/szradm_inventory.py
chmod +x szradm_inventory.py

cat > inventory_mix << EOF
{
  "etcd": {
    "children": ["openshift-etcd"]
  },
  "masters": {
    "children": ["openshift-master"],
    "vars": {
      "openshift_schedulable": "false",
      "openshift_node_labels": "{'region':'infra','zone':'default'}"
    }
  },
  "lb": {
    "children": ["openshift-lb"]
  },
  "node-infra": {
    "children": ["openshift-node-infra"],
    "vars": {
      "openshift_node_labels": "{'region':'infra','zone':'default'}"
    }
  },
  "node-primary": {
    "children": ["openshift-node-regular"],
    "vars": {
      "openshift_node_labels": "{'region':'primary','zone':'default'}"
    }
  },
  "nodes": {
    "children": ["masters", "node-infra", "node-primary"]
  },
  "OSEv3": {
    "children": ["masters", "nodes", "etcd", "lb"],
    "vars": {
      "is_containerized": "false",
      "deployment_type": "origin",
      "openshift_master_cluster_method": "native",
      "openshift_master_cluster_hostname": "${OPENSHIFT_MASTER_CLUSTER_HOSTNAME}",
      "openshift_master_cluster_public_hostname": "${OPENSHIFT_MASTER_CLUSTER_PUBLIC_HOSTNAME}",
      "openshift_master_identity_providers": "[{'name': 'htpasswd_auth', 'login': 'true', 'challenge': 'true', 'kind': 'HTPasswdPasswordIdentityProvider', 'filename': '/etc/openshift.htpasswd'}]",
      "os_sdn_network_plugin_name": "redhat/openshift-ovs-multitenant"
    }
  }
}
EOF

git clone https://github.com/openshift/openshift-ansible.git || true

cd openshift-ansible

OUTPUT_FILE="/root/logs/install.log"
OUTPUT_FILE+="-$(date +%F_%H:%M:%S)"

mkdir -p "$(dirname $"{OUTPUT_FILE}")"

# time unbuffer ansible-playbook -i szradm_inventory.py -v playbooks/byo/config.yml | tee "${OUTPUT_FILE}"

#cloud-config
# https://cloudinit.readthedocs.io/en/latest/topics/modules.html

groups:
  - ${groups}

users:
  - default
  - name: ${username}
    primary_group: ${primary_group}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: ${groups}
    shell: ${shell}
    ssh_import_id: None
    lock_passwd: false
    ssh_authorized_keys:
    - ${ssh_key_list}

ssh_pwauth: true
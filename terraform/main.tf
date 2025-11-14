# Configure the vSphere Provider
provider "vsphere" {
  vsphere_server        = var.vsphere_server
  user                  = var.vsphere_user
  password              = var.vsphere_password
  allow_unverified_ssl  = var.allow_unverified_ssl
}

# Data sources for vSphere infrastructure
data "vsphere_datacenter" "dc" {
  name = var.datacenter_name
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.cluster_name
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "datastore" {
  name          = var.datastore_name
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_storage_policy" "storage_policy" {
  name = var.storage_policy_name
}

resource "vsphere_resource_pool" "pool" {
  name          = var.resource_pool_name
  parent_resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
}

# Data source for VPC network/subnet
data "vsphere_network" "vpc_subnet" {
  name          = var.vpc_subnet_name
  datacenter_id = data.vsphere_datacenter.dc.id
}

# Content Library
resource "vsphere_content_library" "my_content_library" {
  name            = var.vsphere_content_library_name
  description     = var.vsphere_content_library_description
  storage_backing = [data.vsphere_datastore.datastore.id]
}

resource "vsphere_content_library_item" "my_content_library_item" {
  name        = var.vsphere_content_library_item_name
  description = var.vsphere_content_library_item_description
  library_id  = vsphere_content_library.my_content_library.id
  file_url    = var.vsphere_content_library_item_file_url
}

#
# Read and parse current user public id_rsa key
#
locals {
  raw_lines = [
  for line in split("\n", file(var.rsa_public_key_file)) :
  trimspace(line)
  ]
  ssh_authorized_keys = [
  for line in local.raw_lines :
  line if length(line) > 0 && substr(line, 0, 1) != "#"
  ]
}

#
# Cloud-init
# https://registry.terraform.io/providers/hashicorp/template/latest/docs/data-sources/cloudinit_config
#
data "template_cloudinit_config" "userdata" {
  gzip = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content = templatefile("cloud-init-userdata.yml.tpl", {
      username = var.cloud_init_username
      primary_group = var.cloud_init_primary_group
      groups = var.cloud_init_groups
      shell: var.cloud_init_user_shell
      ssh_key_list = local.ssh_authorized_keys[0]
      data_disks_count = var.crdb_vm_data_disk_count
    })
  }
}

# CRDB VM
resource "vsphere_virtual_machine" "crdb_vm" {
  count = var.crdb_vm_count
  name = format("%s-%02d", var.crdb_vm_name_prefix, (count.index + 1))
  hardware_version = var.crdb_vm_hw_version
  resource_pool_id = vsphere_resource_pool.pool.id

  # Storage
  datastore_id = data.vsphere_datastore.datastore.id
  storage_policy_id = data.vsphere_storage_policy.storage_policy.id

  # Compute Configuration
  num_cpus = var.crdb_vm_cpu_count
  memory = var.crdb_vm_memory_gb * 1024

  # SCSI Controller
  # scsi0:0-14 are unit numbers 0-14
  # scsi1:0-14 are unit numbers 15-29
  # scsi2:0-14 are unit numbers 30-44
  # scsi3:0-14 are unit numbers 45-59
  scsi_controller_count = max(1, min(4, var.crdb_vm_data_disk_count + 1))

  # OS Disk
  disk {
    label = format("%s-%02d-%s", var.crdb_vm_name_prefix, count.index + 1, "os")
    size = var.crdb_vm_os_disk_gb
    io_reservation = 1
    unit_number = 0
  }

  # Data disks
  # evenly distribute the data disk across controllers
  dynamic "disk" {
    for_each = range(1, var.crdb_vm_data_disk_count + 1)

    content {
      label             = format("%s-%02d-%s-disk%d", var.crdb_vm_name_prefix, count.index + 1, "data", disk.value)
      size              = var.crdb_vm_data_disk_size_gb
      io_reservation    = 1
      unit_number       = 14 + (((disk.value - 1) % 3) * 14) + disk.value
    }
  }

  cdrom {
    client_device = true
  }

  # Network interface configuration - connecting to VPC subnet
  network_interface {
    network_id   = data.vsphere_network.vpc_subnet.id
    adapter_type = "vmxnet3"
  }

  clone {
    template_uuid = vsphere_content_library_item.my_content_library_item.id

    customize {
      linux_options {
        host_name = format("%s-%02d", var.crdb_vm_name_prefix, (count.index + 1))
        domain = var.vpc_subnet_domain
      }

      network_interface {
        ipv4_address = var.vpc_subnet_ips[count.index]
        ipv4_netmask = var.vpc_subnet_netmask
      }

      ipv4_gateway = var.vpc_subnet_gateway
      dns_server_list = var.vpc_subnet_dns_servers
      dns_suffix_list = var.vpc_subnet_dns_suffix
    }
  }

  # https://github.com/tenthirtyam/terrafom-examples-vmware/tree/main/vsphere/vsphere-virtual-machine/clone-template-linux-cloud-init
  extra_config = {
    "guestinfo.userdata" = data.template_cloudinit_config.userdata.rendered
    "guestinfo.userdata.encoding" = "gzip+base64"
  }

  lifecycle {
      ignore_changes = [
         num_cores_per_socket
      ]
   }
}

resource "time_sleep" "wait_30_seconds" {
  depends_on = [ vsphere_virtual_machine.crdb_vm ]

  create_duration = "30s"
}

resource "null_resource" "ptp_device" {
  depends_on = [ time_sleep.wait_30_seconds ]
  count = var.crdb_vm_ptp_device ? 1 : 0

  provisioner "local-exec" {
    when = create
    command     = "../tools/add_ptp_to_vm.py --server '${var.vsphere_server}' --user '${var.vsphere_user}' --password '${var.vsphere_password}' --no-ssl-verify --vms '${join(",", vsphere_virtual_machine.crdb_vm[*].name) }' --enable --no-confirm"
 }
}

resource "null_resource" "vmotion_notification" {
  depends_on = [null_resource.ptp_device]
  count = var.crdb_vmotion_notification_enabled ? 1 : 0

  provisioner "local-exec" {
    when = create
    command     = "../tools/add_vmotion_notification_to_vm.py --server '${var.vsphere_server}' --user '${var.vsphere_user}' --password '${var.vsphere_password}' --no-ssl-verify --vms '${join(",", vsphere_virtual_machine.crdb_vm[*].name) }' --enable --timeout ${var.crdb_vmotion_notification_timeout} --no-confirm"
 }
}

# CRDB Anti-affinity rules
resource "vsphere_compute_cluster_vm_anti_affinity_rule" "crdb_anti_affinity_rule" {
  count = var.crdb_vm_anti_affinity && var.crdb_vm_count > 1  ? 1 : 0
  name                = format("%s-anti-affinity-rule", var.crdb_vm_name_prefix)
  compute_cluster_id  = data.vsphere_compute_cluster.cluster.id
  virtual_machine_ids = vsphere_virtual_machine.crdb_vm.*.id
}

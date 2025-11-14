# Variables for vSphere VM deployment in VF9 VPC environment

# vSphere Variables
variable "vsphere_user" {
  description = "vSphere username"
  type        = string
  sensitive   = true
}

variable "vsphere_password" {
  description = "vSphere password"
  type        = string
  sensitive   = true
}

variable "vsphere_server" {
  description = "vSphere server FQDN or IP"
  type        = string
}

variable "allow_unverified_ssl" {
  description = "Allow unverified SSL certificates"
  type        = bool
  default     = false
}

# vSphere Infrastructure Variables
variable "datacenter_name" {
  description = "Name of the vSphere datacenter"
  type        = string
}

variable "datastore_name" {
  description = "Name of the datastore for VM storage"
  type        = string
}

variable "storage_policy_name" {
  description = "vsan storage policy"
  type = string
  default = "vSAN Default Storage Policy"
}

variable "cluster_name" {
  description = "Name of the vSphere cluster"
  type        = string
}

variable "resource_pool_name" {
  description = "Name of the resource pool"
  type        = string
  default     = "Resources"
}

# VPC Network Variables
variable "vpc_subnet_name" {
  description = "Name of the VPC subnet/network to connect the VM to"
  type        = string
}

variable "vpc_subnet_domain" {
  description = "vpc subnet domain name"
  type = string
  default = "domain.local"
}

variable "vpc_subnet_ips" {
  description = "VPC subnet IPs"
  type = list(string)
}

variable "vpc_subnet_netmask" {
  description = "VPC subnet mask"
  type = number
}

variable "vpc_subnet_gateway" {
  description = "VPC subnet gateway"
  type = string
}

variable "vpc_subnet_dns_servers" {
  description = "DNS server ip list"
  type = list(string)
  default = ["8.8.8.8", "8.8.4.4"]
}

variable "vpc_subnet_dns_suffix" {
  description = "DNS server suffix list"
  type = list(string)
  default = []
}

# Content Library Variables
variable "vsphere_content_library_name" {
  description = "content library name"
  type = string
}

variable "vsphere_content_library_description" {
  description = "content library description"
  type = string
  default = "A new source of content"
}

variable "vsphere_content_library_item_name" {
  description = "name of the content library template"
  type = string
  default = "template"
}

variable "vsphere_content_library_item_description" {
  description = "description of the content library template"
  type = string
  default = "Template for terraform automation"
}

variable "vsphere_content_library_item_file_url" {
  description = "template url"
  type = string
}

# RSA
variable "rsa_private_key_file" {
  description = "RSA private key file"
  type = string
  default = "~/.ssh/id_rsa"
}

variable "rsa_public_key_file" {
  description = "RSA public key file"
  type = string
  default = "~/.ssh/id_rsa.pub"
}

# Cloud-Init
#
# Cloud Init
#
variable "cloud_init_username" {
  description = "username for the user on the linux system"
  type = string
  default = "vmware"
}

variable "cloud_init_primary_group" {
  description = "primary group for the user on the linux system"
  type = string
  default = "vmware"
}

variable "cloud_init_groups" {
  description = "comma separated list of groups for the user on the linux system"
  type = string
  default = "wheel"
}

variable "cloud_init_user_shell" {
  description = "user shell"
  type = string
  default = "/bin/bash"
}

# CRDB VM
variable "crdb_vm_count" {
  description = "number of crdb VM"
  type = number
  default = 3
}

variable "crdb_vm_name_prefix" {
  description = "crdb VM name prefix"
  type = string
  default = "crdb"
}

variable "crdb_vm_hw_version" {
  # https://knowledge.broadcom.com/external/article/315655/virtual-machine-hardware-versions.html
  # Minimum version 17 required for PTP clock
  # Minimum version 20 for vmotion notification
  description = "hardware version"
  type = number
  default = 22
}

variable "crdb_vm_cpu_count" {
  description = "number of CRDB VM vCPU"
  type = number
  default = 4
}

variable "crdb_vm_memory_gb" {
  description = "amount of CRDB VM RAM"
  type = number
  default = 8
}

variable "crdb_vm_os_disk_gb" {
  description = "CRDB VM OS disk size in GB"
  type = number
  default = 100
}

variable "crdb_vm_data_disk_count" {
  # Because we can have up to 4 controllers, 1 is used for the OS and
  # 3 for the data disks. So the number of data disks should be
  # 1, 2, 3, or multiples of 3 to ensure a even distribution
  description = "number of CRDB VM data disks"
  type = number
  default = 1
}

variable "crdb_vm_data_disk_size_gb" {
  description = "size of CRDB VM data disks"
  type = number
  default = 100
}

variable "crdb_vm_ptp_device" {
  description = "add a PTP device to the CRDB VM"
  type = bool
  default = true
}

variable "crdb_vmotion_notification_enabled" {
  description = "enable vMotion notification on CRDB VM"
  type = bool
  default = true
}

variable "crdb_vmotion_notification_timeout" {
  description = "vMotion notification timeout value on CRDB VM"
  type = number
  default = 300
  validation {
    condition     = var.crdb_vmotion_notification_timeout >= 60
    error_message = "crdb_vmotion_notification_timeout must be greater or equal to 60"
  }
}


variable "crdb_vm_anti_affinity" {
  description = "create anti-affinity rules for CRDB VM"
  type = bool
  default = true
}

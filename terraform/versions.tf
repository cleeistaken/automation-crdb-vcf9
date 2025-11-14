terraform {
  required_version = ">= 1.13.5"
  required_providers {
    vsphere = {
      source  = "vmware/vsphere"
      version = "~> 2.15.0"
    }
  }
}
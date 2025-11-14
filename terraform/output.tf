resource "local_file" "inventory" {
  content  = templatefile("inventory-crdb.yml.tpl", {
    # VM credentials
    vm_user = var.cloud_init_username
    vm_ssh_private_key_file = var.rsa_private_key_file

    # CRDB VMs
    crdb_vms = vsphere_virtual_machine.crdb_vm
    ptp_enabled = var.crdb_vm_ptp_device
    vmotion_notifications_enabled = var.crdb_vmotion_notification_enabled

  })
  filename = "../ansible/inventory.yml"
  file_permission = "644"
}

output "vm_names" {
  value       = vsphere_virtual_machine.crdb_vm[*].name
  description = "The private IP address of the main server instance."
}
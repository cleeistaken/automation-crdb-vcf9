# VMware vSphere VM Configuration Scripts

Python scripts to manage VM operation notification settings and PTP (Precision Time Protocol) devices in VMware vCenter.

## Overview

This repository contains two scripts for managing VMware vSphere VM configurations:

1. **`add_vmotion_notification_to_vm.py`**: Manages VM operation notification settings
2. **`add_ptp_to_vm.py`**: Manages PTP (Precision Time Protocol) devices on VMs

Both scripts follow a consistent interface and support:
- Reading current configuration status
- Enabling/adding features
- Disabling/removing features
- Processing multiple VMs via comma-separated list
- Batch operations with confirmation prompts

## Requirements

- Python 3.6 or higher
- pyvmomi library (VMware vSphere API Python bindings)
- Access to a vCenter server
- Appropriate permissions to reconfigure VMs

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install pyvmomi
```

## Script 1: VM Operation Notification Configuration

### Overview

Manages two key VM configuration properties:

- **`vmOpNotificationToAppEnabled`**: Enable/disable operation notifications to applications
  - When set to `TRUE`, applications running inside the VM will be notified of operations for which they have registered
  - If unset, defaults to `FALSE` (no notifications sent)

- **`vmOpNotificationTimeout`**: Timeout value in seconds for VM operation notifications
  - Specifies how long to wait for application response before proceeding with the operation

### Usage

#### Basic Syntax

```bash
python add_vmotion_notification_to_vm.py -s <vcenter_host> -u <username> -v <vm_names> [action] [options]
```

#### Required Arguments

- `-s, --server`: vCenter server hostname or IP address
- `-u, --user`: vCenter username
- `-v, --vms`: Comma-separated list of VM names
- One of the following actions:
  - `--read`: Read current notification settings
  - `--enable`: Enable VM operation notifications (requires `--timeout`)
  - `--disable`: Disable VM operation notifications

#### Optional Arguments

- `-w, --password`: vCenter password (will prompt if not provided, or use VCENTER_PASSWORD env var)
- `--port`: vCenter port (default: 443)
- `--timeout`: VM operation notification timeout in seconds (required with `--enable`)
- `--no-ssl-verify`: Disable SSL certificate verification (enabled by default for compatibility)
- `--no-confirm`: Skip confirmation prompt before processing VMs
- `--dry-run`: Show which VMs would be processed without making changes

#### Examples

**Read current settings for multiple VMs:**
```bash
python add_vmotion_notification_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2,vm3 \
  --read
```

**Enable notifications with timeout for multiple VMs:**
```bash
python add_vmotion_notification_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2,vm3 \
  --enable \
  --timeout 600
```

**Disable notifications:**
```bash
python add_vmotion_notification_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2 \
  --disable
```

**Using environment variable for password:**
```bash
export VCENTER_PASSWORD="mypassword"
python add_vmotion_notification_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2 \
  --enable \
  --timeout 300
```

**Note**: The `--no-ssl-verify` flag is enabled by default for compatibility with self-signed certificates. SSL verification is automatically disabled unless you explicitly configure it otherwise.

## Script 2: PTP Device Management

### Overview

Manages PTP (Precision Time Protocol) devices on VMware VMs. PTP devices provide high-precision time synchronization for VMs that require accurate timekeeping.

**Note**: VMs must be powered off to add or remove PTP devices. The script will automatically power off VMs if needed and power them back on after the operation.

### Usage

#### Basic Syntax

```bash
python add_ptp_to_vm.py -s <vcenter_host> -u <username> -v <vm_names> [action] [options]
```

#### Required Arguments

- `-s, --server`: vCenter server hostname or IP address
- `-u, --user`: vCenter username
- `-v, --vms`: Comma-separated list of VM names
- One of the following actions:
  - `--read`: Read current PTP device status
  - `--enable`: Enable PTP device (add if not present)
  - `--disable`: Disable PTP device (remove if present)

#### Optional Arguments

- `-w, --password`: vCenter password (will prompt if not provided, or use VCENTER_PASSWORD env var)
- `--port`: vCenter port (default: 443)
- `--no-ssl-verify`: Disable SSL certificate verification (enabled by default for compatibility)
- `--no-confirm`: Skip confirmation prompt before processing VMs
- `--dry-run`: Show which VMs would be processed without making changes

#### Examples

**Read PTP device status for multiple VMs:**
```bash
python add_ptp_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2,vm3 \
  --read
```

**Enable PTP device on multiple VMs:**
```bash
python add_ptp_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2,vm3 \
  --enable
```

**Disable PTP device on VMs:**
```bash
python add_ptp_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2 \
  --disable
```

**Dry run to see what would be processed:**
```bash
python add_ptp_to_vm.py \
  -s vcenter.example.com \
  -u administrator@vsphere.local \
  -v vm1,vm2,vm3 \
  --enable \
  --dry-run
```

**Note**: The `--no-ssl-verify` flag is enabled by default for compatibility with self-signed certificates. SSL verification is automatically disabled unless you explicitly configure it otherwise.

## Common Features

Both scripts share the following features:

- **Consistent Interface**: Both scripts use the same argument naming conventions
- **Batch Processing**: Process multiple VMs via comma-separated list
- **Read Mode**: Check current configuration without making changes
- **Enable/Disable**: Add or remove features as needed
- **Secure Password Handling**: Password prompt or environment variable support
- **SSL Verification Control**: Optional SSL certificate verification (disabled by default for compatibility)
- **Confirmation Prompts**: Optional confirmation before making changes
- **Dry Run Mode**: Preview operations without executing them
- **Detailed Summary**: Shows successful, failed, and skipped VMs
- **Error Handling**: Comprehensive error handling with user-friendly messages

## Permissions Required

The user account needs the following vSphere privileges:

### For VM Notification Script:
- `VirtualMachine.Config.Settings` - To modify VM notification settings
- `System.View` - To view and search for VMs

### For PTP Device Script:
- `VirtualMachine.Config.AddRemoveDevice` - To add/remove PTP devices
- `VirtualMachine.Interact.PowerOff` - To power off VMs when needed
- `VirtualMachine.Interact.PowerOn` - To power on VMs after configuration
- `System.View` - To view and search for VMs

## Reference

For more information about the VM configuration properties, see:
- [VirtualMachineConfigSpec - vSphere Web Services API](https://developer.broadcom.com/xapis/vsphere-web-services-api/8.0u3/vim.vm.ConfigSpec.html)
- [VirtualPrecisionClock - vSphere Web Services API](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.vm.device.VirtualPrecisionClock.html)

## Troubleshooting

### VM Not Found
- Verify the VM name is correct (case-sensitive)
- Ensure you have permissions to view the VM
- Check that you're connected to the correct vCenter

### Permission Denied
- Verify your user account has the required privileges (see Permissions Required section)
- Check that the VM is not in a restricted state

### Connection Issues
- Verify network connectivity to vCenter
- Check firewall rules allow connection on the specified port (default 443)
- SSL certificate verification is disabled by default for compatibility with self-signed certificates
- To enable SSL verification, remove the `--no-ssl-verify` flag (note: it's enabled by default)

### PTP Device Issues
- VMs must be powered off to add/remove PTP devices
- The script will automatically handle power state management
- Ensure VM hardware version supports PTP devices (typically v14 or higher)

## License

These scripts are provided as-is for use with VMware vSphere environments.

## Contributing

Feel free to submit issues or pull requests for improvements.

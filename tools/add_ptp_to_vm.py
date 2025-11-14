#!/usr/bin/env python3
"""
Script to add PTP device to VMware vSphere VMs.
Handles VM power states appropriately.
"""

import ssl
import time
import argparse
import sys
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import atexit
import getpass


class VCenterManager:
    """Manages vCenter connection and VM operations."""

    def __init__(self, host, user, password, port=443, no_ssl_verify=True):
        """
        Initialize vCenter connection.

        Args:
            host: vCenter hostname or IP
            user: vCenter username
            password: vCenter password
            port: vCenter port (default 443)
            no_ssl_verify: Disable SSL certificate verification (default True)
        """
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.no_ssl_verify = no_ssl_verify
        self.si = None

    def connect(self):
        """Establish connection to vCenter."""
        try:
            # Configure SSL context based on no_ssl_verify setting
            if self.no_ssl_verify:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            else:
                context = ssl.create_default_context()

            print(f"Connecting to vCenter: {self.host}...")
            self.si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
                port=self.port,
                sslContext=context
            )

            # Register disconnect on exit
            atexit.register(Disconnect, self.si)
            print("Successfully connected to vCenter")
            return True

        except Exception as e:
            print(f"Error connecting to vCenter: {str(e)}")
            return False

    def get_vm_by_name(self, vm_name):
        """
        Find VM by name.

        Args:
            vm_name: Name of the VM

        Returns:
            VM object or None if not found
        """
        content = self.si.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )

        for vm in container.view:
            if vm.name == vm_name:
                container.Destroy()
                return vm

        container.Destroy()
        return None

    def wait_for_task(self, task, timeout=300):
        """
        Wait for vCenter task to complete.

        Args:
            task: Task object
            timeout: Maximum wait time in seconds

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            if time.time() - start_time > timeout:
                print(f"Task timed out after {timeout} seconds")
                return False
            time.sleep(1)

        if task.info.state == vim.TaskInfo.State.success:
            return True
        else:
            print(f"Task failed: {task.info.error}")
            return False

    def power_off_vm(self, vm):
        """
        Power off a VM.

        Args:
            vm: VM object

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"  Powering off VM: {vm.name}...")
            task = vm.PowerOffVM_Task()
            if self.wait_for_task(task):
                print(f"  VM {vm.name} powered off successfully")
                return True
            return False
        except Exception as e:
            print(f"  Error powering off VM: {str(e)}")
            return False

    def power_on_vm(self, vm):
        """
        Power on a VM.

        Args:
            vm: VM object

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"  Powering on VM: {vm.name}...")
            task = vm.PowerOnVM_Task()
            if self.wait_for_task(task):
                print(f"  VM {vm.name} powered on successfully")
                return True
            return False
        except Exception as e:
            print(f"  Error powering on VM: {str(e)}")
            return False

    def add_ptp_device(self, vm):
        """
        Add PTP device to VM.

        Args:
            vm: VM object

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"  Adding PTP device to VM: {vm.name}...")

            # Create PTP device specification
            ptp_device = vim.vm.device.VirtualPrecisionClock()
            ptp_device.key = -1  # Auto-assign key

            # Create device backing info
            backing = vim.vm.device.VirtualPrecisionClock.SystemClockBackingInfo()
            ptp_device.backing = backing

            # Create device change spec
            device_spec = vim.vm.device.VirtualDeviceSpec()
            device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            device_spec.device = ptp_device

            # Create VM config spec
            config_spec = vim.vm.ConfigSpec()
            config_spec.deviceChange = [device_spec]

            # Reconfigure VM
            task = vm.ReconfigVM_Task(config_spec)

            if self.wait_for_task(task):
                print(f"  PTP device added successfully to {vm.name}")
                return True
            else:
                print(f"  Failed to add PTP device to {vm.name}")
                return False

        except Exception as e:
            print(f"  Error adding PTP device: {str(e)}")
            return False

    def has_ptp_device(self, vm):
        """
        Check if VM already has a PTP device.

        Args:
            vm: VM object

        Returns:
            True if PTP device exists, False otherwise
        """
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualPrecisionClock):
                return True
        return False

    def get_ptp_device(self, vm):
        """
        Get PTP device from VM if it exists.

        Args:
            vm: VM object

        Returns:
            PTP device object or None if not found
        """
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualPrecisionClock):
                return device
        return None

    def remove_ptp_device(self, vm):
        """
        Remove PTP device from VM.

        Args:
            vm: VM object

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"  Removing PTP device from VM: {vm.name}...")

            # Get the PTP device
            ptp_device = self.get_ptp_device(vm)
            if not ptp_device:
                print(f"  No PTP device found on {vm.name}")
                return False

            # Create device change spec for removal
            device_spec = vim.vm.device.VirtualDeviceSpec()
            device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
            device_spec.device = ptp_device

            # Create VM config spec
            config_spec = vim.vm.ConfigSpec()
            config_spec.deviceChange = [device_spec]

            # Reconfigure VM
            task = vm.ReconfigVM_Task(config_spec)

            if self.wait_for_task(task):
                print(f"  PTP device removed successfully from {vm.name}")
                return True
            else:
                print(f"  Failed to remove PTP device from {vm.name}")
                return False

        except Exception as e:
            print(f"  Error removing PTP device: {str(e)}")
            return False

    def process_vm(self, vm_name, action='enable'):
        """
        Process a single VM to manage PTP device.

        Args:
            vm_name: Name of the VM
            action: Action to perform ('read', 'enable', 'disable')

        Returns:
            True if successful, False if failed, None if skipped
        """
        print(f"\nProcessing VM: {vm_name}")

        # Find the VM
        vm = self.get_vm_by_name(vm_name)
        if not vm:
            print(f"  ERROR: VM '{vm_name}' not found")
            return False

        # Handle read action
        if action == 'read':
            has_ptp = self.has_ptp_device(vm)
            print(f"  PTP Device Status: {'Present' if has_ptp else 'Not Present'}")
            if has_ptp:
                ptp_device = self.get_ptp_device(vm)
                print(f"  PTP Device Key: {ptp_device.key}")
                print(f"  PTP Device Label: {ptp_device.deviceInfo.label}")
            return True

        # Handle enable action
        if action == 'enable':
            # Check if PTP device already exists
            if self.has_ptp_device(vm):
                print(f"  VM {vm_name} already has a PTP device. Skipping.")
                return None

            # Check power state
            power_state = vm.runtime.powerState
            print(f"  Current power state: {power_state}")

            was_powered_on = False

            # If VM is powered on, power it off
            if power_state == vim.VirtualMachinePowerState.poweredOn:
                was_powered_on = True
                if not self.power_off_vm(vm):
                    return False
                # Wait a bit for VM to fully power off
                time.sleep(2)

            # Add PTP device
            success = self.add_ptp_device(vm)

            # If VM was originally powered on, power it back on
            if was_powered_on and success:
                time.sleep(2)  # Wait a bit before powering on
                if not self.power_on_vm(vm):
                    print(f"  WARNING: Failed to power on VM {vm_name}")
                    return False

            return success

        # Handle disable action
        if action == 'disable':
            # Check if PTP device exists
            if not self.has_ptp_device(vm):
                print(f"  VM {vm_name} does not have a PTP device. Skipping.")
                return None

            # Check power state
            power_state = vm.runtime.powerState
            print(f"  Current power state: {power_state}")

            was_powered_on = False

            # If VM is powered on, power it off
            if power_state == vim.VirtualMachinePowerState.poweredOn:
                was_powered_on = True
                if not self.power_off_vm(vm):
                    return False
                # Wait a bit for VM to fully power off
                time.sleep(2)

            # Remove PTP device
            success = self.remove_ptp_device(vm)

            # If VM was originally powered on, power it back on
            if was_powered_on and success:
                time.sleep(2)  # Wait a bit before powering on
                if not self.power_on_vm(vm):
                    print(f"  WARNING: Failed to power on VM {vm_name}")
                    return False

            return success

        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Manage PTP device on VMware vSphere VMs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read PTP device status for specific VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2,vm3 --read

  # Enable PTP device on specific VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2,vm3 --enable

  # Disable PTP device on specific VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2 --disable

  # Use environment variable for password
  export VCENTER_PASSWORD="mypassword"
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2 --enable
        """
    )

    # Required arguments
    parser.add_argument(
        '-s', '--server',
        required=True,
        help='vCenter server hostname or IP address'
    )

    parser.add_argument(
        '-u', '--user',
        required=True,
        help='vCenter username'
    )

    parser.add_argument(
        '-w', '--password',
        help='vCenter password (if not provided, will prompt or use VCENTER_PASSWORD env var)'
    )

    # VM selection arguments
    parser.add_argument(
        '-v', '--vms',
        required=True,
        help='Comma-separated list of VM names'
    )

    # Action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--read',
        action='store_true',
        help='Read current PTP device status'
    )
    action_group.add_argument(
        '--enable',
        action='store_true',
        help='Enable PTP device (add if not present)'
    )
    action_group.add_argument(
        '--disable',
        action='store_true',
        help='Disable PTP device (remove if present)'
    )

    # Optional arguments
    parser.add_argument(
        '--port',
        type=int,
        default=443,
        help='vCenter server port (default: 443)'
    )

    parser.add_argument(
        '--no-ssl-verify',
        action='store_true',
        default=True,
        help='Disable SSL certificate verification (default: enabled for compatibility)'
    )

    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt before processing VMs'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show which VMs would be processed without making changes'
    )

    args = parser.parse_args()

    return args


def main():
    """Main function."""
    args = parse_arguments()

    # Determine action
    if args.read:
        action = 'read'
        action_desc = "Reading PTP Device Status"
    elif args.enable:
        action = 'enable'
        action_desc = "Enabling PTP Device"
    elif args.disable:
        action = 'disable'
        action_desc = "Disabling PTP Device"
    else:
        action = 'enable'  # Default
        action_desc = "Enabling PTP Device"

    print("=" * 60)
    print(f"vCenter PTP Device Management Script")
    print(f"Action: {action_desc}")
    print("=" * 60)

    # Get password if not provided
    if args.password:
        vcenter_password = args.password
    else:
        import os
        vcenter_password = os.environ.get('VCENTER_PASSWORD')
        if not vcenter_password:
            vcenter_password = getpass.getpass(f"Enter password for {args.user}: ")

    # Connect to vCenter
    print(f"\nConnecting to vCenter: {args.server}")
    if args.no_ssl_verify:
        print("  SSL certificate verification: DISABLED")
    vcenter = VCenterManager(args.server, args.user, vcenter_password, args.port, args.no_ssl_verify)
    if not vcenter.connect():
        print("Failed to connect to vCenter. Exiting.")
        sys.exit(1)

    # Parse VM names from comma-separated list
    vm_names = [name.strip() for name in args.vms.split(',')]

    # Find all VMs
    print(f"\nLooking up VMs: {', '.join(vm_names)}")
    vms_to_process = []

    for vm_name in vm_names:
        vm = vcenter.get_vm_by_name(vm_name)
        if vm:
            vms_to_process.append(vm)
            print(f"  Found: {vm_name}")
        else:
            print(f"  WARNING: VM '{vm_name}' not found")

    # Check if we have VMs to process
    if not vms_to_process:
        print("\nNo VMs to process. Exiting.")
        sys.exit(0)

    print(f"\n{'=' * 60}")
    print(f"Total VMs to process: {len(vms_to_process)}")
    for vm in vms_to_process:
        print(f"  - {vm.name}")

    # Dry run mode
    if args.dry_run:
        print(f"\n{'=' * 60}")
        print("DRY RUN MODE - No changes will be made")
        print(f"{'=' * 60}")
        print("\nScript completed (dry run).")
        sys.exit(0)

    # Confirmation prompt (skip for read operations)
    if not args.no_confirm and not args.read:
        print(f"\n{'=' * 60}")
        confirm = input("Continue with processing? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Operation cancelled.")
            sys.exit(0)

    # Process each VM
    print("\n" + "=" * 60)
    print("Processing VMs...")
    print("=" * 60)

    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    for vm in vms_to_process:
        result = vcenter.process_vm(vm.name, action=action)
        if result is True:
            results['success'].append(vm.name)
        elif result is None:  # Skipped
            results['skipped'].append(vm.name)
        else:
            results['failed'].append(vm.name)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total VMs processed: {len(vms_to_process)}")
    print(f"Successful: {len(results['success'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['success']:
        print("\nSuccessful VMs:")
        for vm in results['success']:
            print(f"  ✓ {vm}")

    if results['skipped']:
        skip_reason = "already have PTP" if action == 'enable' else "don't have PTP"
        print(f"\nSkipped VMs ({skip_reason}):")
        for vm in results['skipped']:
            print(f"  ⊘ {vm}")

    if results['failed']:
        print("\nFailed VMs:")
        for vm in results['failed']:
            print(f"  ✗ {vm}")

    print("\nScript completed.")

    # Exit with appropriate code
    if results['failed']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()


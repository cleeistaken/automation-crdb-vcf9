#!/usr/bin/env python3
"""
Script to configure VM operation notification settings in vCenter.

This script allows you to:
- Read current vmOpNotificationTimeout and vmOpNotificationToAppEnabled settings
- Set vmOpNotificationTimeout and vmOpNotificationToAppEnabled for VMs

Reference: https://developer.broadcom.com/xapis/vsphere-web-services-api/8.0u3/vim.vm.ConfigSpec.html
"""

import argparse
import sys
import ssl
import getpass
import atexit
from pyVim import connect
from pyVmomi import vim


def get_vm_by_name(content, vm_name):
    """
    Find a VM by name.
    
    Args:
        content: ServiceInstance content
        vm_name: Name of the VM to find
        
    Returns:
        VirtualMachine object or None
    """
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    
    for vm in container.view:
        if vm.name == vm_name:
            container.Destroy()
            return vm
    
    container.Destroy()
    return None


def get_vm_notification_settings(vm):
    """
    Get current VM notification settings.
    
    Args:
        vm: VirtualMachine object
        
    Returns:
        Dictionary with current settings
    """
    config = vm.config
    
    settings = {
        'vmOpNotificationToAppEnabled': getattr(config, 'vmOpNotificationToAppEnabled', None),
        'vmOpNotificationTimeout': getattr(config, 'vmOpNotificationTimeout', None)
    }
    
    return settings


def set_vm_notification_settings(vm, timeout=None, enabled=None):
    """
    Set VM notification settings.
    
    Args:
        vm: VirtualMachine object
        timeout: vmOpNotificationTimeout value (in seconds)
        enabled: vmOpNotificationToAppEnabled value (boolean)
        
    Returns:
        True if successful, False otherwise
    """
    spec = vim.vm.ConfigSpec()
    
    if enabled is not None:
        spec.vmOpNotificationToAppEnabled = enabled
    
    if timeout is not None:
        spec.vmOpNotificationTimeout = timeout
    
    try:
        task = vm.ReconfigVM_Task(spec)
        
        # Wait for the task to complete
        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            pass
        
        if task.info.state == vim.TaskInfo.State.success:
            return True
        else:
            print(f"Error: Task failed with error: {task.info.error.msg}", file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Error: Failed to reconfigure VM: {str(e)}", file=sys.stderr)
        return False


def process_vm(vm, args, content):
    """
    Process a single VM for notification settings.
    
    Args:
        vm: VirtualMachine object
        args: Command line arguments
        content: ServiceInstance content
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\nProcessing VM: {vm.name}")
    
    # Perform the requested action
    if args.read:
        # Read current settings
        settings = get_vm_notification_settings(vm)
        print("  Current VM Notification Settings:")
        print(f"    vmOpNotificationToAppEnabled: {settings['vmOpNotificationToAppEnabled']}")
        print(f"    vmOpNotificationTimeout: {settings['vmOpNotificationTimeout']}")
        return True
        
    else:
        # Set new settings
        enabled = True if args.enable else False if args.disable else None
        timeout = args.timeout
        
        print("  Configuring VM notification settings...")
        print(f"    vmOpNotificationToAppEnabled: {enabled}")
        if timeout is not None:
            print(f"    vmOpNotificationTimeout: {timeout}")
        
        success = set_vm_notification_settings(vm, timeout=timeout, enabled=enabled)
        
        if success:
            print("  ✓ VM notification settings updated successfully")
            
            # Read and display new settings
            settings = get_vm_notification_settings(vm)
            print("  New VM Notification Settings:")
            print(f"    vmOpNotificationToAppEnabled: {settings['vmOpNotificationToAppEnabled']}")
            print(f"    vmOpNotificationTimeout: {settings['vmOpNotificationTimeout']}")
            return True
        else:
            print("  ✗ Failed to update VM notification settings", file=sys.stderr)
            return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Configure VM operation notification settings in vCenter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read current settings for specific VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2,vm3 --read
  
  # Enable notifications with timeout for multiple VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2 --enable --timeout 600
  
  # Disable notifications for VMs
  %(prog)s -s vcenter.example.com -u admin@vsphere.local -v vm1,vm2,vm3 --disable
        """
    )
    
    # vCenter connection arguments
    parser.add_argument('-s', '--server', required=True,
                        help='vCenter server hostname or IP address')
    parser.add_argument('-u', '--user', required=True,
                        help='vCenter username')
    parser.add_argument('-w', '--password',
                        help='vCenter password (will prompt if not provided)')
    parser.add_argument('--port', type=int, default=443,
                        help='vCenter port (default: 443)')
    
    # VM identification arguments
    parser.add_argument('-v', '--vms', required=True,
                        help='Comma-separated list of VM names')
    
    # Action arguments
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--read', action='store_true',
                              help='Read current notification settings')
    action_group.add_argument('--enable', action='store_true',
                              help='Enable VM operation notifications to app')
    action_group.add_argument('--disable', action='store_true',
                              help='Disable VM operation notifications to app')
    
    # Configuration arguments
    parser.add_argument('--timeout', type=int,
                        help='VM operation notification timeout in seconds')
    
    # Optional arguments
    parser.add_argument('--no-ssl-verify', action='store_true', default=True,
                        help='Disable SSL certificate verification (default: enabled for compatibility)')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Skip confirmation prompt before processing VMs')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show which VMs would be processed without making changes')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.enable and args.timeout is None:
        parser.error('--timeout is required when using --enable')
    
    # Get password if not provided
    password = args.password
    if not password:
        import os
        password = os.environ.get('VCENTER_PASSWORD')
        if not password:
            password = getpass.getpass(f'Enter password for {args.user}: ')
    
    # Create SSL context based on no_ssl_verify setting
    if args.no_ssl_verify:
        ssl_context = ssl._create_unverified_context()
    else:
        ssl_context = ssl.create_default_context()
    
    print("=" * 60)
    print("vCenter VM Notification Configuration Script")
    print("=" * 60)
    
    try:
        # Connect to vCenter
        print(f"\nConnecting to vCenter: {args.server}...")
        if args.no_ssl_verify:
            print("  SSL certificate verification: DISABLED")
        si = connect.SmartConnect(
            host=args.server,
            user=args.user,
            pwd=password,
            port=args.port,
            sslContext=ssl_context
        )
        
        # Register disconnect on exit
        atexit.register(connect.Disconnect, si)
        print("Successfully connected to vCenter")
        
        content = si.RetrieveContent()
        
        # Parse VM names from comma-separated list
        vm_names = [name.strip() for name in args.vms.split(',')]
        
        # Find all VMs
        print(f"\nLooking up VMs: {', '.join(vm_names)}")
        vms_to_process = []
        
        for vm_name in vm_names:
            vm = get_vm_by_name(content, vm_name)
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
        
        # Confirmation prompt
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
            'failed': []
        }
        
        for vm in vms_to_process:
            success = process_vm(vm, args, content)
            if success:
                results['success'].append(vm.name)
            else:
                results['failed'].append(vm.name)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total VMs processed: {len(vms_to_process)}")
        print(f"Successful: {len(results['success'])}")
        print(f"Failed: {len(results['failed'])}")
        
        if results['success']:
            print("\nSuccessful VMs:")
            for vm in results['success']:
                print(f"  ✓ {vm}")
        
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
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()


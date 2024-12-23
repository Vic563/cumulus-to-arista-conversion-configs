import paramiko
from getpass import getpass

# SSH server details
hostname = "icna.ssnc-corp.cloud"
port = 8022
username = input("Enter your username: ")
password = getpass("Enter your password: ")

# Device to connect to
device_hostname = "icdlf115-cloud"

try:
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the server's host key (for testing purposes only, consider using a known_hosts file in production)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect to the SSH server
    client.connect(hostname=hostname, port=port, username=username, password=password)

    # Open an interactive shell
    shell = client.invoke_shell()

    # Wait for the initial prompt
    output = ''
    while not output.endswith('NA>'):
        output += shell.recv(1024).decode()
    print(output)

    # Connect to the network device
    shell.send(f"connect {device_hostname}\n")

    # Wait for the device prompt
    output = ''
    while not output.endswith(':~$ '):
        output += shell.recv(1024).decode()
    print(output)

    # Execute the 'net show interface' command
    shell.send("net show interface\n")

    # Receive and print the output
    output = ''
    while not output.endswith(':~$ '):
        output += shell.recv(1024).decode()
    print(output)

    # Get all UP SWP interfaces in range 1-38
    up_swp_interfaces = []
    lines = output.strip().split('\n')
    
    for line in lines[1:]:  # Skip header line
        if line.startswith('UP'):  # Only look at UP interfaces, ignore DN
            fields = line.split()
            interface_name = fields[1]
            if interface_name.startswith('swp'):
                try:
                    swp_num = int(interface_name[3:])  # Extract number after 'swp'
                    if 1 <= swp_num <= 38:  # Only include interfaces in range 1-38
                        up_swp_interfaces.append(interface_name)
                except ValueError:
                    continue  # Skip if number extraction fails

    print(f"\nUP SWP Interfaces (1-38):")
    for interface in up_swp_interfaces:
        print(f"- {interface}")

    # Execute the 'net show interface bonds' command
    shell.send("net show interface bonds\n")

    # Receive and print the output
    output_bonds = ''
    while not output_bonds.endswith(':~$ '):
        output_bonds += shell.recv(1024).decode()
    print(output_bonds)

    # Get all UP bond interfaces
    up_bond_interfaces = []
    bond_lines = output_bonds.strip().split('\n')

    for line in bond_lines[1:]:  # Skip header line
        if line.startswith('UP'):  # Only look at UP interfaces, ignore DN
            fields = line.split()
            up_bond_interfaces.append(fields[1])

    print(f"\nUP Bond Interfaces:")
    for interface in up_bond_interfaces:
        print(f"- {interface}")

    # Check each UP bond interface for trunk or access configuration
    trunk_interfaces = []
    access_interfaces = []

    for bond in up_bond_interfaces:
        shell.send(f"net show interface {bond}\n")
        output_bond_details = ''
        while not output_bond_details.endswith(':~$ '):
            output_bond_details += shell.recv(1024).decode()

        # Find and analyze ONLY the "All VLANs on L2 Port" section
        vlan_section_start = output_bond_details.find("All VLANs on L2 Port")
        if vlan_section_start != -1:
            # Find the end of this section (marked by next section "Untagged" or any other section)
            vlan_section_end = output_bond_details.find("\nUntagged", vlan_section_start)
            if vlan_section_end == -1:  # If "Untagged" not found, look for any section marker
                vlan_section_end = output_bond_details.find("\n-", vlan_section_start + 1)
            if vlan_section_end == -1:  # If no section markers found, use end of output
                vlan_section_end = len(output_bond_details)
            
            # Extract ONLY the "All VLANs on L2 Port" section
            vlan_section = output_bond_details[vlan_section_start:vlan_section_end].split('\n')
            
            # Skip the header and dashed line, get only VLAN numbers
            vlan_numbers = []
            for line in vlan_section[2:]:  # Skip "All VLANs on L2 Port" and "--------------------"
                line = line.strip()
                if line and line.isdigit():
                    vlan_numbers.append(line)
                    
            print(f"\nDebug - Bond {bond}:")
            print(f"All VLANs on L2 Port section:")
            print('\n'.join(vlan_section))
            print(f"VLAN numbers found: {vlan_numbers}")
            
            # Determine interface type based on number of VLANs
            if len(vlan_numbers) == 1:
                access_interfaces.append(bond)
            elif len(vlan_numbers) > 1:
                trunk_interfaces.append(bond)

    print(f"\nAnalysis Results:")
    print(f"Trunk Interfaces: {trunk_interfaces}")
    print(f"Access Interfaces: {access_interfaces}")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if client:
        client.close()

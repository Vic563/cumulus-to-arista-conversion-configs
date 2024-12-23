import paramiko

# SSH server details
hostname = "icna.ssnc-corp.cloud"
port = 8022
username = input("Enter your username: ")
password = input("Enter your password: ")

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

    # Count interfaces and analyze their properties
    lines = output.strip().split('\n')
    headers = lines[0].split()
    state_index = 0
    speed_index = 2
    mode_index = 4

    up_count = 0
    up_interfaces = []

    for line in lines[1:]:
        if line.startswith('UP') or line.startswith('DN'):
            fields = line.split()
            if fields[1].startswith('swp') and 1 <= int(fields[1][3:]) <= 38:
                if len(fields) > state_index and fields[state_index] == 'UP':
                    up_count += 1
                    speed = fields[speed_index] if len(fields) > speed_index else 'N/A'
                    mode = fields[mode_index] if len(fields) > mode_index else 'N/A'
                    up_interfaces.append((fields[1], speed, mode))

    # Execute the 'net show interface bonds' command
    shell.send("net show interface bonds\n")

    # Receive and print the output
    output_bonds = ''
    while not output_bonds.endswith(':~$ '):
        output_bonds += shell.recv(1024).decode()
    print(output_bonds)

    # Analyze the 'net show interface bonds' output
    bond_lines = output_bonds.strip().split('\n')
    up_bond_interfaces = []

    for line in bond_lines[1:]:
        if line.startswith('UP'):
            fields = line.split()
            up_bond_interfaces.append(fields[1])

    # Check each UP bond interface for trunk or access configuration
    trunk_interfaces = []
    access_interfaces = []

    for bond in up_bond_interfaces:
        shell.send(f"net show interface {bond}\n")
        output_bond_details = ''
        while not output_bond_details.endswith(':~$ '):
            output_bond_details += shell.recv(1024).decode()

        # Analyze the VLAN section
        vlan_section_start = output_bond_details.find("All VLANs on L2 Port")
        if vlan_section_start != -1:
            vlan_section = output_bond_details[vlan_section_start:].split('\n')[2:]
            vlan_numbers = [line.strip() for line in vlan_section if line.strip().isdigit()]

            if len(vlan_numbers) > 1:
                trunk_interfaces.append(bond)
            elif len(vlan_numbers) == 1:
                access_interfaces.append(bond)

    print(f"\nAnalysis Results:")
    print(f"Trunk Interfaces: {trunk_interfaces}")
    print(f"Access Interfaces: {access_interfaces}")
    print(f"Number of UP bond interfaces: {len(up_bond_interfaces)}")
    print("UP Bond Interfaces and their UP Member Interfaces:")
    for bond in up_bond_interfaces:
        if bond != 'peerlink':
            print(f"- {bond}")
            for interface, speed, mode in up_member_interfaces:
                if bond in mode:
                    print(f"  - {interface}: Speed={speed}")
    
    print(f"\nNumber of UP interfaces (swp1-swp38): {up_count}")
    print("UP Interfaces (swp1-swp38):")
    for interface, speed, mode in up_interfaces:
        print(f"- {interface}: Speed={speed}, Mode={mode}")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if client:
        client.close()

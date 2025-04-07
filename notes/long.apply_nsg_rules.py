import csv
import subprocess
import sys
import os
import json

# Get values from environment variables
RESOURCE_GROUP = os.getenv("RESOURCE_GROUP")
NSG_NAME = os.getenv("NSG_NAME")

if not RESOURCE_GROUP or not NSG_NAME:
    print("❌ Environment variables RESOURCE_GROUP and NSG_NAME must be set.")
    sys.exit(1)

def run_az_command(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        if capture:
            return None, result.stderr.strip()
        return False, result.stderr.strip()
    if capture:
        return result.stdout.strip(), None
    return True, None

def build_list(value):
    value = value.strip()
    if value == "*":
        return ["*"]
    return value.replace(",", " ").split()

def get_existing_rule(name):
    cmd = [
        "az", "network", "nsg", "rule", "show",
        "--resource-group", RESOURCE_GROUP,
        "--nsg-name", NSG_NAME,
        "--name", name,
        "--output", "json"
    ]
    output, err = run_az_command(cmd)
    if output:
        return json.loads(output)
    return None

def normalize(value):
    if isinstance(value, list):
        return sorted([str(v).lower() for v in value])
    return str(value).lower()

def rules_are_equal(existing, desired):
    fields = [
        "priority", "direction", "access", "protocol",
        "sourceAddressPrefixes", "sourcePortRanges",
        "sourceAddressPrefix", "sourcePortRange",
        "destinationAddressPrefix", "destinationPortRange",
        "destinationAddressPrefixes", "destinationPortRanges"
    ]
    # import pdb; pdb.set_trace();
    for field in fields:
        existing_val = normalize(existing.get(field, []))
        desired_val = normalize(desired.get(field, []))
        if existing_val != desired_val:
            return False
    return True

def apply_nsg_rule(row):
    name = row["name"].strip()

    # Parse lists
    source_prefixes = build_list(row["source_prefixes"])
    destination_prefixes = build_list(row["destination_prefixes"])
    source_ports = build_list(row["source_ports"])
    destination_ports = build_list(row["destination_ports"])

    desired = {
        "priority": int(row["priority"].strip()),
        "direction": row["direction"].strip(),
        "access": row["access"].strip(),
        "protocol": row["protocol"].strip(),
        "sourcePortRanges": source_ports,
        "destinationPortRanges": destination_ports,
    }

    if len(source_prefixes) == 1:
        desired["sourceAddressPrefix"] = source_prefixes[0]
    else:
        desired["sourceAddressPrefixes"] = source_prefixes
    if len(destination_prefixes) == 1:
        desired["destinationAddressPrefix"] = destination_prefixes[0]
    else:
        desired["destinationAddressPrefixes"] = destination_prefixes

    if len(source_ports) == 1:
        desired["sourcePortRange"] = source_ports[0]
        desired["sourcePortRanges"] = []
    else:
        desired["sourcePortRanges"] = source_ports
    if len(destination_ports) == 1:
        desired["destinationPortRange"] = destination_ports[0]
        desired["destinationPortRanges"] = []
    else:
        desired["destinationPortRanges"] = destination_ports

    existing = get_existing_rule(name)
    if existing and rules_are_equal(existing, desired):
        print(f"✔️  Skipping '{name}': no changes.")
        return

    # Build the base command
    base_cmd = [
        "az", "network", "nsg", "rule", "create",
        "--resource-group", RESOURCE_GROUP,
        "--nsg-name", NSG_NAME,
        "--name", name,
        "--priority", str(desired["priority"]),
        "--direction", desired["direction"],
        "--access", desired["access"],
        "--protocol", desired["protocol"],
        "--source-port-ranges", *source_ports,
        "--destination-port-ranges", *destination_ports,
        "--output", "none"
    ]

    if "sourceAddressPrefix" in desired:
        base_cmd += ["--source-address-prefix", desired["sourceAddressPrefix"]]
    else:
        base_cmd += ["--source-address-prefixes", *desired["sourceAddressPrefixes"]]
    if "destinationAddressPrefix" in desired:
        base_cmd += ["--destination-address-prefix", desired["destinationAddressPrefix"]]
    else:
        base_cmd += ["--destination-address-prefixes", *desired["destinationAddressPrefixes"]]

    if "sourcePortRange" in desired:
        base_cmd += ["--source-port-ranges", desired["sourcePortRange"]]
    else:
        base_cmd += ["--source-port-ranges", *desired["sourcePortRanges"]]
    if "destinationPortRange" in desired:
        base_cmd += ["--destination-port-ranges", desired["destinationPortRange"]]
    else:
        base_cmd += ["--destination-port-ranges", *desired["destinationPortRanges"]]

    success, err = run_az_command(base_cmd, capture=False)
    if success:
        print(f"🔄 Applied rule: {name}")
    else:
        print(f"❌ Failed to apply rule {name}: {err}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python apply_nsg_rules.py rules.csv")
        sys.exit(1)

    try:
        with open(sys.argv[1], newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["priority"].strip():
                    print(f"⚠️ Skipping rule '{row.get('name', '')}': missing priority")
                    continue
                apply_nsg_rule(row)
    except FileNotFoundError:
        print(f"❌ File not found: {sys.argv[1]}")
        sys.exit(1)

if __name__ == "__main__":
    main()

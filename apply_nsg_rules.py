import csv, os, sys, json, subprocess

RESOURCE_GROUP = os.getenv("RESOURCE_GROUP")
NSG_NAME = os.getenv("NSG_NAME")
if not RESOURCE_GROUP or not NSG_NAME:
    print("❌ Set RESOURCE_GROUP and NSG_NAME.")
    sys.exit(1)

def run_az_command(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        return (None, result.stderr.strip()) if capture else (False, result.stderr.strip())
    return (result.stdout.strip(), None) if capture else (True, None)

def build_list(value):
    return ["*"] if value.strip() == "*" else value.replace(",", " ").split()

def get_existing_rule(name):
    cmd = ["az", "network", "nsg", "rule", "show", "--resource-group", RESOURCE_GROUP,
           "--nsg-name", NSG_NAME, "--name", name, "--output", "json"]
    output, _ = run_az_command(cmd)
    return json.loads(output) if output else None

def normalize(v):
    return sorted([str(i).lower() for i in v]) if isinstance(v, list) else str(v).lower()

def rules_are_equal(existing, desired):
    fields = [
        "priority", "direction", "access", "protocol",
        "sourceAddressPrefixes", "sourceAddressPrefix",
        "destinationAddressPrefixes", "destinationAddressPrefix",
        "sourcePortRanges", "destinationPortRanges",
        "sourcePortRange", "destinationPortRange"
    ]
    return all(normalize(existing.get(f, [])) == normalize(desired.get(f, [])) for f in fields)

def assign_prefix_fields(desired, key, values):
    if len(values) == 1:
        desired[f"{key}Prefix"] = values[0]
    else:
        desired[f"{key}Prefixes"] = values

def assign_port_fields(desired, key, values):
    if len(values) == 1:
        desired[f"{key}PortRange"] = values[0]
    else:
        desired[f"{key}PortRanges"] = values

def apply_nsg_rule(row):
    name = row["name"].strip()
    source_prefixes = build_list(row["source_prefixes"])
    dest_prefixes = build_list(row["destination_prefixes"])
    source_ports = build_list(row["source_ports"])
    dest_ports = build_list(row["destination_ports"])

    desired = {
        "priority": int(row["priority"].strip()),
        "direction": row["direction"].strip(),
        "access": row["access"].strip(),
        "protocol": row["protocol"].strip(),
    }

    assign_prefix_fields(desired, "sourceAddress", source_prefixes)
    assign_prefix_fields(desired, "destinationAddress", dest_prefixes)
    assign_port_fields(desired, "source", source_ports)
    assign_port_fields(desired, "destination", dest_ports)

    existing = get_existing_rule(name)
    if existing and rules_are_equal(existing, desired):
        print(f"✔️  Skipping '{name}': no changes.")
        return

    base_cmd = [
        "az", "network", "nsg", "rule", "create",
        "--resource-group", RESOURCE_GROUP,
        "--nsg-name", NSG_NAME,
        "--name", name,
        "--priority", str(desired["priority"]),
        "--direction", desired["direction"],
        "--access", desired["access"],
        "--protocol", desired["protocol"],
        "--output", "none"
    ]

    for field, arg in [
        ("sourceAddressPrefix", "--source-address-prefix"),
        ("sourceAddressPrefixes", "--source-address-prefixes"),
        ("destinationAddressPrefix", "--destination-address-prefix"),
        ("destinationAddressPrefixes", "--destination-address-prefixes"),
        ("sourcePortRange", "--source-port-ranges"),
        ("sourcePortRanges", "--source-port-ranges"),
        ("destinationPortRange", "--destination-port-ranges"),
        ("destinationPortRanges", "--destination-port-ranges"),
    ]:
        if field in desired:
            val = desired[field]
            base_cmd += [arg] + ([val] if isinstance(val, str) else val)

    success, err = run_az_command(base_cmd, capture=False)
    print(f"🔄 Applied rule: {name}" if success else f"❌ Failed to apply rule {name}: {err}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python apply_nsg_rules.py rules.csv")
        sys.exit(1)

    try:
        with open(sys.argv[1], newline='') as f:
            for row in csv.DictReader(f):
                if not row["priority"].strip():
                    print(f"⚠️ Skipping rule '{row.get('name', '')}': missing priority")
                    continue
                apply_nsg_rule(row)
    except FileNotFoundError:
        print(f"❌ File not found: {sys.argv[1]}")
        sys.exit(1)

if __name__ == "__main__":
    main()

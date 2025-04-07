# apply_nsg_rules

Applies nsg rules from csv file in order to simply networking rules. Terraform is attrocious at this though you can write your own transform and use terraform to store the state. This seems a lot better.

## Rules fields

name,priority,direction,access,protocol,source_prefixes,source_ports,destination_prefixes,destination_ports

## command options

```
❌ CSV file is required unless using --get
usage: apply_nsg_rules.py [-h] [-d] [-D] [-G OUTPUT_FILE] [csv_file]

Apply or export Azure NSG rules.

positional arguments:
  csv_file              CSV file containing NSG rules to apply

options:
  -h, --help            show this help message and exit
  -d, --delete_rule     Delete existing rules before applying
  -D, --delete_all_rules
                        Delete existing rules before applying
  -G OUTPUT_FILE, --get OUTPUT_FILE
                        Export existing NSG rules to a CSV file
```

## TODO

* csv read validation for formatting checks
* Currently uses the name as UID, you could use name/priority

import json
import os

CONFIG_DIR = "configs"

with open("mapping.json", "r", encoding="utf-8") as f:
    data = json.load(f)

groups = data["groups"]
devices = data["devices"]

os.makedirs(CONFIG_DIR, exist_ok=True)

valid_files = set()

for device, group_name in devices.items():

    group = groups[group_name]

    filename = f"{device}.yaml"
    filepath = os.path.join(CONFIG_DIR, filename)

    valid_files.add(filename)

    proxies_yaml = ""

    proxy_names = []

    # MAIN

    main = group["main"]

    proxy_names.append("MAIN")

    proxies_yaml += f'''
  - name: MAIN
    type: "{main['type']}"
    server: "{main['proxy']}"
    port: {main['port']}
    username: "{main['user']}"
    password: "{main['pass']}"
    udp: true
'''

    # BACKUPS

    for i, backup in enumerate(group["backups"], start=1):

        name = f"BACKUP{i}"

        proxy_names.append(name)

        proxies_yaml += f'''
  - name: {name}
    type: "{backup['type']}"
    server: "{backup['proxy']}"
    port: {backup['port']}
    username: "{backup['user']}"
    password: "{backup['pass']}"
    udp: true
'''

    proxy_list = "\n      - ".join(proxy_names)

    yaml_content = f"""
mixed-port: 7890
allow-lan: false
mode: rule
log-level: info

proxies:
{proxies_yaml}

proxy-groups:
  - name: AUTO
    type: fallback
    url: "http://www.gstatic.com/generate_204"
    interval: 300
    proxies:
      - {proxy_list}

rules:
  - MATCH,AUTO
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[UPDATED] {filename}")

# DELETE OLD YAML

for filename in os.listdir(CONFIG_DIR):

    if filename.endswith(".yaml"):

        if filename not in valid_files:

            os.remove(os.path.join(CONFIG_DIR, filename))

            print(f"[DELETED] {filename}")

print("DONE")
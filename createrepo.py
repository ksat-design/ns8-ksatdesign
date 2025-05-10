
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023 Nethesis S.r.l.

import os
import sys
import copy
import json
import semver
import subprocess
import glob

path = '.'
index = []

defaults = {
    "name": "",
    "description": {"en": ""},
    "logo": None,
    "screenshots": [],
    "categories": ["unknown"],
    "authors": [{"name": "unknown", "email": "info@nethserver.org"}],
    "docs": {
        "documentation_url": "https://docs.nethserver.org",
        "bug_url": "https://github.com/NethServer/dev",
        "code_url": "https://github.com/NethServer/"
    },
    "versions": []
}

if len(sys.argv) >= 2:
    path = sys.argv[1]

# Walk all subdirectories
for entry_path in glob.glob(path + '/*'):
    if not os.path.isdir(entry_path):
        continue

    entry_name = os.path.basename(entry_path)
    metadata = copy.deepcopy(defaults)
    metadata["name"] = entry_name.capitalize()
    metadata["description"]["en"] = f"Auto-generated description for {entry_name}"
    metadata["id"] = entry_name

    version_labels = {}
    metadata_file = os.path.join(entry_path, "metadata.json")

    try:
        with open(metadata_file) as metadata_fp:
            metadata = {**metadata, **json.load(metadata_fp)}
    except FileNotFoundError as ex:
        print(f"Module {entry_name} was ignored:", ex, file=sys.stderr)
        continue

    # Use GitHub raw URLs for logo and screenshots from the main branch
    metadata["logo"] = f"https://raw.githubusercontent.com/ksat-design/ns8-ksatdesign/main/{entry_name}/logo.png"

    screenshot_dir = os.path.join(entry_path, "screenshots")
    if os.path.isdir(screenshot_dir):
        for file in os.listdir(screenshot_dir):
            if file.lower().endswith(".png"):
                metadata["screenshots"].append(
                    f"https://raw.githubusercontent.com/ksat-design/ns8-ksatdesign/main/{entry_name}/screenshots/{file}"
                )

    print("Inspect " + metadata["source"])
    try:
        with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
            info = json.load(proc.stdout)
            metadata["versions"] = []
            versions = []
            for tag in info.get("RepoTags", []):
                try:
                    versions.append(semver.VersionInfo.parse(tag))
                    p = subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}:{tag}'],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    info_tags = json.load(p.stdout)
                    version_labels[tag] = info_tags.get("Labels", {})
                except Exception:
                    pass

            for v in sorted(versions, reverse=True):
                metadata["versions"].append({
                    "tag": str(v),
                    "testing": v.prerelease is not None,
                    "labels": version_labels.get(str(v), {})
                })
    except Exception as e:
        print(f"Failed to inspect {metadata['source']}: {e}")

    index.append(metadata)

# Write repodata.json
with open(os.path.join(path, 'repodata.json'), 'w') as outfile:
    json.dump(index, outfile, separators=(',', ':'))

# Optionally update README.md with a logo table
with open('repodata.json') as json_file:
    data = json.load(json_file)
    with open('README.md', 'a') as f:
        f.write('\n\n## 🐞 KSAT Design Bug Tracker\n\n')
        f.write('[Raise a bug](https://github.com/ksat-design/dev/issues)\n\n')
        f.write('## 📚 Available Modules\n\n')
        f.write('| Module Name | Description | Code |\n')
        f.write('|-------------|-------------|----------------|\n')
        for module in data:
            name = module["name"]
            description = module["description"]["en"]
            code_url = module["docs"]["code_url"]
            logo = module.get("logo", "")
            name_column = f'<img src="{logo}" width="80"><br>{name}' if logo else name
            f.write(f'| {name_column} | {description} | [Code]({code_url}) |\n')
        f.write('\n')

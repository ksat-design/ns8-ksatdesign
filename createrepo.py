#!/usr/bin/env python3

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023 Nethesis S.r.l.

import os
import sys
import copy
import json
import semver
import subprocess
import glob
import urllib.parse
from datetime import datetime

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

    print("Inspecting image:", metadata["source"])
    try:
        with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}'],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
            info = json.load(proc.stdout)
            metadata["versions"] = []
            versions = []

            for tag in info.get("RepoTags", []):
                try:
                    parsed_version = semver.VersionInfo.parse(tag)
                    versions.append(parsed_version)

                    image_ref = f'docker://{metadata["source"]}:{tag}'
                    p = subprocess.Popen(["skopeo", "inspect", image_ref],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    info_tags = json.load(p.stdout)
                    version_labels[tag] = info_tags.get("Labels", {})
                except Exception:
                    continue

            for v in sorted(versions, reverse=True):
                metadata["versions"].append({
                    "tag": str(v),
                    "testing": v.prerelease is not None,
                    "labels": version_labels.get(str(v), {})
                })

    except Exception as e:
        print(f"Failed to inspect {metadata['source']}: {e}", file=sys.stderr)

    index.append(metadata)

# Add UTC timestamp to metadata
timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
metadata_output = {
    "timestamp": timestamp,
    "modules": index
}

# Write repodata.json with timestamp
with open(os.path.join(path, 'repodata.json'), 'w') as outfile:
    json.dump(metadata_output, outfile, separators=(',', ':'))

print("Metadata written. Last updated at:", timestamp)

# Generate index.md with branding and cards
with open('index.md', 'w') as f:
    f.write(f"<p align=\"center\"><img src=\"https://raw.githubusercontent.com/ksat-design/ns8-ksatdesign/main/logo.png\" width=\"160\" /></p>\n\n")
    f.write("# The KSAT Design Forge for NS8\n\n")
    f.write("*Official KSAT Design repository of NS8 modules, tools, and open-source identity solutions.*\n\n")
    f.write(f"_Last updated: **{timestamp}**_\n\n")

    f.write("## 📚 Available Modules\n\n")

    for module in metadata_output["modules"]:
        name = module["name"]
        module_id = module.get("id", name.lower().replace(" ", "-"))
        description = module["description"]["en"]
        code_url = module["docs"]["code_url"]
        logo = module.get("logo", "")
        screenshots = module.get("screenshots", [])

        issue_title = f"[Bug] {name}"
        issue_body = f"**Module**: `{module_id}`\n**Version**: `x.y.z`\n**Issue**: Describe the problem..."
        issue_url = "https://github.com/ksat-design/support/issues/new?" + urllib.parse.urlencode({
            "title": issue_title,
            "body": issue_body
        })

        f.write(f"### {name}\n")
        if logo:
            f.write(f'<img src="{logo}" alt="{name} logo" width="120"/>\n\n')
        f.write(f"**Description:** {description}  \n")
        f.write(f"[Source Code]({code_url}) | [Report Issue]({issue_url})\n\n")

        for shot in screenshots:
            f.write(f'<img src="{shot}" width="300"/>  \n')

        f.write("\n---\n\n")

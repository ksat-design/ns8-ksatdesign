#!/usr/bin/env python3

#
# Copyright (C) 2023 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

#
# Create NethForge repository metadata
# Walk all directories on the given path: each path represent a package
#

import os
import sys
import copy
import json
import imghdr
import semver
import subprocess
import glob
import urllib.request
import json

path = '.'
index = []
defaults = {
    "name": "",
    "description": { "en": "" },
    "logo": None,
    "screenshots": [],
    "categories" : [ "unknown" ],
    "authors" : [ {"name": "unknown", "email": "info@nethserver.org" } ],
    "docs": { 
        "documentation_url": "https://docs.nethserver.org",
        "bug_url": "https://github.com/NethServer/dev",
        "code_url": "https://github.com/NethServer/"
    },
    "versions": []
}

# Get current working directory if no path is specified
if len(sys.argv) >= 2:
    path = sys.argv[1]

# Walk all subdirectories
for entry_path in glob.glob(path + '/*'): # do not match .git and similar
    if not os.path.isdir(entry_path):
        continue # ignore files

    entry_name = entry_path[len(path + '/'):]

    # make sure to copy the defaults and do not just creating a reference
    metadata = copy.deepcopy(defaults)
    # prepare default values
    metadata["name"] = entry_name.capitalize()
    metadata["description"]["en"] = f"Auto-generated description for {entry_name}"
    # this field will be used to calculate the base name of images
    metadata["id"] = entry_name

    version_labels = {}
    metadata_file = os.path.join(entry_name, "metadata.json")

    try:
        with open(metadata_file) as metadata_fp:
            # merge defaults and JSON file, the latter one has precedence
            metadata = {**metadata, **json.load(metadata_fp)}
    except FileNotFoundError as ex:
        print(f"Module {entry_name} was ignored:", ex, file=sys.stderr)
        continue

    logo = os.path.join(entry_name, "logo.png")
    if os.path.isfile(logo) and imghdr.what(logo) == "png":
        metadata["logo"] = "logo.png"

    # add screenshots if pngs are available inside the screenshots directory
    screenshot_dirs = os.path.join(entry_name, "screenshots")
    if os.path.isdir(screenshot_dirs):
        with os.scandir(screenshot_dirs) as sdir:
            for screenshot in sdir:
                if imghdr.what(screenshot) == "png":
                    metadata["screenshots"].append(os.path.join("screenshots",screenshot.name))

    print("Inspect " + metadata["source"])
    # Parse the image info from remote registry to retrieve tags
    with subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}'], stdout=subprocess.PIPE, stderr=sys.stderr) as proc:
        info = json.load(proc.stdout)
        metadata["versions"] = []
        versions = []
        for tag in info["RepoTags"]:
            try:
                versions.append(semver.VersionInfo.parse(tag))
                # Retrieve labels for each valid version
                p = subprocess.Popen(["skopeo", "inspect", f'docker://{metadata["source"]}:{tag}'], stdout=subprocess.PIPE, stderr=sys.stderr)
                info_tags = json.load(p.stdout)
                version_labels[tag] = info_tags['Labels']
            except:
                # skip invalid semantic versions
                pass

        # Sort by most recent
        for v in sorted(versions, reverse=True):
            metadata["versions"].append({"tag": f"{v}", "testing": (not v.prerelease is None),  "labels": version_labels[f"{v}"]})

    index.append(metadata)

with open (os.path.join(path, 'repodata.json'), 'w') as outfile:
    json.dump(index, outfile, separators=(',', ':'))


# # list all the folders in the current directory and append the name of all folders to the end of readme.md
# folders = [f for f in os.listdir('.') if os.path.isdir(f) and not f.startswith('.')]  # list all non-hidden folders in the current directory
# with open('README.md', 'a') as f:
#     f.write('\n\n## List of all the modules in this repository\n\n')
#     for folder in folders:
#         f.write(f'- {folder}\n')    # append the name of all folders to the end of readme.md
#     f.write('\n\n')
#     f.close()


with open('repodata.json') as json_file:
    data = json.load(json_file)
    with open('README.md', 'a') as f:
        # Add project bug tracker link
        f.write('\n\n## KSAT Design bug tracker\n\n')
        f.write('[Raise a bug](https://github.com/ksat-design/dev/issues)\n\n')  # Replace with the actual project link

        # Add table header
        f.write('## List of all the modules in this repository with their description\n\n')
        f.write('| Module Name | Description | Code |\n')
        f.write('|-------------|-------------|----------------|\n')

        # Add table rows
        for module in data:
            name = module["name"]
            description = module["description"]["en"]
            code_url = module["docs"]["code_url"]
            f.write(f'| {name} | {description} | [Code]({code_url}) |\n')

        f.write('\n\n')
        f.close()

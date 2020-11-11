#! /usr/bin/python3
""" Build a `bind` catalog zone in PowerDNS, using its rest/api """

import argparse
import json
import sys
import hashlib
import dns.name
import requests
from requests.auth import HTTPBasicAuth

DEFAULT_TTL = 3600

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument(
    "-Y",
    '--yes',
    help="Actually make the changes, don't just report on them",
    action="store_true")
parser.add_argument("-S",
                    '--secure',
                    help='Use HTTPS, not HTTP',
                    action="store_true")
parser.add_argument("-s",
                    '--server',
                    help='action to request',
                    default="pdnsdev.jrcs.net")
parser.add_argument("-u", '--username', help='Username', default="dns")
parser.add_argument("-p", '--password', help='Password', default="dns")
parser.add_argument("-k", '--api-key', help='API-Key')
parser.add_argument("-x",
                    '--exclude',
                    help='Zones to exclude from the catalog (comma sep)')
parser.add_argument("-c",
                    '--catalog',
                    help='The name of your catalog zone',
                    default="lst.zz.")
args = parser.parse_args()

headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
if args.api_key is not None:
    headers["X-Api-Key"] = args.api_key

exclude_zones = {}
if args.exclude is not None:
    exclude_zones = {
        ex if ex[-1] == "." else ex + "."
        for ex in args.exclude.split(",")
    }


def hashname(name):
    """ return {name} FQDN as a catalog hash in text """
    return hashlib.sha1(dns.name.from_text(name).to_wire()).hexdigest()


def call_api(ending, method="GET", ok_resp=200, send_json=None):
    """ rest/api call to PowerDNS """

    ret = None
    if args.secure:
        url = "https://" + args.server
    else:
        url = "http://" + args.server

    url = url + "/api/v1/servers/localhost/" + ending

    myauth = None
    if "username" in args and "password" in args:
        myauth = HTTPBasicAuth(args.username, args.password)

    data = None
    if send_json is not None:
        data = json.dumps(send_json)

    if send_json is not None:
        ret = requests.request(method,
                               url,
                               data=data,
                               headers=headers,
                               auth=myauth)
    else:
        ret = requests.request(method, url, headers=headers, auth=myauth)

    if ret.status_code == ok_resp:
        return ret.content

    print("ERROR:", ret.status_code, "->", ret.content)
    return None


r = call_api("zones?dnssec=false")
if r is None:
    print("ERROR: Failed to request zone list from server")
    sys.exit(1)

try:
    zones = json.loads(r)
except json.JSONDecodeError as exp:
    print("ERROR: Zone list returned was not in JSON")
    sys.exit(1)

have_zones = {
    z["name"]: hashname(z["name"])
    for z in zones if z["name"] not in exclude_zones
}
hash_have_zones = {
    have_zones[z]: z
    for z in have_zones if z not in exclude_zones
}

if args.catalog not in have_zones:
    print("ERROR: catalog does not exsit")
    sys.exit(1)

del have_zones[args.catalog]

r = call_api("zones/" + args.catalog).decode("utf8")
try:
    catalog = json.loads(r)
except json.JSONDecodeError as exp:
    print("ERROR: Catalog Zone returned was not in JSON")
    sys.exit(1)

sfx = ".zones." + args.catalog
len_sfx = len(sfx)
back_sfx = len_sfx * -1

catalog_hash = {
    c["name"].split(".")[0]: c["records"][0]["content"]
    for c in catalog["rrsets"]
    if (c["name"] != args.catalog and c["type"] == "PTR" and
        len(c["name"]) > len_sfx and c["name"][back_sfx:] == sfx and "records"
        in c and len(c["records"]) > 0 and "content" in c["records"][0])
}

one_failed = False
made_a_change = False
changes_needed = False

for h in catalog_hash:
    if h not in hash_have_zones or hash_have_zones[h] != catalog_hash[h]:
        if not args.yes:
            print("= NEED: Delete: {hash} for zone '{zone}'".format(
                hash=h, zone=catalog_hash[h]))
            changes_needed = True
            continue

        ret = call_api(
            "zones/" + args.catalog, "PATCH", 204, {
                "rrsets": [{
                    "name": h + sfx,
                    "ttl": DEFAULT_TTL,
                    "type": "PTR",
                    "changetype": "REPLACE",
                    "records": []
                }]
            })
        if ret is not None:
            made_a_change = True
            print("= SUCCESS: Delete: {hash} for zone '{zone}'".format(
                hash=h, zone=catalog_hash[h]))
        else:
            one_failed = True
            print("= FAILED: Delete: {hash} for zone '{zone}'".format(
                hash=h, zone=catalog_hash[h]))

for z in have_zones:
    if have_zones[z] not in catalog_hash or catalog_hash[have_zones[z]] != z:
        if not args.yes:
            print("= NEED:    Add: {hash} for zone '{zone}'".format(
                hash=have_zones[z], zone=z))
            changes_needed = True
            continue

        ret = call_api(
            "zones/" + args.catalog, "PATCH", 204, {
                "rrsets": [{
                    "name": have_zones[z] + sfx,
                    "ttl": DEFAULT_TTL,
                    "type": "PTR",
                    "changetype": "REPLACE",
                    "records": [{
                        "content": z,
                        "disabled": False
                    }]
                }]
            })
        if ret is not None:
            made_a_change = True
            print("= SUCCESS:    Add: {hash} for zone '{zone}'".format(
                hash=have_zones[z], zone=z))
        else:
            one_failed = True
            print("= FAILED:    Add: {hash} for zone '{zone}'".format(
                hash=have_zones[z], zone=z))

if not args.yes:
    if changes_needed:
        print("= Updates deliberately not executed")
        sys.exit(2)
    else:
        sys.exit(0)

if one_failed:
    print("\nOne or more of the updates failed")
    sys.exit(1)

if made_a_change:
    ret = call_api("zones/" + args.catalog + "/notify", "PUT")
    if ret is not None:
        print("= SUCCESS: Zone NOTIFY queued")
        sys.exit(0)
else:
    print("= SUCCESS: Nothing to change")

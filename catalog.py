#! /usr/bin/python3

import argparse
import requests, json, pprint
from requests.auth import HTTPBasicAuth
import json
import sys
import dns.name
import hashlib

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument("-S", '--secure', help='Use HTTPS, not HTTP',action="store_true")
parser.add_argument("-s", '--server', help='action to request',default="pdnsdev.jrcs.net")
parser.add_argument("-u", '--username', help='Username',default="dns")
parser.add_argument("-p", '--password', help='Password',default="dns")
parser.add_argument("-c", '--catalog', help='The name of your catalog zone',default="lst.zz.")
args = parser.parse_args()

headers = {
    'Content-type': 'application/json',
    'Accept': 'application/json'
    }


def hashname(name):
    """ return {name} FQDN as a catalog hash in text """
    return hashlib.sha1(dns.name.from_text(name).to_wire()).hexdigest()


def call_api(ending,send_json = None,method="GET"):
    """ rest/api call to PowerDNS """

    if args.secure:
        url = "https://" + args.server
    else:
        url = "http://" + args.server

    url = url + "/api/v1/servers/localhost/" + ending

    myauth = None
    if "username" in args and "password" in args:
        myauth = HTTPBasicAuth(args.username,args.password)

    if send_json is not None:
        r = requests.request(method, url, data=json.dumps(data),
            headers=headers, auth=myauth )
    else:
        r = requests.request(method,url, headers=headers, auth=myauth)

    if r.status_code == 200:
        return r.content

    print("ERROR:",r.status_code,"->",r.content)
    return None


r = call_api("zones")
if r is None:
    print("ERROR: Failed to request zone list from server");
    sys.exit(1)

try:
    zones = json.loads(r)
except Exception as e:
    print("ERROR: Zone list returned was not in JSON")
    sys.exit(1)

r = call_api("zones/"+args.catalog).decode("utf8")
try:
    catalog = json.loads(r)
except Exception as e:
    print("ERROR: Catalog Zone returned was not in JSON")
    sys.exit(1)

## print(json.dumps(catalog,indent=3))

zonehash = { c["name"].split(".")[0]:True for c in catalog["rrsets"] if c["name"] != args.catalog and c["type"] == "PTR" }

all_zones_hash = {}
for z in zones:
    if z["name"] == args.catalog:
        continue

    zh = hashname(z["name"])
    all_zones_hash[zh] = True
    if zh not in zonehash:
        print("NO ",z["name"],zh)

for h in zonehash:
    if h not in all_zones_hash:
        print("GO ",h)

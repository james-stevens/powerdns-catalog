# powerdns-catalog
Python script to maintain a `bind` catalog zone in PowerDNS using the Rest/API

If you are using PowerDNS as your DNS Master, but you wish to use standard Zone Transfers to export your zones, it can be handy to use a feature in `bind` called a Catalog Zone.

If you are using an external DNS provider, or you are transferring your zones over long distances, it may not be possible or practical to use database replication, so zone transfer may be a better option.

This script allows you to maintain a pseudo-zone that contains a list of all the zones you want a slave to maintain. By slaving this zone onto bind, then telling `bind` this is a `catalog-zone` you can add & remove zones form all your `bind` slaves by simply maintaining the pseudo zone on the PowerDNS Master.

This utility will automatically manage the catalog zone by getting a list of all the zones on your PowerDNS Master, removing the ones you wish to exclude, then updating a catalog zone to reflect the current active list of zones.

If the catalog zone does not exist, it will be created with suitable settings (META data records). If you want specific settings for the catalog zone, its probably best to simply pre-create an empty catalog zone, and set it up as you prefer – although the script will not alter the zone settings once it has been created, so you can create the zone using this script, then modify it to your preferred configuration and it will be left like that.

NOTE: in PowerDNS a catalog zone is just a normal DNS zone, it only becomes special when you tell `bind` to treat it as a `catalog-zone`.


# Python

I developed this using Python v3.8, but it doesn't use any particularly new features (I don't think).



# Excluding Zones by `Kind` or `name`

Zones, that exist on your PowerDNS Master, can be excluded from the catalog individually by name, by providing a comma separated list, or by zone `kind`.

By default only zones with a `kind` of `Master` will be included, but you can optionally additionally include zones with a `kind` of `Native`, or include all zones.



NOTE: The default action of the script is to only report on the changes necessary. You must always specify the `-Y` flag to actually execute the changes.

If the script makes any changes to the zone and all the changes execute correctly, the script will finish by forcing a DNS `NOTIFY` on the catalog zone, so your slaves should grab the new catalog and any new zones pretty much immediately.



# Exit Codes

Normally the script with exit with code `0` when everything has gone well. 

An exit code of `1` means something failed and an exit code of `2` means changes were required, but you only requested reporting mode – i.e. you did not specify the `-Y` flag.

Reporting mode, with no changes required will give an exit code of `0`



# Talking to the Rest/API

The script supports talking to the Rest/API with either `HTTP` or `HTTPS` and can authenticate either using the PowerDNS `api-key` mechanism or using `HTTP` Basic Authentication, with a username & password.

For PowerDNS the default is `HTTP` on port `8081` with an API-Key. You specify a port with `:[port]` after the server's name or IP Address.

I use an NGINX HTTPS proxy in front of my PowerDNS API, so I can have HTTPS and per-user authentication.

You will need at least the following in your PowerDNS config file

	api=yes
	api-key=Some-Key
	webserver-allow-from=127.0.0.1

Please refer to the PowerDNS documentation about getting their rest/api to work as you require.


# Examples

### update the catalog `lst.zz` (the default) connecting directly to PowerDNS
	$ ./catalog.py -s 127.0.0.1:8081 -K Some-Key -Y

### log in with a user name & password via an HTTPS proxy
	$ ./catalog.py -s 127.0.0.1 -S -u user -p pass -Y



# How to configure a catalog zone in `bind`

You have to add two entries to configure a catalog zone in `bind`.

Get `bind` to slave the catalog zone
Tell `bind` it is a catalog

Oddly, you sequence these two the opposite way round. First, in the `options` section, declare a catalog zone. In this example we are using the name `lst.zz`, because dot-ZZ is never going to be used as a real Top-Level-Domain.

	catalog-zones { zone "lst.zz" default-masters { 192.168.1.1; }; };

the `default-masters` is the list of masters from where to get the listed zones (the zones listed in the catalog), not where to get the catalog itself

Now we tell bind to slave the catalog. This is not in the options section.

	zone "lst.zz" { type slave; file "/zones/lst.zz"; masters { 192.168.1.1; }; };

The `masters` listed here are the servers from where to get the catalog zone. 

If you are using this script to build a catalog on a PowerDNS Master, it is highly likely that these two lists of IP Addresses (where to get the catalog zone & where to get the listed zones) will be the same, like in my example.

If you have multiple masters, with different zones on each, you can have one catalog per master and get a single `bind` to slave all the catalog and so all the zones. Each catalog zone must have a different name.

If you do not specify a `zone-directory` for a catalog zone, the listed zone's files will be put in your default `bind` directory. The file name for the listed zones will include their zone name and the name of the catalog they were listed in.


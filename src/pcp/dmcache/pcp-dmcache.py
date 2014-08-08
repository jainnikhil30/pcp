#!/usr/bin/python
#
# Copyright (C) 2014 Red Hat.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# DmCache Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# pylint: disable=C0103,R0914,R0902,W0141
""" Display device mapper cache statistics for the system """

import sys
from pcp import pmapi, pmcc

CACHE_METRICS = ['dmcache.cache.used', 'dmcache.cache.total',
                 'dmcache.metadata.used', 'dmcache.metadata.total',
                 'dmcache.read_hits', 'dmcache.read_misses',
                 'dmcache.write_hits', 'dmcache.write_misses',
                 'disk.dm.read', 'disk.dm.write']
MOUNT_METRICS = ['hinv.map.dmname', 'filesys.mountdir']

HEADING = \
    '---device--- ---%used--- ---------reads--------- --------writes---------'
SUBHEAD = \
    '             meta  cache     hit    miss     ops     hit    miss     ops'

def cache_value(group, device, width, values):
    """ Lookup value for device instance, return it in a short string """
    if device not in values:
        return '?'.rjust(width)
    result = group.contextCache.pmNumberStr(values[device])
    return result.strip(' ').rjust(width)

def cache_percent(device, width, used, total):
    """ From used and total values (dict), calculate 'percentage used' """
    if device not in used or device not in total:
        return '?%'.rjust(width)
    value = 100.0 * (used[device] / total[device])
    if value >= 100.0:
        return '100%'.rjust(width)
    return ('%3.1f%%' % value).rjust(width)

def cache_dict(group, metric):
    """ Create an instance:value dictionary for the given metric """
    values = group[metric].netConvValues
    if not values:
        return {}
    return dict(map(lambda x: (x[1], x[2]), values))


class DmCachePrinter(pmcc.MetricGroupPrinter):
    """ Report device mapper cache statistics """

    def __init__(self, devices):
        """ Construct object - prepare for command line handling """
        pmcc.MetricGroupPrinter.__init__(self)
        self.headings = 10        # repeat heading after every N samples
        self.hostname = None
        self.devices = devices

    def report_values(self, group):
        """ Report values for one of more device mapper cache devices """

        # Build several dictionaries, keyed on cache names, with the values
        cache_used = cache_dict(group, 'dmcache.cache.used')
        cache_total = cache_dict(group, 'dmcache.cache.total')
        meta_used = cache_dict(group, 'dmcache.metadata.used')
        meta_total = cache_dict(group, 'dmcache.metadata.total')
        read_hits = cache_dict(group, 'dmcache.read_hits')
        read_misses = cache_dict(group, 'dmcache.read_misses')
        read_ops = cache_dict(group, 'disk.dm.read')
        write_hits = cache_dict(group, 'dmcache.write_hits')
        write_misses = cache_dict(group, 'dmcache.write_misses')
        write_ops = cache_dict(group, 'disk.dm.write')

        devicelist = self.devices
        if not devicelist:
            devicelist = cache_used.keys()
        for name in sorted(devicelist):
            print '%s %s %s %s %s %s %s %s %s' % (name.ljust(12),
                    cache_percent(name, 5, meta_used, meta_total),
                    cache_percent(name, 5, cache_used, cache_total),
                    cache_value(group, name, 7, read_hits),
                    cache_value(group, name, 7, read_misses),
                    cache_value(group, name, 7, read_ops),
                    cache_value(group, name, 7, write_hits),
                    cache_value(group, name, 7, write_misses),
                    cache_value(group, name, 7, write_ops))

    def report(self, groups):
        """ Report driver routine - headings, sub-headings and values """
        self.convert(groups)
        group = groups['dmcache']
        if groups.counter % self.headings == 1:
            if not self.hostname:
                self.hostname = group.contextCache.pmGetContextHostName()
            stamp = group.contextCache.pmCtime(long(group.timestamp))
            title = '@ %s (host %s)' % (stamp.rstrip(), self.hostname)
            print '%s\n%s\n%s' % (title, HEADING, SUBHEAD)
        self.report_values(group)

if __name__ == '__main__':
    try:
        options = pmapi.pmOptions('?')
        options.pmSetShortUsage('[options] [device ...]')
        options.pmSetLongOptionHeader('Options')
        options.pmSetLongOptionVersion()
        options.pmSetLongOptionHelp()
        manager = pmcc.MetricGroupManager.fromOptions(options, sys.argv)
        manager.printer = DmCachePrinter(options.pmNonOptionsFromList(sys.argv))
        manager['dmcache'] = CACHE_METRICS
        manager['devices'] = MOUNT_METRICS
        manager.run()
    except pmapi.pmErr, error:
        print '%s: %s\n' % (error.progname(), error.message())
    except pmapi.pmUsageErr, usage:
        usage.message()
    except KeyboardInterrupt:
        pass

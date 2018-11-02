import argparse

import blivet
from blivet.size import Size
from blivet.util import set_up_logging

set_up_logging()
b = blivet.Blivet()


def init_disk(device):
    global b
    if device.isleaf and device.format.type is None:
        b.initialize_disk(device)


def manage_device(*args, **kwargs):
    global b
    # create an lv named data in a vg named testvg
    device = b.factory_device(*args, **kwargs)
    print(b.devicetree)
    #b.do_it()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Manage block devices.')
    parser.add_argument('-n', '--name', help='the name of the device')
    parser.add_argument('-s', '--size', default='')
    parser.add_argument('-d', '--disks', default=list())
    parser.add_argument('-t', '--type')
    parser.add_argument('-f', '--fstype')
    parser.add_argument('-e', '--encrypted', action='store_true')
    parser.add_argument('-r', '--raid-level')
    parser.add_argument('-p', '--pool-name')
    parser.add_argument('--pool-encrypted', action='store_true')
    parser.add_argument('--pool-raid-level')

    args = parser.parse_args()
    print(args)

    # special handling for size
    size = None
    if args.size and args.size.lower() != 'max':
        size = Size(args.size)

    # special handling for type
    device_type = None
    if args.type == None:
        device_type = blivet.devicefactory.DEVICE_TYPE_LVM
    elif args.type == 'lvm':
        device_type = blivet.devicefactory.DEVICE_TYPE_LVM
    elif args.type.startswith('part'):
        device_type = blivet.devicefactory.DEVICE_TYPE_PARTITION
    elif args.type in ('raid', 'md', 'mdraid'):
        device_type = blivet.devicefactory.DEVICE_TYPE_MD

    b.reset()

    # special handling for disks
    disks = list()
    for disk_id in args.disks.split(','):
        disk = b.devicetree.resolve_device(disk_id)
        if not disk.is_disk:
            sys.stderr.write("specified disk '%s' is not a disk\n" % disk_id)
            sys.exit(1)

        disks.append(disk)
        init_disk(disk)

    manage_device(device_type=device_type,
                  size=size,
                  disks=disks,
                  name=args.name,
                  fstype=args.fstype,
                  encrypted=args.encrypted,
                  raid_level=args.raid_level,
                  container_name=args.pool_name,
                  container_encrypted=args.pool_encrypted,
                  container_raid_level=args.pool_raid_level)

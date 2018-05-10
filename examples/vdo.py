import os

import blivet
from blivet.size import Size
from blivet.util import set_up_logging, create_sparse_tempfile

set_up_logging()
b = blivet.Blivet()   # create an instance of Blivet (don't add system devices)

# create a disk image file on which to create new devices
disk1_file = create_sparse_tempfile("disk1", Size("20GiB"))
b.disk_images["disk1"] = disk1_file

b.reset()

try:
    disk1 = b.devicetree.get_device_by_name("disk1")

    b.initialize_disk(disk1)

    """
    part = b.new_partition(size=Size("50GiB"), fmt_type="vdo")
    b.create_device(part)

    # allocate the partitions (decide where and on which disks they'll reside)
    blivet.partitioning.do_partitioning(b)

    vdo = blivet.devices.VDODevice("vdo1", parents=[part])
    vdo.format = get_format("xfs", device=vdo.path)
    b.create_device(vdo)
    """
    b.factory_device(name="testlv", fstype="xfs", size=Size("50 GiB"), disks=[disk1],
                     data_reduction=True)

    print(b.devicetree)

    # write the new partitions to disk and format them as specified
    b.do_it()
    print(b.devicetree)
finally:
    b.devicetree.teardown_disk_images()
    os.unlink(disk1_file)

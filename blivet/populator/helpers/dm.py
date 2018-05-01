# populator/helpers/dm.py
# Device-mapper backend code for populating a DeviceTree.
#
# Copyright (C) 2009-2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU Lesser General Public License v.2, or (at your option) any later
# version. This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY expressed or implied, including the implied
# warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU Lesser General Public License for more details.  You should have
# received a copy of the GNU Lesser General Public License along with this
# program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301, USA.  Any Red Hat trademarks
# that are incorporated in the source code or documentation are not subject
# to the GNU Lesser General Public License and may only be used or
# replicated with the express permission of Red Hat, Inc.
#
# Red Hat Author(s): David Lehman <dlehman@redhat.com>
#

from ... import udev
from ... import dependencies
from ...devices import DMDevice
from ...devicelibs import lvm
from ...storage_log import log_method_call
from .devicepopulator import DevicePopulator

import logging
log = logging.getLogger("blivet")


class DMDevicePopulator(DevicePopulator):
    priority = 50

    @classmethod
    @dependencies.blockdev_dm_required()
    def match(cls, data):
        return (udev.device_is_dm(data) and
                not udev.device_is_dm_partition(data) and
                not udev.device_is_dm_luks(data) and
                not udev.device_is_dm_lvm(data) and
                not udev.device_is_dm_mpath(data) and
                not udev.device_is_dm_raid(data))

    def run(self):
        name = udev.device_get_name(self.data)
        log_method_call(self, name=name)
        sysfs_path = udev.device_get_sysfs_path(self.data)
        slave_devices = self._devicetree._add_slave_devices(self.data)
        device = self._devicetree.get_device_by_name(name)

        # create a device for the livecd OS image(s)
        if device is None and udev.device_is_dm_livecd(self.data):
            device = DMDevice(name, dm_uuid=self.data.get('DM_UUID'),
                              sysfs_path=sysfs_path, exists=True,
                              parents=[slave_devices[0]])
            device.protected = True
            device.controllable = False
            self._devicetree._add_device(device)

        # if we get here, we found all of the slave devices and
        # something must be wrong -- if all of the slaves are in
        # the tree, this device should be as well
        if device is None:
            lvm.lvm_cc_addFilterRejectRegexp(name)
            log.warning("ignoring dm device %s", name)

        return device

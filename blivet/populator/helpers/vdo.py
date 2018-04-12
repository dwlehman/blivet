# populator/helpers/vdo.py
# VDO backend code for populating a DeviceTree.
#
# Copyright (C) 2018  Red Hat, Inc.
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

import gi
gi.require_version("BlockDev", "2.0")

from gi.repository import BlockDev as blockdev

from ... import udev
from ...devices import VDODevice
from ...errors import DeviceError, NoSlavesError
from ...storage_log import log_method_call
from .devicepopulator import DevicePopulator
from .formatpopulator import FormatPopulator

import logging
log = logging.getLogger("blivet")


class VDODevicePopulator(DevicePopulator):
    @classmethod
    def match(cls, data):
        return (udev.device_is_dm_vdo(data))

    def run(self):
        name = udev.device_get_name(self.data)
        log_method_call(self, name=name)

        try:
            self._devicetree._add_slave_devices(self.data)
        except NoSlavesError:
            log.error("no slaves found for vdo %s, skipping", name)
            return None

        # try to get the device again now that we've got all the slaves
        device = self._devicetree.get_device_by_name(name)

        if device is None:
            try:
                uuid = udev.device_get_uuid(self.data)
            except KeyError:
                log.warning("failed to obtain uuid for vdo device")
            else:
                device = self._devicetree.get_device_by_uuid(uuid)

        if device and name:
            # update the device instance with the real name in case we had to
            # look it up by something other than name
            device.name = name

        return device


class VDOFormatPopulator(FormatPopulator):
    priority = 100
    _type_specifier = "vdo"

    def _get_kwargs(self):
        kwargs = super(VDOFormatPopulator, self)._get_kwargs()
        try:
            kwargs["uuid"] = udev.device_get_uuid(self.data)
        except KeyError:
            log.warning("vdo %s has no uuid", udev.device_get_name(self.data))

        return kwargs

    def run(self):
        super(VDOFormatPopulator, self).run()
        try:
            vdo_info = blockdev.vdo.info(self.device.path)
        except blockdev.VDOError as e:
            log.debug("blockdev.vdo.info error: %s", str(e))
            return

        # TODO: name collision resolution/handling

        try:
            vdo_device = VDODevice(
                                name=vdo_info.name,
                                uuid=vdo_info.uuid,
                                compression=vdo_info.compression,
                                deduplication=vdo_info.deduplication,
                                parents=[self.device],
                                exists=True)
        except (ValueError, DeviceError) as e:
            log.error("failed to create vdo: %s", e)
            return

        vdo.update_sysfs_path()
        self._devicetree._add_device(vdo_device)
        if vdo_device.status:
            vdo_device_info = udev.get_device(vdo_device.sysfs_path)
            if not vdo_device_info:
                log.error("failed to get udev data for %s", vdo_device.name)
                return

            self._devicetree.handle_device(vdo_device_info, update_orig_fmt=True)

    def update(self):
        # update device based on current vdo data
        pass

# devices/vdo.py
#
# Copyright (C) 2018  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): David Lehman <dlehman@redhat.com>
#
import gi
gi.require_version("BlockDev", "2.0")
from gi.repository import BlockDev as blockdev

from ..storage_log import log_method_call
from ..size import Size
from ..tasks import availability

import logging
log = logging.getLogger("blivet")

from .dm import DMDevice


class VDODevice(DMDevice):

    """ A mapped VDO device. """
    _type = "vdo"
    _packages = ["vdo"]
    _external_dependencies = [availability.BLOCKDEV_VDO_PLUGIN]

    def __init__(self, name, fmt=None, size=None, uuid=None,
                 exists=False, sysfs_path='', parents=None,
                 compression=True, deduplication=True):
        """
            :param name: the device name (generally a device node's basename)
            :type name: str
            :keyword exists: does this device exist?
            :type exists: bool
            :keyword size: the device's size
            :type size: :class:`~.size.Size`
            :keyword parents: a list of parent devices
            :type parents: list of :class:`StorageDevice`
            :keyword fmt: this device's formatting
            :type fmt: :class:`~.formats.DeviceFormat` or a subclass of it
            :keyword sysfs_path: sysfs device path
            :type sysfs_path: str
            :keyword uuid: the device UUID
            :type uuid: str
            :keyword bool compression: whether to enable compression
            :keyword bool deduplication: whether to enable deduplication
        """
        super(VDODevice, self).__init__(name, fmt=fmt, size=size, parents=parents,
                                        sysfs_path=sysfs_path, uuid=None, exists=exists)
        self.compression = compression
        self.deduplication = deduplication

    @property
    def raw_device(self):
        return self.slave

    def metadata_size_estimate(self, size=None):
        if size is None:
            size = self.slave.size

        return Size("3 GiB") + Size(size / 812)

    @property
    def size(self):
        if not self.exists:
            size = self.slave.size - self.metadata_size_estimate
        else:
            size = self.current_size
        return size

    def _create(self):
        blockdev.vdo.create(self.name, self.slave,
                            compression=self.compression,
                            deduplication=self.deduplication)

    def _post_create(self):
        self.name = self.slave.format.map_name
        super(VDODevice, self)._post_create()

    def _destroy(self):
        blockdev.vdo.remove(self.name, force=True)

    def _setup(self):
        blockdev.vdo.activate(self.name)
        blockdev.vdo.start(self.name)

    def _teardown(self):
        blockdev.vdo.stop(self.name)
        blockdev.vdo.deactivate(self.name)

    def _post_teardown(self, recursive=False):
        if not recursive:
            # this is handled by StorageDevice._post_teardown if recursive
            # is True
            self.teardown_parents(recursive=recursive)

        super(VDODevice, self)._post_teardown(recursive=recursive)

    #def dracut_setup_args(self):
    #    return set(["rd.luks.uuid=luks-%s" % self.slave.format.uuid])

    def populate_ksdata(self, data):
        self.slave.populate_ksdata(data)
        data.compression = self.compression
        data.deduplication = self.deduplication
        super(VDODevice, self).populate_ksdata(data)

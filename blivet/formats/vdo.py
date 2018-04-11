# luks.py
# Device format classes for anaconda's storage configuration module.
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

import os

from ..storage_log import log_method_call
from ..errors import VDOError
from . import DeviceFormat, register_device_format
from ..flags import flags
from ..i18n import _, N_
from ..tasks import availability
from ..size import Size

import logging
log = logging.getLogger("blivet")


class VDO(DeviceFormat):

    """ VDO """
    _type = "vdo"
    _name = N_("VDO")
    _udev_types = ["vdo"]
    _formattable = True                 # can be formatted
    _linux_native = True                # for clearpart
    _packages = ["vdo"]                 # required packages
    _min_size = Size("8 GiB")           # XXX FIXME
    _max_size = Size("16 EiB")
    _plugin = availability.BLOCKDEV_VDO_PLUGIN

    def __init__(self, **kwargs):
        """
            :keyword device: the path to the underlying device
            :keyword uuid: the VDO UUID
            :keyword exists: indicates whether this is an existing format
            :type exists: bool
            :keyword name: the name of the mapped device

            .. note::

                The 'device' kwarg is required for existing formats. For non-
                existent formats, it is only necessary that the :attr:`device`
                attribute be set before the :meth:`create` method runs. Note
                that you can specify the device at the last moment by specifying
                it via the 'device' kwarg to the :meth:`create` method.
        """
        log_method_call(self, **kwargs)
        DeviceFormat.__init__(self, **kwargs)

        self.map_name = kwargs.get("name")

        if not self.map_name and self.exists and self.uuid:
            self.map_name = "vdo-%s" % self.uuid
        elif not self.map_name and self.device:
            self.map_name = "vdo-%s" % os.path.basename(self.device)

    def __repr__(self):
        s = super(VDO, self).__repr__()
              "  map_name = %(map_name)s\n" %
              {"map_name": self.map_name})
        return s

    @property
    def dict(self):
        d = super(VDO, self).dict
        d.update("map_name": self.map_name})
        return d

    @property
    def formattable(self):
        return super(VDO, self).formattable and self._plugin.available

    @property
    def supported(self):
        return super(VDO, self).supported and self._plugin.available

    @property
    def controllable(self):
        return super(VDO, self).controllable and self._plugin.available

    @property
    def status(self):
        if not self.exists or not self.map_name:
            return False
        return os.path.exists("/dev/mapper/%s" % self.map_name)

    @property
    def destroyable(self):
        return self._plugin.available


register_device_format(VDO)

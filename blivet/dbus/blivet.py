#
# Copyright (C) 2016  Red Hat, Inc.
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
from collections import OrderedDict
import sys

import dbus

from blivet import Blivet
from blivet.callbacks import callbacks
from blivet.util import ObjectID
from .action import DBusAction
from .constants import BLIVET_INTERFACE, BLIVET_OBJECT_PATH, BUS_NAME
from .device import DBusDevice
from .format import DBusFormat
from .object import DBusObject


class DBusBlivet(DBusObject):
    """ This class provides the main entry point to the Blivet1 service.

        It provides methods for controlling the blivet service and querying its
        state.
    """
    def __init__(self, manager):
        super().__init__(manager)
        self._dbus_actions = OrderedDict()  # id -> DBusAction
        self._dbus_devices = OrderedDict()  # id -> DBusDevice
        self._dbus_formats = OrderedDict()  # id -> DBusFormat
        self._blivet = Blivet()
        self._id = ObjectID().id
        self._manager.add_object(self)
        self._set_up_callbacks()

    def _set_up_callbacks(self):
        callbacks.device_added.add(self._device_added)
        callbacks.device_removed.add(self._device_removed)
        callbacks.format_added.add(self._format_added)
        callbacks.format_removed.add(self._format_removed)
        callbacks.action_added.add(self._action_added)
        callbacks.action_removed.add(self._action_removed)
        callbacks.action_executed.add(self._action_removed)

    @property
    def id(self):
        return self._id

    @property
    def object_path(self):
        return BLIVET_OBJECT_PATH

    @property
    def interface(self):
        return BLIVET_INTERFACE

    @property
    def properties(self):
        props = {"Devices": self.ListDevices()}
        return props

    def _device_removed(self, device):
        """ Update ObjectManager interface after a device is removed. """
        removed = self._manager.get_object_by_id(device.id)
        # Make sure the format gets removed in case the device was removed w/o
        # removing the format first.
        removed_fmt = self._manager.get_object_by_id(device.format.id)
        if removed_fmt.object_path in self._dbus_formats:
            self._format_removed(device.format)
        self._manager.remove_object(removed)
        del self._dbus_devices[device.id]

    def _device_added(self, device):
        """ Update ObjectManager interface after a device is added. """
        added = DBusDevice(device, self._manager)
        self._dbus_devices[added.id] = added
        self._manager.add_object(added)

    def _format_removed(self, fmt):
        removed = self._manager.get_object_by_id(fmt.id)
        # We have to remove the object either way since its path will change.
        self._manager.remove_object(removed)
        del self._dbus_formats[fmt.id]

    def _format_added(self, fmt):
        added = DBusFormat(fmt, self._manager)
        self._dbus_formats[added.id] = added
        self._manager.add_object(added)

    def _action_removed(self, action):
        removed = self._manager.get_object_by_id(action.id)
        self._manager.remove_object(removed)
        del self._dbus_actions[removed.id]

    def _action_added(self, action):
        added = DBusAction(action, self._manager)
        self._dbus_actions[added.id] = added
        self._manager.add_object(added)

    def _list_devices(self, removed=False):
        return [d for d in self._dbus_devices.values() if removed or not d.removed]

    def get_device_by_object_path(self, object_path, removed=False):
        """ Return the StorageDevice corresponding to an object path. """
        dbus_device = next((d for d in self._dbus_devices.values() if d.object_path == object_path),
                           None)
        if dbus_device is None:
            raise dbus.exceptions.DBusException('%s.DeviceNotFound' % BUS_NAME,
                                                'No device found with object path "%s".'
                                                % object_path)

        if dbus_device.removed and not removed:
            raise dbus.exceptions.DBusException('%s.DeviceNotFound' % BUS_NAME,
                                                'Device with object path "%s" has already been '
                                                'removed.' % object_path)

        return dbus_device._device

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE)
    def Reset(self):
        """ Reset the Blivet instance and populate the device tree. """
        old_devices = self._blivet.devices[:]
        for removed in old_devices:
            self._device_removed(device=removed)

        self._blivet.reset()

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE)
    def Exit(self):
        """ Stop the blivet service. """
        sys.exit(0)

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, out_signature='ao')
    def ListDevices(self):
        """ Return a list of strings describing the devices in this system. """
        return dbus.Array((d.object_path for d in self._list_devices()), signature='o')

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, in_signature='s', out_signature='o')
    def ResolveDevice(self, spec):
        """ Return a string describing the device the given specifier resolves to. """
        device = self._blivet.devicetree.resolve_device(spec)
        if device is None:
            raise dbus.exceptions.DBusException('%s.DeviceLookupFailed' % BUS_NAME,
                                                'No device was found that matches the device '
                                                'descriptor "%s".' % spec)

        object_path = next(p for (p, d) in self._dbus_devices.items() if d._device == device)
        return object_path

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, in_signature='o')
    def RemoveDevice(self, object_path):
        """ Remove a device and all devices built on it. """
        device = self.get_device_by_object_path(object_path)
        self._blivet.devicetree.recursive_remove(device)

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, in_signature='o')
    def InitializeDisk(self, object_path):
        """ Clear a disk and create a disklabel on it. """
        self.RemoveDevice(object_path)
        device = self.get_device_by_object_path(object_path)
        self._blivet.initialize_disk(device)

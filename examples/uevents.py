import time

import blivet3
from blivet3.events.manager import event_manager
from blivet3.util import set_up_logging


def print_changes(event, changes):
    print("***", event)
    for change in changes:
        print("***", change)
    print("***")
    print()


set_up_logging(console_logs=["blivet3.event"])
b = blivet.Blivet()  # create an instance of Blivet
b.reset()  # detect system storage configuration
print(b.devicetree)

event_manager.notify_cb = print_changes
event_manager.enable()

while True:
    time.sleep(0.5)

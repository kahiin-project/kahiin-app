from jnius import autoclass, cast
from android.runnable import run_on_ui_thread
from android.permissions import request_permissions, Permission

def request_android_permissions():
    request_permissions([
        Permission.INTERNET, 
        Permission.ACCESS_NETWORK_STATE,
        Permission.WAKE_LOCK,
        Permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
    ])
#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
kivy.require('1.11.1')
from android.permissions import request_permissions, Permission
from android import AndroidService
import signal
import socket
# Import just the Flask app
from kahiin.app import start_flask,stop_flask


service = AndroidService('Kahiin Service', 'running')

def signal_handler(signal, frame):
    print(" CTRL + C detected, exiting ... ")
    exit(0)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class MainScreen(Screen):
    def __init__(self, **kwargs):
        self.name = "MAIN SCREEN"
        super(Screen, self).__init__(**kwargs)

class MainApp(App):
    MainScreenTitle = "MainScreen title"
    MainScreenLabel = f"Local IP: {get_local_ip()}"
    MessageButtonEnter = "START"
    MessageButtonExit = "EXIT"
    
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
    
    def start(self):
        print("Starting Flask server...")
        def callback(permissions, results):
            if all([res for res in results]):
                print("Got all permissions!")
            else:
                print("Did not get all permissions!")
        request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE, Permission.WAKE_LOCK, Permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS], callback)

        service.start('service started')
        start_flask()
    
    def stop(self):
        print("Stopping Flask server...")
        service.stop()
        stop_flask()
    
    def on_stop(self):
        self.stop()
    
    def build(self):
        sm = Builder.load_string("""
ScreenManager:
    MainScreen:
        size_hint: 1, .7
        auto_dismiss: False
        title: app.MainScreenTitle
        title_align: "center"
        BoxLayout:
            orientation: "vertical"
            Label:
                text: app.MainScreenLabel
            BoxLayout:
                orientation: "horizontal"
                spacing: 10
                size_hint: 1, .5
                Button:
                    text: app.MessageButtonEnter
                    on_press: app.start()
                Button:
                    text: app.MessageButtonExit
                    on_press: app.stop()
        """)
        return sm

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    MainApp().run()

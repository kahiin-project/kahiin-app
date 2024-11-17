#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# kivy modules first, if not Kivy may cause problems
import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen
kivy.require('1.11.1')  # Set to your Kivy version
import hypercorn
from hypercorn.config import Config
import asyncio
from flask_socketio import SocketIO, emit
# common modules
import sys
import os
import time
import signal
from multiprocessing import Process
import threading
import socket

from kahiin import app as kahiin
# main.py
from kivy.support import install_twisted_reactor
install_twisted_reactor()

from flask import Flask
from flask_socketio import SocketIO
from threading import Lock
import eventlet


def signal_handler(signal, frame):
    print(" CTRL + C detected, exiting ... ")
    exit(0)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# kivy gui classes ######################################################
class MainScreen(Screen):
    def __init__(self, **kwargs):
        self.name = "MAIN SCREEN"
        super(Screen, self).__init__(**kwargs)

class MainApp(App):
    MainScreenTitle = "MainScreen title"
    MainScreenLabel = f"Local IP: {get_local_ip()}"  # Set the label to the local IP
    MessageButtonEnter = "START"
    MessageButtonExit = "EXIT"
    
    def start_Flask(self):
        print("Starting Flask...")
        # Using waitress instead of eventlet
        config = Config()
        config.bind = ["0.0.0.0:5000"]
        
        async def run_server():
            await hypercorn.asyncio.serve(kahiin.app, config)

        # Run the event loop in the current thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_server())
        print("Server started")
    
    def stop(self):
        print("terminating Flask and exiting...")
        global p1
        p1.terminate()
    
    def start(self):
        print("starting Flask as process...")
        global p1
        p1 = Process(target=self.start_Flask)  # assign Flask to a process
        p1.daemon = True
        p1.start()  # launch Flask as separate process
    
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
                    text: app.MessageButtonEnter  # start app
                    on_press:
                        app.start() 
                Button:
                    text: app.MessageButtonExit  # exit app
                    on_press:
                        app.stop()
        """)
        return sm

# main ################################################
if __name__ == '__main__':
    # CTRL+C signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    MainApp().run()  # run Kivy app
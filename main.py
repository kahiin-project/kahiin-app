#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
kivy.require('1.11.1')

import sys
import os
import time
import signal
import socket
import threading
import queue
from werkzeug.serving import make_server
from kahiin import app as flask_app  # Import just the Flask app

class ThreadSafeServer:
    def __init__(self, app):
        self.app = app
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.event_queue = queue.Queue()
        self.thread_lock = threading.Lock()
        
    def _process_events(self):
        while self.is_running:
            try:
                event = self.event_queue.get(timeout=0.1)
                if event == 'stop':
                    break
                # Process other events if needed
            except queue.Empty:
                continue

    def start_server(self):
        with self.thread_lock:
            if not self.server_thread:
                self.is_running = True
                # Create WSGI server
                self.server = make_server('0.0.0.0', 5000, self.app)
                self.server_thread = threading.Thread(target=self._run_server)
                self.server_thread.daemon = True
                
                # Start event processing thread
                self.event_thread = threading.Thread(target=self._process_events)
                self.event_thread.daemon = True
                
                self.server_thread.start()
                self.event_thread.start()

    def stop_server(self):
        if self.is_running:
            self.is_running = False
            self.event_queue.put('stop')
            if self.server:
                self.server.shutdown()
            if self.server_thread:
                self.server_thread.join()
            if self.event_thread:
                self.event_thread.join()
            self.server_thread = None
            self.event_thread = None

    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.is_running = False

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
        self.server = ThreadSafeServer(flask_app)
    
    def start(self):
        print("Starting Flask server...")
        self.server.start_server()
    
    def stop(self):
        print("Stopping Flask server...")
        self.server.stop_server()
    
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
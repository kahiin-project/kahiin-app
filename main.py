#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys
import traceback
import logging
from kivy.core.window import Window
from kivy.utils import platform
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kahiin.app import start_flask
from src.screens.main_screen import MainScreen
from src.utils.Settings import get_app_glossary
from src.services.signal_handler import setup_signal_handlers

import src.config
glossary = get_app_glossary()

class MainApp(MDApp):
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        self.flask_thread = None
        self.service = None
        
        # Prevent app from closing on back button
        Window.bind(on_keyboard=self.on_key)

    def on_key(self, window, key, *args):
        if key == 27:  # ESC/Back button
            return True
        return False

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(glossary=glossary))
        return sm

    def stop(self, *args):
        logging.info("Stopping application...")
        if self.flask_thread:
            logging.info("Attempting to stop Flask server")
        if self.service and platform == 'android':
            logging.info("Stopping Android service")
            self.service.stopForeground(True)
        else:
            logging.error("Error stopping application")
            traceback.print_exc()
            sys.exit(1)
            self.stop()

    def on_stop(self):
        main_screen = self.root.get_screen('main_screen')
        if main_screen.wakelock_acquired:
            main_screen.release_wakelock()
        super().on_stop()

def main():
    setup_signal_handlers()
    
    if platform == 'android':
        from src.android_utils import request_android_permissions
        request_android_permissions()
    
    MainApp().run()


if __name__ == '__main__':
    main()
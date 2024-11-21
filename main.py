#!/usr/bin/python3
# -*- coding: utf-8 -*-
import kivy
from kivy.config import Config
# Ensure multi-touch is disabled
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import os
import sys
import signal
import socket
import threading
import traceback
import logging

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.utils import platform
from kivy.core.window import Window

# Logging setup
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout),
                        logging.FileHandler('app_log.txt', mode='w')
                    ])

# Conditional imports for Android
if platform == 'android':
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    from android.permissions import request_permissions, Permission

class SafeButton(Button):
    def on_touch_down(self, touch):
        try:
            return super(SafeButton, self).on_touch_down(touch)
        except Exception as e:
            logging.error(f"Touch event error: {e}")
            traceback.print_exc()
            return False

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.name = "main_screen"

class MainApp(App):
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        self.local_ip = self.get_local_ip()
        self.flask_thread = None
        self.service = None
        
        # Prevent app from closing on back button
        Window.bind(on_keyboard=self.on_key)

    def on_key(self, window, key, *args):
        # Prevent back button from closing the app
        if key == 27:  # ESC/Back button
            return True
        return False

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.254.254.254', 1))
            IP = s.getsockname()[0]
        except Exception as e:
            logging.error(f"IP retrieval error: {e}")
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def start_flask_server(self):
        try:
            # Import Flask app here to avoid circular imports
            from kahiin.app import start_flask
            
            # Run Flask in a separate thread
            self.flask_thread = threading.Thread(target=start_flask, daemon=True)
            self.flask_thread.start()
            logging.info("Flask server started successfully")
        except Exception as e:
            logging.error(f"Failed to start Flask server: {e}")
            traceback.print_exc()

    def create_android_service(self):
        if platform == 'android':
            try:
                # Import Android-specific classes
                PythonService = autoclass('org.kivy.android.PythonService')
                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                
                # Get the service
                service = PythonService()
                
                # Create notification channel
                channel_id = "kahiin_service_channel"
                channel_name = "Kahiin Web Server"
                channel = NotificationChannel(
                    channel_id, 
                    channel_name, 
                    NotificationManager.IMPORTANCE_LOW
                )
                
                # Get notification manager and create channel
                notification_manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
                notification_manager.createNotificationChannel(channel)
                
                # Additional service setup can be added here
                logging.info("Android service created successfully")
                return service
            except Exception as e:
                logging.error(f"Failed to create Android service: {e}")
                traceback.print_exc()
                return None

    def on_start_button(self, *args):
        try:
            self.start_flask_server()
            if platform == 'android':
                self.service = self.create_android_service()
                
                # Request battery optimization exemption
                self.request_ignore_battery_optimizations()
        except Exception as e:
            logging.error(f"Startup error: {e}")
            traceback.print_exc()
    if platform == 'android':
        @run_on_ui_thread
        def request_ignore_battery_optimizations(self):
            if platform == 'android':
                try:
                    Context = autoclass('android.content.Context')
                    PowerManager = autoclass('android.os.PowerManager')
                    Intent = autoclass('android.content.Intent')
                    Uri = autoclass('android.net.Uri')
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')

                    # Get the current activity
                    context = PythonActivity.mActivity
                    
                    # Check if battery optimization is enabled
                    power_manager = context.getSystemService(Context.POWER_SERVICE)
                    package_name = context.getPackageName()
                    
                    if not power_manager.isIgnoringBatteryOptimizations(package_name):
                        # Request to ignore battery optimizations
                        intent = Intent(Intent.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                        intent.setData(Uri.parse(f"package:{package_name}"))
                        context.startActivity(intent)
                    
                    logging.info("Battery optimization request completed")
                except Exception as e:
                    logging.error(f"Battery optimization request failed: {e}")
                    traceback.print_exc()

    def build(self):
        # Create screen manager
        sm = ScreenManager()
        
        # Create main screen
        main_screen = MainScreen(name='main_screen')
        
        # Create layout
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # IP Address Label
        ip_label = Label(
            text=f"Local IP: {self.local_ip}", 
            font_size='20sp',
            size_hint_y=None, 
            height=50
        )
        layout.add_widget(ip_label)
        
        # Start Server Button (using SafeButton)
        start_button = SafeButton(
            text='Start Server', 
            on_press=self.on_start_button,
            size_hint_y=None, 
            height=200
        )
        layout.add_widget(start_button)
        
        # Exit Button (using SafeButton)
        exit_button = SafeButton(
            text='Exit App', 
            on_press=self.stop,
            size_hint_y=None, 
            height=200
        )
        layout.add_widget(exit_button)
        
        # Add layout to main screen
        main_screen.add_widget(layout)
        
        # Add screen to screen manager
        sm.add_widget(main_screen)
        
        return sm

    def stop(self, *args):
        try:
            logging.info("Stopping application...")
            
            # Stop Flask server (implement server stop logic in your Flask app)
            if self.flask_thread:
                # You may need to implement a proper stop mechanism in your Flask app
                logging.info("Attempting to stop Flask server")
            
            # Stop Android service if applicable
            if self.service and platform == 'android':
                logging.info("Stopping Android service")
                self.service.stopForeground(True)
            
            # Exit the app
            self.stop()
        except Exception as e:
            logging.error(f"Error during stop: {e}")
            traceback.print_exc()
            sys.exit(0)

def main():
    try:
        # Setup signal handlers for graceful exit
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}. Performing cleanup...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Request permissions on Android
        if platform == 'android':
            request_permissions([
                Permission.INTERNET, 
                Permission.ACCESS_NETWORK_STATE,
                Permission.WAKE_LOCK,
                Permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
            ])
        
        # Run the app
        MainApp().run()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
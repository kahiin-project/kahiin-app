#!/usr/bin/python3
# -*- coding: utf-8 -*-
import kivy
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import os
import sys
import signal
import socket
import threading
import traceback
import logging
import json
import hashlib

from kivy.core.window import Window
from kivy.utils import platform
from kivy.core.text import LabelBase
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivymd.icon_definitions import md_icons

from kahiin.app import start_flask

# Set the current directory to the one containing this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))
LabelBase.register(name='NotoSans', fn_regular='NotoSans.ttf')
LabelBase.register(name='MaterialIcons', fn_regular='MaterialDesignIcons.ttf')

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
    from android import mActivity

class SafeButton(MDRaisedButton):
    def on_touch_down(self, touch):
        try:
            return super(SafeButton, self).on_touch_down(touch)
        except Exception as e:
            logging.error(f"Touch event error: {e}")
            traceback.print_exc()
            return False

def get_local_ip():
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

def get_app_settings():
    with open('settings.json', 'r') as f:
        return json.load(f)

def get_kahiin_settings():
    with open(os.path.join(os.path.dirname(__file__), 'kahiin', 'settings.json'), 'r') as f:
        return json.load(f)

def get_app_glossary():
    with open('glossary.json', 'r') as f:
        return json.load(f)[get_app_settings().get('language')]
    
glossary = get_app_glossary()
class Tab(MDFloatLayout, MDTabsBase):
    pass

class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.name = "main_screen"
        self.app = MDApp.get_running_app()
        self.kahiin_settings_path = os.path.join(os.path.dirname(__file__), 'kahiin', 'settings.json')

        # Charger les paramètres actuels
        with open(self.kahiin_settings_path, 'r') as f:
            self.settings = json.load(f)

        self.flask_thread = None
        self.service = None
        self.wakelock_acquired = False
        self.wakelock = None

        # Create the main layout
        layout = MDBoxLayout(orientation='vertical')
        
        # Add tabs
        tabs = MDTabs()
        
        # Main tab
        main_tab = Tab(title='Serveur')
        main_content = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        # Fullscreen warning message
        warning_label = MDLabel(
            text=f"[size={dp(30)}px][font=MaterialDesignIcons]{md_icons['alert-rhombus']}[/font][/size] [size={dp(20)}px]" + glossary["KeepAppWake"] + "[/size]",
            theme_text_color="Error", 
            halign='center',
            markup=True, 
            size_hint_y=None,
            height=dp(50)
        )
        main_content.add_widget(warning_label)

        # IP Address Label
        ip_label = MDLabel(
            text=f"IP Locale: {get_local_ip()}",
            font_style='H5',
            size_hint_y=None,
            height=dp(50)
        )
        main_content.add_widget(ip_label)

        # Start Server Button
        self.start_button = self.create_button(
            text=f'{glossary["StartServer"]}',
            icon='server-network',
            on_press=self.on_start_button,
            md_bg_color=(0.2, 0.8, 0.2, 1)
        )
        main_content.add_widget(self.start_button)

        self.stop_button = self.create_button(
            text=f'{glossary["StopServer"]}',
            on_press=self.on_stop_button,
            md_bg_color=(0.5, 0.5, 0.5, 1),
            disabled=True
        )

        # Exit Button
        exit_button = self.create_button(
            text=f'{glossary["ExitApp"]}',
            icon='exit-to-app',
            on_press=self.stop_app,
            md_bg_color=(0.8, 0.2, 0.2, 1)
        )
        main_content.add_widget(exit_button)

        # Wakelock Button
        self.wakelock_button = self.create_button(
            text='Activer le Wakelock',
            on_press=self.toggle_wakelock,
            md_bg_color=(0.2, 0.2, 0.8, 1)
        )
        main_content.add_widget(self.wakelock_button)

        main_tab.add_widget(main_content)

        # Settings tab
        settings_tab = Tab(title='Paramètres')
        settings_content = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))

        # Language selection with flags
        languages = {
            'fr': {'icon': md_icons["baguette"], 'name': 'Français'},
            'en': {'icon': md_icons["tea"], 'name': 'English'},
            'es': {'icon': md_icons["weather-sunny"], 'name': 'Español'},
            'it': {'icon': md_icons["pizza"], 'name': 'Italiano'},
            'de': {'icon': md_icons["sausage"], 'name': 'Deutsch'}
        }
        lang_box = MDBoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(60))
        self.btn_list = []
        self.lang_btn_list = []
        for lang_code, lang_info in languages.items():
            lang_btn = self.create_button(
                text=f"[size={dp(20)}px][font=MaterialDesignIcons]{lang_info['icon']}[/font][/size] {lang_info['name']}",
                on_press=lambda x, lc=lang_code: self.change_language(lc),
                md_bg_color=self.get_language_color(lang_code)
            )
            self.btn_list.append(lang_btn)
            self.lang_btn_list.append((lang_btn, lang_code))
            lang_box.add_widget(lang_btn)
        settings_content.add_widget(lang_box)

        # Accessibility settings title
        access_label = MDLabel(
            text=glossary['AccessibilitySettings'],
            font_style='H6',
            size_hint_y=None,
            height=dp(40)
        )
        settings_content.add_widget(access_label)

        # Accessibility settings buttons
        access_box = MDBoxLayout(orientation='vertical', spacing=dp(10), adaptive_height=True)
        
        self.dyslexic_btn = self.create_button(
            text=glossary['DyslexicMode'],
            on_press=lambda x: self.toggle_setting('dyslexicMode', self.dyslexic_btn),
            md_bg_color=self.get_button_color('dyslexicMode')
        )
        
        self.endOnAllAnswered_btn = self.create_button(
            text=glossary['EndOnAllAnswered'],
            on_press=lambda x: self.toggle_setting('endOnAllAnswered', self.endOnAllAnswered_btn),
            md_bg_color=self.get_button_color('endOnAllAnswered')
        )

        self.randomOrder_btn = self.create_button(
            text=glossary['RandomOrder'],
            on_press=lambda x: self.toggle_setting('randomOrder', self.randomOrder_btn),
            md_bg_color=self.get_button_color('randomOrder')
        )

        access_box.add_widget(self.dyslexic_btn)
        access_box.add_widget(self.endOnAllAnswered_btn)
        access_box.add_widget(self.randomOrder_btn)
        settings_content.add_widget(access_box)

        # Password section with validation button
        pwd_box = MDBoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(60))
        
        self.password_field = MDTextField(
            hint_text=glossary['ChangePassword'],
            password=True,
            size_hint_x=0.7
        )
        
        pwd_button = self.create_button(
            text=glossary['Change'],
            on_press=lambda x: self.change_password(self.password_field.text),
            md_bg_color=(0.2, 0.2, 0.8, 1)
        )
        self.btn_list.extend([self.dyslexic_btn, self.endOnAllAnswered_btn, self.randomOrder_btn, pwd_button])
        pwd_box.add_widget(self.password_field)
        pwd_box.add_widget(pwd_button)
        settings_content.add_widget(pwd_box)

        settings_tab.add_widget(settings_content)

        # Add tabs to layout
        tabs.add_widget(main_tab)
        tabs.add_widget(settings_tab)
        layout.add_widget(tabs)

        self.add_widget(layout)

    def create_button(self, text, on_press, md_bg_color, icon=None, disabled=False):
        return SafeButton(
            text=text,
            on_press=on_press,
            md_bg_color=md_bg_color,
            size_hint_y=None,
            height=dp(50),
            font_size=dp(18),
            disabled=disabled
        )

    def update_settings(self):
        with open('settings.json', 'r') as f:
            self.app_settings = json.load(f)

    def update_kahiin_settings(self):
        # Charger les paramètres depuis le fichier
        with open(self.kahiin_settings_path, 'r') as f:
            self.settings = json.load(f)

    def get_button_color(self, setting_name):
        self.update_kahiin_settings()
        return (0.2, 0.8, 0.2, 1) if self.settings.get(setting_name, False) else (0.8, 0.2, 0.2, 1)
    
    def get_language_color(self, lang_code):
        self.update_settings()
        return (0.2, 0.8, 0.2, 1) if lang_code == self.app_settings.get('language') else (0.8, 0.2, 0.2, 1)

    def change_language(self, lang_code):
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        settings['language'] = lang_code
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        for btn in self.lang_btn_list:
            btn[0].md_bg_color = self.get_language_color(btn[1])
        
    def change_password(self, new_password):
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        self.settings['adminPassword'] = hashed_password
        self.update_settings()
        toast(glossary['PasswordChanged'])

    def start_flask_server(self):
        self.flask_thread = threading.Thread(target=start_flask, daemon=True)
        self.flask_thread.start()      
        logging.info("Flask server started successfully")

    def create_android_service(self):
        if platform == 'android':
            PythonService = autoclass('org.kivy.android.PythonService')
            service = PythonService.mService
            logging.info("Service Android par défaut utilisé.")
            return service
        
    def on_start_button(self, *args):
        self.start_flask_server()
        if platform == 'android':
            self.service = self.create_android_service()
            self.request_ignore_battery_optimizations()
        self.start_button.disabled = True
        self.start_button.md_bg_color = (0.5, 0.5, 0.5, 1)
        for btn in self.btn_list:
            btn.disabled = True
            btn.md_color = (0.5, 0.5, 0.5, 1)
        self.password_field.disabled = True
        self.stop_button.disabled = False
        self.stop_button.md_color = (0.8, 0.2, 0.2, 1)

    
    def on_stop_button(self, *args):
        self.stop_flask_server()
        self.stop_button.md_color = (0.5, 0.5, 0.5, 1)
        self.stop_button.disabled = True

    if platform == 'android':
        @run_on_ui_thread
        def request_ignore_battery_optimizations(self):
            # if the battery settings are already set dont do anythin
            if os.path.exists('.battery_optimization_informed'):
                return
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            Uri = autoclass('android.net.Uri')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
    
            context = PythonActivity.mActivity
            intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
            context.startActivity(intent)
            # create a file to indicate that the user has been informed
            with open('.battery_optimization_informed', 'w') as f:
                f.write('')
            toast(glossary['DisableBatteryOptimizations'])
            logging.info("Paramètres d'optimisation de la batterie ouverts.")

    def stop_app(self, *args):
        self.app.stop()

    def toggle_setting(self, setting_name, button):
        settings = get_kahiin_settings()
        settings[setting_name] = not settings[setting_name]
        with open(self.kahiin_settings_path, 'w') as f:
            json.dump(settings, f)
        button.md_bg_color = self.get_button_color(setting_name)
        toast(glossary["Setting"] + " " + setting_name + " " + (glossary["Enabled"] if self.settings[setting_name] else glossary["Disabled"]))

    def toggle_wakelock(self, *args):
        if not self.wakelock_acquired:
            self.acquire_wakelock()
        else:
            self.release_wakelock()

    def acquire_wakelock(self):
        if platform == 'android':
            try:
                PowerManager = autoclass('android.os.PowerManager')
                Context = autoclass('android.content.Context')
                activity = mActivity
                pm = activity.getSystemService(Context.POWER_SERVICE)
                self.wakelock = pm.newWakeLock(PowerManager.FULL_WAKE_LOCK, 'MyApp::WakelockTag')
                self.wakelock.acquire()
                self.wakelock_acquired = True
                self.wakelock_button.text = 'Désactiver le Wakelock'
                toast('Wakelock activé')
            except Exception as e:
                print(f"Erreur lors de l'activation du wakelock: {e}")
        else:
            toast('Wakelock non pris en charge sur cette plateforme')

    def release_wakelock(self):
        if self.wakelock_acquired and self.wakelock is not None:
            self.wakelock.release()
            self.wakelock_acquired = False
            self.wakelock_button.text = 'Activer le Wakelock'
            toast('Wakelock désactivé')


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
        sm.add_widget(MainScreen())
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
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}. Performing cleanup...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if platform == 'android':
        request_permissions([
            Permission.INTERNET, 
            Permission.ACCESS_NETWORK_STATE,
            Permission.WAKE_LOCK,
            Permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
        ])
    
    MainApp().run()


if __name__ == '__main__':
    main()
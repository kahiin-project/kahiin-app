#!/usr/bin/python3
# -*- coding: utf-8 -*-
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import os
import threading
import logging
import json
import hashlib
import socket

from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivymd.icon_definitions import md_icons
from kivymd.uix.tab import MDTabs

from kahiin.app import start_flask
from src.ui.Tab import Tab
from src.ui.SafeButton import SafeButton

if platform == 'android':
    from jnius import autoclass
    from android.runnable import run_on_ui_thread
    
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

class MainScreen(MDScreen):
    def __init__(self, glossary, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.glossary = glossary
        self.name = "main_screen"
        self.app = MDApp.get_running_app()
        self.kahiin_settings_path = "settings.json"

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
            text=f"[size={dp(30)}px][font=MaterialIcons]{md_icons['alert-rhombus']}[/font][/size] [size={dp(20)}px]" + self.glossary["KeepAppWake"] + "[/size]",
            theme_text_color="Error", 
            halign='center',
            markup=True, 
            size_hint_y=None,
            # height=dp(50),
            font_name='Bagnard'
        )
        main_content.add_widget(warning_label)

        # IP Address Label
        ip_label = MDLabel(
            text=f"IP Locale: {get_local_ip()}",
            font_style='H5',
            size_hint_y=None,
            height=dp(50),
            font_name='Bagnard'
        )
        main_content.add_widget(ip_label)

        # Start Server Button
        self.start_button = self.create_button(
            text=f'{self.glossary["StartServer"]}',
            icon='server-network',
            on_press=self.on_start_button,
            md_bg_color=(0.2, 0.8, 0.2, 1),
            font_name='Bagnard'
        )
        main_content.add_widget(self.start_button)

        self.stop_button = self.create_button(
            text=f'{self.glossary["StopServer"]}',
            on_press=self.on_stop_button,
            md_bg_color=(0.5, 0.5, 0.5, 1),
            disabled=True,
            font_name='Bagnard'
        )

        # Exit Button
        exit_button = self.create_button(
            text=f'{self.glossary["ExitApp"]}',
            icon='exit-to-app',
            on_press=self.stop_app,
            md_bg_color=(0.8, 0.2, 0.2, 1),
            font_name='Bagnard'
        )
        main_content.add_widget(exit_button)

        # Wakelock Button
        self.wakelock_button = self.create_button(
            text='Activer le Wakelock',
            on_press=self.toggle_wakelock,
            md_bg_color=(0.2, 0.2, 0.8, 1),
            font_name='Bagnard'
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
                text=f"[size={dp(20)}px][font=MaterialIcons]{lang_info['icon']}[/font][/size] {lang_info['name']}",
                on_press=lambda x, lc=lang_code: self.change_language(lc),
                md_bg_color=self.get_language_color(lang_code),
                font_name='Bagnard'
            )
            self.btn_list.append(lang_btn)
            self.lang_btn_list.append((lang_btn, lang_code))
            lang_box.add_widget(lang_btn)
        settings_content.add_widget(lang_box)

        # Accessibility settings title
        access_label = MDLabel(
            text=self.glossary['AccessibilitySettings'],
            font_style='H6',
            size_hint_y=None,
            height=dp(40),
            font_name='Bagnard'
        )
        settings_content.add_widget(access_label)

        # Accessibility settings buttons
        access_box = MDBoxLayout(orientation='vertical', spacing=dp(10), adaptive_height=True)
        
        self.dyslexic_btn = self.create_button(
            text=self.glossary['DyslexicMode'],
            on_press=lambda x: self.toggle_setting('dyslexicMode', self.dyslexic_btn),
            md_bg_color=self.get_button_color('dyslexicMode'),
            font_name='Bagnard'
        )
        
        self.endOnAllAnswered_btn = self.create_button(
            text=self.glossary['EndOnAllAnswered'],
            on_press=lambda x: self.toggle_setting('endOnAllAnswered', self.endOnAllAnswered_btn),
            md_bg_color=self.get_button_color('endOnAllAnswered'),
            font_name='Bagnard'
        )

        self.randomOrder_btn = self.create_button(
            text=self.glossary['RandomOrder'],
            on_press=lambda x: self.toggle_setting('randomOrder', self.randomOrder_btn),
            md_bg_color=self.get_button_color('randomOrder'),
            font_name='Bagnard'
        )

        access_box.add_widget(self.dyslexic_btn)
        access_box.add_widget(self.endOnAllAnswered_btn)
        access_box.add_widget(self.randomOrder_btn)
        settings_content.add_widget(access_box)

        # Password section with validation button
        pwd_box = MDBoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(60))
        
        self.password_field = MDTextField(
            hint_text=self.glossary['ChangePassword'],
            password=True,
            size_hint_x=0.7,
            font_name='Bagnard'
        )
        
        pwd_button = self.create_button(
            text=self.glossary['Change'],
            on_press=lambda x: self.change_password(self.password_field.text),
            md_bg_color=(0.2, 0.2, 0.8, 1),
            font_name='Bagnard'
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

    def create_button(self, text, on_press, md_bg_color, icon=None, disabled=False, font_name='CustomFont'):
        return SafeButton(
            text=text,
            on_press=on_press,
            md_bg_color=md_bg_color,
            size_hint_y=None,
            height=dp(50),
            font_size=dp(18),
            disabled=disabled,
            font_name=font_name,
            elevation=0
        )

    def update_settings(self):
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'settings.json'), 'r') as f:
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
        toast(self.glossary['PasswordChanged'])

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
            toast(self.glossary['DisableBatteryOptimizations'])
            logging.info("Paramètres d'optimisation de la batterie ouverts.")

    def stop_app(self, *args):
        self.app.stop()

    def toggle_setting(self, setting_name, button):
        settings = get_kahiin_settings()
        settings[setting_name] = not settings[setting_name]
        with open(self.kahiin_settings_path, 'w') as f:
            json.dump(settings, f)
        button.md_bg_color = self.get_button_color(setting_name)
        toast(self.glossary["Setting"] + " " + setting_name + " " + (self.glossary["Enabled"] if self.settings[setting_name] else self.glossary["Disabled"]))

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
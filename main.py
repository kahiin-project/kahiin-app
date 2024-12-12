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

from kivy.core.window import Window
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivymd.uix.list import OneLineListItem
from kivymd.icon_definitions import md_icons
import json
from kahiin.app import start_flask #, stop_flask
import hashlib
from kivy.core.text import LabelBase


# set the current dir to the one containing this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))
LabelBase.register(name='NotoSans', fn_regular=os.path.join(os.path.dirname(__file__), 'NotoSans.ttf'))
LabelBase.register(name='MaterialIcons', fn_regular=os.path.join(os.path.dirname(__file__), 'MaterialDesignIcons.ttf'))
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

class Tab(MDFloatLayout, MDTabsBase):
    pass

# Modifions la classe MainScreen pour ajouter les onglets
class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.name = "main_screen"
        self.app = MDApp.get_running_app()  # Référence à l'app principale
        self.flask_thread = None
        self.service = None

        # Charger les paramètres actuels
        with open(os.path.join(os.path.dirname(__file__), 'kahiin', 'settings.json'), 'r') as f:
            self.settings = json.load(f)

        # Créer le layout principal
        layout = MDBoxLayout(orientation='vertical')
        
        # Ajouter les tabs
        tabs = MDTabs()
        
        # Tab principale
        main_tab = Tab(title='Serveur')
        main_content = MDBoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Message de garde en plein écran
        warning_label = MDLabel(
            text=f"[size=30px][font=MaterialDesignIcons]{md_icons['alert-rhombus']}[/font][/size] [size=20px]Gardez l'application en plein écran pour éviter qu'Android ne la ferme[/size]",
            font_name='NotoSans',
            theme_text_color="Error", 
            halign='center',
            markup=True, 
            size_hint_y=None,
            height=50
        )
        main_content.add_widget(warning_label)

        # IP Address Label
        ip_label = MDLabel(
            text=f"IP Locale: {get_local_ip()}",
            font_style='H5',
            size_hint_y=None,
            height=50
        )
        main_content.add_widget(ip_label)

        # Start Server Button stylisé avec la bonne référence
        self.start_button = SafeButton(
            text='Démarrer le serveur',
            icon='server-network',
            on_press=self.on_start_button, 
            md_bg_color=(0.2, 0.8, 0.2, 1),
            size_hint_y=None,
            height=50
        )
        main_content.add_widget(self.start_button)

        self.stop_button = SafeButton(
            text='Arrêter le serveur',
            on_press=self.on_stop_button,
            md_bg_color=(0.5, 0.5, 0.5, 1),
            disabled=True,
            height=50,
            size_hint_y=None,
        )

        # main_content.add_widget(self.stop_button)



        exit_button = SafeButton(
            text='Quitter',
            icon='exit-to-app',
            on_press=self.stop_app, 
            md_bg_color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None,
            height=50
        )
        main_content.add_widget(exit_button)
        main_tab.add_widget(main_content)

        # Tab paramètres
        settings_tab = Tab(title='Paramètres')
        settings_content = MDBoxLayout(orientation='vertical', padding=20, spacing=10)

        # Sélection de langue avec drapeaux
        languages = {
            'fr': {'icon': md_icons["baguette"], 'name': 'Français'},
            'en': {'icon': md_icons["tea"], 'name': 'English'},
            'es': {'icon': md_icons["weather-sunny"], 'name': 'Español'}
        }
        lang_box = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=60)
        self.btn_list = []
        for lang_code, lang_info in languages.items():
            lang_btn = MDRaisedButton(
                text=f"[size=20px][font=MaterialDesignIcons]{lang_info['icon']}[/font][/size] {lang_info['name']}",
                on_press=lambda x, lc=lang_code: self.change_language(lc),
                font_name='NotoSans',
                size_hint_y=None,
                height=50

            )
            self.btn_list.append(lang_btn)
            lang_box.add_widget(lang_btn)
        settings_content.add_widget(lang_box)

        # Titre de la section Accessibilité
        access_label = MDLabel(
            text="Paramètres d'accessibilité",
            font_style='H6',
            size_hint_y=None,
            height=40
        )
        settings_content.add_widget(access_label)

        # Boutons pour les paramètres d'accessibilité
        access_box = MDBoxLayout(orientation='vertical', spacing=10, adaptive_height=True)
        
        self.dyslexic_btn = MDRaisedButton(
            text="Mode dyslexique",
            on_press=lambda x: self.toggle_setting('dyslexicMode', self.dyslexic_btn),
            size_hint_y=None,
            height=50,
            md_bg_color=self.get_button_color('dyslexicMode')
        )
        
        self.endOnAllAnswered_btn = MDRaisedButton(
            text="Finir quand tous ont répondu",
            on_press=lambda x: self.toggle_setting('endOnAllAnswered', self.endOnAllAnswered_btn),
            size_hint_y=None,
            height=50,
            md_bg_color=self.get_button_color('endOnAllAnswered')
        )

        self.randomOrder_btn = MDRaisedButton(
            text="Ordre aléatoire",
            on_press=lambda x: self.toggle_setting('randomOrder', self.randomOrder_btn),
            size_hint_y=None,
            height=50,
            md_bg_color=self.get_button_color('randomOrder')
        )

        access_box.add_widget(self.dyslexic_btn)
        access_box.add_widget(self.endOnAllAnswered_btn)
        access_box.add_widget(self.randomOrder_btn)
        settings_content.add_widget(access_box)

        # Section mot de passe avec bouton de validation
        pwd_box = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=60)
        
        self.password_field = MDTextField(
            hint_text="Nouveau mot de passe admin",
            password=True,
            helper_text="Laissez vide pour ne pas changer",
            size_hint_x=0.7
        )
        
        pwd_button = MDRaisedButton(
            text="Changer",
            on_press=lambda x: self.change_password(self.password_field.text),
            size_hint_x=0.3
        )
        self.btn_list.extend([self.dyslexic_btn,self.endOnAllAnswered_btn,self.randomOrder_btn, pwd_button])
        pwd_box.add_widget(self.password_field)
        pwd_box.add_widget(pwd_button)
        settings_content.add_widget(pwd_box)

        settings_tab.add_widget(settings_content)

        # Ajouter les tabs
        tabs.add_widget(main_tab)
        tabs.add_widget(settings_tab)
        layout.add_widget(tabs)

        self.add_widget(layout)

    def get_button_color(self, setting_name):
        return (0.2, 0.8, 0.2, 1) if self.settings.get(setting_name, False) else (0.8, 0.2, 0.2, 1)

    def change_language(self, lang_code):
        try:
            with (os.path.join(os.path.dirname(__file__), 'kahiin/settings.json'), 'r') as f:
                settings = json.load(f)
            settings['language'] = lang_code
            with (os.path.join(os.path.dirname(__file__), 'kahiin/settings.json'), 'w') as f:
                json.dump(settings, f)
            toast(f"Langue changée en {lang_code}")
        except Exception as e:
            toast(f"Erreur: {str(e)}")

    def change_password(self, new_password):
        try:
            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
            with open(os.path.join(os.path.dirname(__file__), 'kahiin/settings.json'), 'r') as f:
                settings = json.load(f)
            settings['adminPassword'] = hashed_password
            with open(os.path.join(os.path.dirname(__file__), 'kahiin/settings.json'), 'w') as f:
                json.dump(settings, f)
            toast("Mot de passe changé avec succès")
        except Exception as e:
            print(f"Erreur: {str(e)}")

    def start_flask_server(self):
        try:
            self.flask_thread = threading.Thread(target=start_flask, daemon=True)
            self.flask_thread.start()
            logging.info("Flask server started successfully")
        except Exception as e:
            logging.error(f"Failed to start Flask server: {e}")
            traceback.print_exc()




    def create_android_service(self):
        if platform == 'android':
            try:
                PythonService = autoclass('org.kahiin.android.WebServerService')
                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                
                service = PythonService()
                
                channel_id = "kahiin_service_channel"
                channel_name = "Kahiin Web Server"
                channel = NotificationChannel(
                    channel_id, 
                    channel_name, 
                    NotificationManager.IMPORTANCE_LOW
                )
                
                notification_manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
                notification_manager.createNotificationChannel(channel)
                
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
                self.request_ignore_battery_optimizations()
            # Désactiver le bouton et le griser
            self.start_button.disabled = True
            self.start_button.md_bg_color = (0.5, 0.5, 0.5, 1)
            for btn in self.btn_list:
                btn.disabled = True
                btn.md_color = (0.5, 0.5, 0.5, 1)
            self.password_field.disabled = True
            self.stop_button.disabled = False
            self.stop_button.md_color = (0.8, 0.2, 0.2, 1)

        except Exception as e:
            logging.error(f"Startup error: {e}")
            traceback.print_exc()
    
    def on_stop_button(self, *args):
        self.stop_flask_server()
        self.stop_button.md_color = (0.5, 0.5, 0.5, 1)
        self.stop_button.disabled = True

    if platform == 'android':
        @run_on_ui_thread
        def request_ignore_battery_optimizations(self):
            try:
                Context = autoclass('android.content.Context')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kahiin.android.WebServerActivity')

                context = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                context.startActivity(intent)
                
                logging.info("Battery optimization settings opened")
            except Exception as e:
                logging.error(f"Battery optimization request failed: {e}")
                traceback.print_exc()

    def stop_app(self, *args):
        try:
            logging.info("Stopping application...")
            
            if self.flask_thread:
                logging.info("Attempting to stop Flask server")
            
            if self.service and platform == 'android':
                logging.info("Stopping Android service")
                self.service.stopForeground(True)
            
            self.app.stop()  # Utilise la référence à l'app principale
        except Exception as e:
            logging.error(f"Error during stop: {e}")
            traceback.print_exc()
            sys.exit(0)

    def toggle_setting(self, setting_name, button):
        try:
            self.settings[setting_name] = not self.settings.get(setting_name, False)
            with open(os.path.join(os.path.dirname(__file__), 'kahiin', 'settings.json'), 'w') as f:
                json.dump(self.settings, f, indent=4)
            # Mettre à jour la couleur du bouton
            button.md_bg_color = self.get_button_color(setting_name)
            toast(f"Paramètre {setting_name} {'activé' if self.settings[setting_name] else 'désactivé'}")
        except Exception as e:
            toast(f"Erreur: {str(e)}")

class MainApp(MDApp):
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        self.flask_thread = None
        self.service = None
        
        # Prevent app from closing on back button
        Window.bind(on_keyboard=self.on_key)

    def on_key(self, window, key, *args):
        # Prevent back button from closing the app
        if key == 27:  # ESC/Back button
            return True
        return False

    def build(self):
        # Create screen manager
        sm = ScreenManager()
    
        sm.add_widget(MainScreen())
        
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
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
from kivy.utils import platform, get_color_from_hex
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivymd.icon_definitions import md_icons
from kivymd.uix.tab import MDTabs
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.menu import MDDropdownMenu

from kahiin.app import start_flask
from src.ui.Tab import Tab
from src.ui.SafeButton import SafeButton

from src.utils.Settings import get_kahiin_settings
if platform == 'android':
    from jnius import autoclass
    from android.runnable import run_on_ui_thread

# Modern color palette with dark gray instead of purple
COLORS = {
    'primary': get_color_from_hex("#333333"),  # Dark gray instead of purple
    'primary_dark': get_color_from_hex("#212121"),  # Very dark gray
    'accent': get_color_from_hex("#5D5D5D"),  # Medium gray
    'background': get_color_from_hex("#FFFFFF"),
    'card': get_color_from_hex("#F5F5F5"),
    'text': get_color_from_hex("#333333"),
    'success': get_color_from_hex("#4CAF50"),
    'warning': get_color_from_hex("#FFC107"),
    'error': get_color_from_hex("#F44336"),
    'info': get_color_from_hex("#2196F3"),
}
    
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
        self.kahiin_settings_path = os.path.join('kahiin','settings.json')
        
        # Variables for language dropdown
        self.current_language = None
        self.language_menu = None

        # Set the background color of the screen
        self.md_bg_color = COLORS['background']

        # Load current settings
        with open(self.kahiin_settings_path, 'r') as f:
            self.settings = json.load(f)
            
        # Load application settings
        try:
            with open('settings.json', 'r') as f:
                self.app_settings = json.load(f)
                self.current_language = self.app_settings.get('language', 'fr')
        except:
            self.current_language = 'fr'

        self.flask_thread = None
        self.service = None
        self.wakelock_acquired = False
        self.wakelock = None

        # Initialize the interface
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Create the main layout
        layout = MDBoxLayout(orientation='vertical')
        
        # Add a toolbar at the top
        toolbar = MDTopAppBar(
            title="Kahiin App",
            elevation=0,
            md_bg_color=COLORS['primary'],
            specific_text_color=get_color_from_hex("#FFFFFF"),
        )
        layout.add_widget(toolbar)
        
        # Add tabs with custom styling
        tabs = MDTabs(
            background_color=COLORS['primary'],
            text_color_normal=get_color_from_hex("#CCCCCC"),
            text_color_active=get_color_from_hex("#FFFFFF"),
            indicator_color=COLORS['accent'],
            elevation=0,
            tab_hint_x=0.5  # Each tab takes half of the width
        )
        
        # Main tab
        main_tab = Tab(title=self.glossary["ServerTab"], icon="server")
        main_content = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15), size_hint_y=1)
        
        # Card for server info
        server_card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
            elevation=0,
            radius=dp(5),
            ripple_behavior=True,
            size_hint_y=1  # Takes all available space
        )
        
        # IP Address Label with modern style - put IP first and larger
        ip_box = MDBoxLayout(
            orientation='vertical',
            size_hint_y=1,  # Use all available space
            padding=[dp(10), dp(30), dp(10), dp(30)],  # Large vertical padding
        )

        ip_label = MDLabel(
            text=f"{get_local_ip()}[color=#CCCCCC]:8080[/color]",
            font_style='H3',
            size_hint_y=1,  # Takes all remaining space
            font_name='Bagnard',
            halign='center',
            valign='middle',
            theme_text_color="Primary",
            bold=True,
            markup=True,
        )

        ip_box.add_widget(ip_label)
        server_card.add_widget(ip_box)

        # Fullscreen warning message with reduced size
        warning_label = MDLabel(
            text=f"[size={dp(20)}px][font=MaterialIcons]{md_icons['alert-rhombus']}[/font][/size] [size={dp(14)}px]" + self.glossary["KeepAppWake"] + "[/size]",
            theme_text_color="Error", 
            halign='center',
            markup=True, 
            size_hint_y=None,  # Fixed height instead of proportion
            height=dp(40),  # Reduced fixed height
            font_name='Bagnard',
            padding=(0, dp(5))  # Reduced padding
        )
        server_card.add_widget(warning_label)

        # Button Card for server controls
        button_card = MDCard(
            orientation="vertical",
            padding=[dp(16), dp(5), dp(16), dp(16)],  # Reduce padding at the top
            spacing=dp(10),
            elevation=0,
            radius=dp(5),
            size_hint_y=None,
            height=dp(165),  # Reduce height to account for removed button
            md_bg_color=get_color_from_hex("#F4F4F4"),
        )

        # Start Server Button
        self.start_button = self.create_button(
            text=f'{self.glossary["StartServer"]}',
            icon='server-network',
            on_press=self.on_start_button,
            md_bg_color=COLORS['success'],
            font_name='Bagnard',
            height=dp(45)  # Reduce button height
        )
        button_card.add_widget(self.start_button)

        # Wakelock Button
        self.wakelock_button = self.create_button(
            text=self.glossary["EnableWakelock"],
            on_press=self.toggle_wakelock,
            md_bg_color=COLORS['info'],
            font_name='Bagnard',
            height=dp(45)  # Consistent height
        )
        button_card.add_widget(self.wakelock_button)

        # Exit Button
        exit_button = self.create_button(
            text=f'{self.glossary["ExitApp"]}',
            icon='exit-to-app',
            on_press=self.stop_app,
            md_bg_color=COLORS['error'],
            font_name='Bagnard',
            height=dp(45)  # Consistent height
        )
        button_card.add_widget(exit_button)
        
        main_content.add_widget(server_card)
        main_content.add_widget(button_card)
        main_tab.add_widget(main_content)

        # Settings tab
        settings_tab = Tab(title=self.glossary["SettingsTab"], icon="cog")
        
        # Add a ScrollView to allow scrolling
        scroll_view = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=4,
            bar_color=COLORS['primary'],
            effect_cls='ScrollEffect'
        )
        
        settings_content = MDBoxLayout(
            orientation='vertical', 
            padding=dp(20), 
            spacing=dp(15),
            size_hint_y=None,
            height=dp(600)  # Sufficient height to contain all content
        )
        
        # Set height based on content
        settings_content.bind(minimum_height=settings_content.setter('height'))
        
        # Card for language selection
        lang_card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
            elevation=0,
            radius=dp(5),
            size_hint_y=None,
            height=dp(120),
            md_bg_color=get_color_from_hex("#F4F4F4"),
        )
        
        # Language title
        lang_title = MDLabel(
            text=self.glossary["LanguageTitle"],
            font_style='H6',
            size_hint_y=None,
            height=dp(30),
            font_name='Bagnard',
            theme_text_color="Secondary",
            padding=(0, dp(8))  # Add uniform vertical padding
        )
        lang_card.add_widget(lang_title)
        
        # Button for language dropdown
        languages = {
            'fr': {'icon': md_icons["baguette"], 'name': 'Français'},
            'en': {'icon': md_icons["tea"], 'name': 'English'},
            'es': {'icon': md_icons["weather-sunny"], 'name': 'Español'},
            'it': {'icon': md_icons["pizza"], 'name': 'Italiano'},
            'de': {'icon': md_icons["sausage"], 'name': 'Deutsch'}
        }
        
        # Button to display dropdown
        self.lang_dropdown_button = self.create_button(
            text=f"[size={dp(20)}px][font=MaterialIcons]{languages[self.current_language]['icon']}[/font][/size] {languages[self.current_language]['name']}",
            on_press=self.show_language_menu,
            md_bg_color=COLORS['primary'],
            font_name='Bagnard',
            height=dp(50),
        )
        
        lang_card.add_widget(self.lang_dropdown_button)
        
        # Create menu items
        menu_items = []
        for lang_code, lang_info in languages.items():
            menu_items.append({
                "text": f"{lang_info['name']}",
                "viewclass": "OneLineListItem",
                "on_release": lambda x=lang_code: self.change_language(x),
                "icon": lang_info['icon']
            })
            
        # Create dropdown menu
        self.language_menu = MDDropdownMenu(
            caller=self.lang_dropdown_button,
            items=menu_items,
            width_mult=4,
            max_height=dp(250),
            background_color=COLORS['card'],
        )
        
        settings_content.add_widget(lang_card)

        # Card for accessibility settings
        access_card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
            elevation=0,
            radius=dp(5),
            size_hint_y=None,
            height=dp(220),
            md_bg_color=get_color_from_hex("#F4F4F4"),
        )
        
        # Accessibility settings title
        access_label = MDLabel(
            text=self.glossary['AccessibilitySettings'],
            font_style='H6',
            size_hint_y=None,
            height=dp(30),
            font_name='Bagnard',
            theme_text_color="Secondary",
            padding=(0, dp(8))  # Add uniform vertical padding
        )
        access_card.add_widget(access_label)

        # Accessibility settings buttons
        access_box = MDBoxLayout(orientation='vertical', spacing=dp(10), adaptive_height=True)
        
        self.dyslexic_btn = self.create_button(
            text=self.glossary['DyslexicMode'],
            on_press=lambda x: self.toggle_setting('dyslexicMode', self.dyslexic_btn),
            md_bg_color=self.get_button_color('dyslexicMode'),
            font_name='Bagnard',
            height=dp(45),
        )
        
        self.endOnAllAnswered_btn = self.create_button(
            text=self.glossary['EndOnAllAnswered'],
            on_press=lambda x: self.toggle_setting('endOnAllAnswered', self.endOnAllAnswered_btn),
            md_bg_color=self.get_button_color('endOnAllAnswered'),
            font_name='Bagnard',
            height=dp(45),
        )

        self.randomOrder_btn = self.create_button(
            text=self.glossary['RandomOrder'],
            on_press=lambda x: self.toggle_setting('randomOrder', self.randomOrder_btn),
            md_bg_color=self.get_button_color('randomOrder'),
            font_name='Bagnard',
            height=dp(45),
        )

        access_box.add_widget(self.dyslexic_btn)
        access_box.add_widget(self.endOnAllAnswered_btn)
        access_box.add_widget(self.randomOrder_btn)
        access_card.add_widget(access_box)
        settings_content.add_widget(access_card)

        # Card for password
        pwd_card = MDCard(
            orientation="vertical",
            padding=[dp(16), dp(35), dp(16), dp(10)],  # Augment padding at the top
            spacing=dp(0),  # Remove spacing between elements
            elevation=0,
            radius=dp(5),
            size_hint_y=None,
            height=dp(160),
            md_bg_color=get_color_from_hex("#F4F4F4"),
        )
        
        # Password title
        pwd_title = MDLabel(
            text=self.glossary['ChangePassword'],
            font_style='H6',
            size_hint_y=None,
            height=dp(30),
            font_name='Bagnard',
            theme_text_color="Secondary",
            padding=(0, 0)  # Remove padding from title
        )
        pwd_card.add_widget(pwd_title)
        
        # Password section with validation button
        pwd_box = MDBoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        self.password_field = MDTextField(
            hint_text=self.glossary['ChangePassword'],
            password=True,
            size_hint_x=1,  # Take full width
            font_name='Bagnard',
            mode="rectangle",
            line_color_normal=COLORS['primary'],
        )
        
        pwd_button = self.create_button(
            text=self.glossary['Change'],
            on_press=lambda x: self.change_password(self.password_field.text),
            md_bg_color=COLORS['primary'],
            font_name='Bagnard',
            height=dp(45),
        )
        self.btn_list = [self.dyslexic_btn, self.endOnAllAnswered_btn, self.randomOrder_btn, pwd_button]
        pwd_box.add_widget(self.password_field)
        pwd_box.add_widget(pwd_button)
        pwd_card.add_widget(pwd_box)
        settings_content.add_widget(pwd_card)

        # Add content to ScrollView
        scroll_view.add_widget(settings_content)
        settings_tab.add_widget(scroll_view)

        # Add tabs to layout
        tabs.add_widget(main_tab)
        tabs.add_widget(settings_tab)
        layout.add_widget(tabs)

        # Entrance animation
        self.opacity = 0
        self.add_widget(layout)
        Clock.schedule_once(self.animate_screen, 0.1)
        
        # Apply Bagnard font to all text widgets
        Clock.schedule_once(lambda dt: self.apply_font_to_all_widgets(), 0.2)
    
    def show_language_menu(self, instance):
        # Ensure all menu items use Bagnard font
        for item in self.language_menu.items:
            item['font_name'] = 'Bagnard'
        self.language_menu.open()
    
    def animate_screen(self, dt):
        anim = Animation(opacity=1, duration=0.5)
        anim.start(self)

    def create_button(self, text, on_press, md_bg_color, icon=None, disabled=False, font_name='CustomFont', height=dp(50)):
        button = SafeButton(
            text=text,
            on_press=on_press,
            md_bg_color=md_bg_color,
            size_hint_y=None,
            height=height,
            font_size=dp(16),
            disabled=disabled,
            font_name=font_name,
            elevation=0
        )
        return button

    def update_settings(self):
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'settings.json'), 'r') as f:
            self.app_settings = json.load(f)

    def update_kahiin_settings(self):
        # Load settings from file
        with open(self.kahiin_settings_path, 'r') as f:
            self.settings = json.load(f)

    def get_button_color(self, setting_name):
        self.update_kahiin_settings()
        return (0.2, 0.8, 0.2, 1) if self.settings.get(setting_name, False) else (0.8, 0.2, 0.2, 1)
    
    def get_language_color(self, lang_code):
        self.update_settings()
        return (0.2, 0.8, 0.2, 1) if lang_code == self.app_settings.get('language') else (0.8, 0.2, 0.2, 1)

    def change_language(self, lang_code):
        # Save language in settings
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        old_lang = settings['language']
        settings['language'] = lang_code
        self.current_language = lang_code
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        
        # Load all glossary to be able to access the new language
        with open('glossary.json', 'r') as f:
            all_glossaries = json.load(f)
        
        # Update glossary with selected language
        self.glossary = all_glossaries[lang_code]
        
        # Create message to display change
        message = self.glossary["LanguageChanged"]
        
        # Option 1: Recreate complete interface
        # This approach is the most reliable but can be a bit heavy
        self.clear_widgets()
        self._init_ui()
        
        # Option 2: Update existing interface texts
        # Lighter but potentially less reliable depending on interface complexity
        # self._update_ui_texts()
        
        # Change notification
        toast(message)

    def _update_ui_texts(self):
        """Update all interface texts with current language"""
        # Access tabs
        # Find Tab objects in hierarchy
        for widget in self.walk():
            if isinstance(widget, Tab):
                if hasattr(widget, 'icon') and widget.icon:
                    if "server" in widget.icon.lower():
                        widget.title = self.glossary["ServerTab"]
                    elif "cog" in widget.icon.lower():
                        widget.title = self.glossary["SettingsTab"]
        
        # Main page texts - find widgets directly
        for widget in self.walk():
            if isinstance(widget, MDLabel):
                # Update warning label
                if widget.theme_text_color == "Error" and "[font=MaterialIcons]" in widget.text:
                    widget.text = f"[size={dp(28)}px][font=MaterialIcons]{md_icons['alert-rhombus']}[/font][/size] [size={dp(18)}px]" + self.glossary["KeepAppWake"] + "[/size]"
                # Update IP label
                elif "IP" in widget.text:
                    widget.text = f"IP {self.glossary['Local']}: {get_local_ip()}[color=#CCCCCC]:8080[/color]"
                # Update section titles
                elif widget.text == self.glossary.get("AccessibilitySettings") or "Accessibilité" in widget.text:
                    widget.text = self.glossary["AccessibilitySettings"]
                elif widget.text == self.glossary.get("LanguageTitle") or "Langue" in widget.text:
                    widget.text = self.glossary["LanguageTitle"]
                elif widget.text == self.glossary.get("AboutApp") or "À propos" in widget.text:
                    widget.text = self.glossary["AboutApp"]
                elif widget.text == self.glossary.get("ChangePassword") or "mot de passe" in widget.text.lower():
                    widget.text = self.glossary["ChangePassword"]
        
        # Buttons
        self.start_button.text = self.glossary["StartServer"]
        if self.wakelock_acquired:
            self.wakelock_button.text = self.glossary["DisableWakelock"]
        else:
            self.wakelock_button.text = self.glossary["EnableWakelock"]
        
        # Accessibility buttons
        self.dyslexic_btn.text = self.glossary["DyslexicMode"]
        self.endOnAllAnswered_btn.text = self.glossary["EndOnAllAnswered"]
        self.randomOrder_btn.text = self.glossary["RandomOrder"]
        
        # Password field
        if hasattr(self, 'password_field'):
            self.password_field.hint_text = self.glossary["ChangePassword"]
        
        # Iterate through all buttons to find quit button and change button
        for widget in self.walk():
            if isinstance(widget, SafeButton):
                if widget.text == self.glossary.get("ExitApp") or "quitt" in widget.text.lower():
                    widget.text = self.glossary["ExitApp"]
                elif widget.text == self.glossary.get("Change") or "chang" in widget.text.lower():
                    widget.text = self.glossary["Change"]

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
            logging.info("Default Android service used.")
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
        self.wakelock_button.disabled = False
        self.wakelock_button.md_color = (0.8, 0.2, 0.2, 1)

    def stop_flask_server(self):
        if self.flask_thread:
            # Code to stop Flask server if necessary
            logging.info("Flask server stopped")

    if platform == 'android':
        @run_on_ui_thread
        def request_ignore_battery_optimizations(self):
            # If the battery settings are already set don't do anything
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
            logging.info("Battery optimization settings opened.")

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
                self.wakelock_button.text = self.glossary["DisableWakelock"]
                toast(self.glossary["WakelockEnabled"])
            except Exception as e:
                print(f"Error when activating wakelock: {e}")
        else:
            toast(self.glossary["WakelockNotSupported"])

    def release_wakelock(self):
        if self.wakelock_acquired and self.wakelock is not None:
            self.wakelock.release()
            self.wakelock_acquired = False
            self.wakelock_button.text = self.glossary["EnableWakelock"]
            toast(self.glossary["WakelockDisabled"])

    # Create a function to apply text style to all widgets
    def apply_font_to_all_widgets(self):
        """Apply Bagnard font to all text widgets"""
        for widget in self.walk():
            if hasattr(widget, 'font_name'):
                widget.font_name = 'Bagnard'
            # For specific widgets with title properties
            if hasattr(widget, 'title') and isinstance(widget, MDTopAppBar):
                for child in widget.walk():
                    if hasattr(child, 'font_name'):
                        child.font_name = 'Bagnard'
            # For MDDropdownMenu items that will be created dynamically
            if isinstance(widget, MDDropdownMenu):
                for item in widget.items:
                    if 'font_name' not in item:
                        item['font_name'] = 'Bagnard'
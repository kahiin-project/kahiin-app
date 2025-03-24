from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.animation import Animation

class Tab(MDFloatLayout, MDTabsBase):
    """Enhanced Tab class with animation and modern style"""
    content = ObjectProperty(None)
    icon = StringProperty("")
    
    def on_kv_post(self, base_widget):
        self.opacity = 0
        self.padding = [dp(15), dp(10)]
        
        # Allow text to display on multiple lines
        self.tab_label.markup = True
        self.tab_label.text_size = (None, None)
        self.tab_label.halign = 'center'
        self.tab_label.line_height = 1.2
        
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self)
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.animation import Animation

class Tab(MDFloatLayout, MDTabsBase):
    """Classe Tab améliorée avec animation et style moderne"""
    content = ObjectProperty(None)
    icon = StringProperty("")
    
    def on_kv_post(self, base_widget):
        self.opacity = 0
        self.padding = [dp(15), dp(10)]
        
        # Permettre au texte de s'afficher sur plusieurs lignes
        self.tab_label.markup = True
        self.tab_label.text_size = (None, None)
        self.tab_label.halign = 'center'
        self.tab_label.line_height = 1.2
        
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self)
import traceback
import logging
from kivymd.uix.button import MDRaisedButton
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty

class SafeButton(MDRaisedButton):
    ripple_scale = NumericProperty(2.75)
    md_bg_color_down = ListProperty([0, 0, 0, 0])
    
    def __init__(self, **kwargs):
        super(SafeButton, self).__init__(**kwargs)
        self.radius = [dp(15), ]
        self.elevation = 0
        self.shadow_softness = 0
        self.shadow_offset = (0, 0)
        self._original_color = None
        
        # Permettre aux boutons de prendre toute la largeur
        self.size_hint_x = 1
        
        # Permettre au texte de s'afficher sur plusieurs lignes
        self.halign = 'center'
        self.line_height = 1.2
        self.allow_stretch = True
        self.text_size = (None, None)
        self.shorten = False
        self.markup = True
        
    def on_press(self):
        if self._original_color is None:
            self._original_color = self.md_bg_color.copy()
        
        # Effet d'animation quand on appuie (sans ombre)
        darker_color = [max(c * 0.85, 0) for c in self.md_bg_color[:3]] + [self.md_bg_color[3]]
        anim = Animation(md_bg_color=darker_color, duration=0.1)
        anim.start(self)
        
    def on_release(self):
        # Restauration après appui
        if self._original_color:
            anim = Animation(md_bg_color=self._original_color, duration=0.1)
            anim.start(self)
    
    def on_touch_down(self, touch):
        try:
            return super(SafeButton, self).on_touch_down(touch)
        except Exception as e:
            logging.error(f"Touch event error: {e}")
            traceback.print_exc()
            return False
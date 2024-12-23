import traceback
import logging
from kivymd.uix.button import MDRaisedButton

class SafeButton(MDRaisedButton):
    def on_touch_down(self, touch):
        try:
            return super(SafeButton, self).on_touch_down(touch)
        except Exception as e:
            logging.error(f"Touch event error: {e}")
            traceback.print_exc()
            return False
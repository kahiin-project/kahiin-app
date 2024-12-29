from kivy.config import Config
from kivy.core.text import LabelBase
import logging
import os
import sys

Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# Set the current directory to the one containing this file
# os.chdir(os.path.dirname(os.path.abspath(__file__)))
LabelBase.register(name='MaterialIcons', fn_regular='src/MaterialDesignIcons.ttf')
LabelBase.register(name='Bagnard', fn_regular='kahiin/web/static/font/Bagnard.otf')

# Logging setup
logging.basicConfig(level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_log.txt', mode='w')
    ])
import json
import os

def get_app_settings():
    with open('settings.json', 'r') as f:
        return json.load(f)

def get_kahiin_settings():
    with open(os.path.join('kahiin', 'settings.json'), 'r') as f:
        return json.load(f)

def get_app_glossary():
    with open('glossary.json', 'r') as f:
        return json.load(f)[get_app_settings().get('language')]
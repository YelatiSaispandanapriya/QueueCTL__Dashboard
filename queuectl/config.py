# config.py
from db import get_config, set_config

def set_config_cli(key, value):
    set_config(key, str(value))

def get_all_configs():
    return {
        'retry_base': float(get_config('retry_base', '2')),
        'default_max_retries': int(get_config('default_max_retries', '3'))
    }

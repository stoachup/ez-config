#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Christophe Druet'
__copyright__ = 'Copyright (c) 2016-, Stoachup SRL - All rights reserved'
__credits__ = ['Christophe Druet']
__license__ = 'Proprietary'
__version__ = '0.1.1'
__maintainer__ = 'Christophe Druet'
__email__ = 'christophe.druet@stoachup.com'
__status__ = 'Production'

import os
import re
from typing import List, Dict, Any, Literal
from benedict import benedict

from loguru import logger


DEFAULT_FORMAT = 'toml'
DEFAULT_CONFIG = benedict()
VALIDATORS = {}


def extend_default_config(config: dict):
    """
    Merges the input configuration dictionary with the DEFAULT_CONFIG using benedict.

    :param config: A dictionary containing configuration settings to be merged.
    """
    DEFAULT_CONFIG.merge(benedict(config))


def extend_default_validators(config: dict):
    """
    Add validators for different parts of the configuration.

    :param config: The configuration dictionary containing parts to validate.
    :type config: dict

    :return: None
    :rtype: None
    """
    for part in config.keys():
        def valid(conf: benedict) -> bool:
            return (f'{part}' in conf.keys() and 
                    set(config[f'{part}'].keys()) == set(conf.get(f'{part}', default={}).keys()))

        VALIDATORS[part] = valid


extend_default_config({ 'config': { 'file': 'config', 'directory': './conf' } })
extend_default_validators(DEFAULT_CONFIG)


class BaseConfig:
    """Initialize, load, update, and manage configuration settings.

    :param name: The name of the configuration.
    :type name: str
    :param default_conf: The default configuration settings.
    :type default_conf: Dict[str, Any] | benedict
    :param config_dir: The directory path for configuration files.
    :type config_dir: str

    :raises AttributeError: If the default configuration is not a dict or benedict.

    Methods:
        - load(files: List[str] | None = None): Initialize config using elements locally stored and default values.
        - reload(): Alias for load.
        - reset(): Reset configuration settings.
        - update(files: List[str] | None = None): Update configuration settings.
        - get(*args, **kwargs): Retrieve configuration settings.
        - find: Alias for get.
        - set(*args): Set configuration values.
        - save(files: List[str] | None = None, mode='asis'): Save configuration files.
        - __getitem__(key): Get an item from the configuration.
        - __setitem__(key, value): Set an item in the configuration.
        - __delitem__(key): Delete an item from the configuration.
        - __iter__(): Iterate over the configuration.
        - __len__(): Get the length of the configuration.
    """
    def __init__(self, 
                 name: str = 'configuration', 
                 default_conf: Dict[str, Any] | benedict = DEFAULT_CONFIG,
                 config_dir: str = None):
        self.name = name

        if not isinstance(default_conf, benedict) and not isinstance(default_conf, dict):
            raise AttributeError('Default config must be dict or benedict.')
        
        self.defaults = benedict(default_conf)

        cfg_dir = config_dir or self.defaults.find(['config.directory'], default='./conf')
        self.config_dir = os.path.normpath(os.path.join(os.getcwd(), cfg_dir))
        if not os.path.exists(self.config_dir):
            logger.warning(f'Configuration folder "{cfg_dir}" does not exist')
            os.makedirs(self.config_dir)
            logger.success(f'Configuration folder "{cfg_dir}" created')

        self.store = benedict()

        self.load()

        self.generate_dynamic_find_methods()

    def load(self, files: List[str] | None = None):
        # Initialize config using default values
        self.store = benedict()

        self.update(files or self.defaults.find(['config.sections'], default=[]))

        return self

    reload = load

    def reset(self):
        sections = self.defaults.find(['config.sections'], default=[])
        deletion = { s: False for s in sections }
        for s in [ s for s in os.listdir(self.config_dir) if s in [ f'{s}.toml' for s in sections ] ]:
            if (input(f'{s} already exists. Are you sure that you want to delete it? Y/[N] ') or 'N') == 'Y':
                os.remove(os.path.join(self.config_dir, s))
            else:
                deletion[f] = False
        
        if not all(list(deletion.values())):
            self.reload()
            logger.debug('Configuration has been partly deleted')
        else:
            self.store = benedict()
            logger.success('Configuration has been fully deleted')

        return self

    def update(self, sections: List[str] | None = None):
        sections = sections or self.defaults.find(['config.sections'], default=[])
        # Finding configuration files in config folder
        if config_files := [ f for f in os.listdir(self.config_dir) if re.search(fr'^({"|".join(sections)})\.toml$', f) ]:
            # Merging config files with defaults
            self.store.merge(*[ benedict.from_toml(os.path.join(self.config_dir, f)) for f in config_files ])

        return self

    def get(self, *args, **kwargs):
        if len(args) == 0:
            return self.store

        keypath = args[0] if len(args) == 1 else '.'.join(args)

        default = kwargs.get('default', self.defaults.find([keypath], default=None))

        return self.store.find([keypath], default=default)

    find = get

    def generate_dynamic_find_methods(self):
        def create_method(method_name):
            def method(self, *args, **kwargs):
                return self.find(method_name, *args, **kwargs)
            return method

        for method_name in self.defaults.find(['config.sections'], default=list(self.defaults.keys())):
            generated_method = create_method(method_name)
            setattr(self.__class__, method_name, generated_method)

    def set(self, *args):
        if len(args) < 2:
            raise RuntimeError('Setting config value requires at least 2 arguments (key, value)')

        keypath = args[0] if len(args) == 2 else '.'.join(args[:-1])
        value = args[-1]

        self.store[keypath] = value

        return self

    def save(self, 
             sections: List[str] | None = None, 
             mode: Literal['asis', 'full', 'delta'] = 'asis'):
        """ Saving the configuration files """
        sections = sections or self.defaults.find(['config.sections'], default=[])

        data = benedict()
        if mode == 'full':
            data.merge(self.defaults.clone())

        data.merge(self.store.clone())

        if mode == 'delta':
            fdata = data.flatten(separator='$$')
            data = benedict()
            fdefault = self.defaults.flatten(separator='$$')
            for k in fdata.keypaths():
                if k not in fdefault:
                    logger.debug(f'{k} not in defaults')
                    data[k.replace('$$', '.')] = fdata[k]
                elif fdata[k] != fdefault[k]:
                    logger.debug(f'{fdata[k]} != {fdefault[k]}')
                    data[k.replace('$$', '.')] = fdata[k]

        stored = 0
        if data:
            for section in sections:
                path = os.path.join(self.config_dir, f'{section}.toml')
                if section in data:
                    data.subset(section).to_toml(filepath=path)
                    stored += 1
                    logger.debug(f'Configuration "{section}" successfully stored')
                elif mode == 'delta' and os.path.exists(path):
                    os.remove(path)

        return stored

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)
    
    def __len__(self):
        return len(self.store)
    
    def __str__(self):
        return str(self.store)

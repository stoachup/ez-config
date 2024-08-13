# Easy config

Simple class to manage configurations.

## Installation

Classic through pip or your favourite package manager:

```shell
pip install ez-config-mgt
```

## Usage

You want to define a default configuration and allow users to override some of the settings. 
The class simply get the config value for the user's specific config and get the default value if not defined.

First thing is to instantiate a configuration. 

```python
from ez_config_mgt import BaseConfig

config = BaseConfig('test')

print(config)
```

'test' is the name of the configuration. You can define several configurations.

You can tailor the default configuration to your needs.

```python
from ez_config_mgt import BaseConfig, extend_default_config

extend_default_config({'mydefaults': { 'example': 'test' }})

config = BaseConfig('test')

print(config)
```

Class is meant to be inherited. It's quite useful if you just need one config and prefer not to bother passing arguments in your main code.

```python
from ez_config_mgt import BaseConfig

class MyToolConfig(BaseConfig):
    def __init__(self):
        super().__init__('mytool', default_conf = { 
            'config': { 'file': 'config', 'directory': './conf' }, 
            'mydefaults': { 'example': 'test' }})

config = MyToolConfig()

print(config)
```

Alternatively, you can first extend the default config. It's rather convenient if your package is made of multiple parts, each of them having its own configuration needs that you want to deal with in one single config.

```python
from ez_config_mgt import BaseConfig, extend_default_config

extend_default_config({'mydefaults': { 'example': 'test' }})

class MyToolConfig(BaseConfig):
    def __init__(self):
        super().__init__('mytool')

config = MyToolConfig()

print(config)
```

## Acknowledgements

This is quite simple stuff that was written to speed up config management for internal needs. It's published to be criticized, of course, but mainly to make reuse and deployment easier.
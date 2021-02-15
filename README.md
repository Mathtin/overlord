# Overlord

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Discord Manager Bot

## Features

Bot frontend functionality represented by extensions:

  - Utility
  - Config
  - Ranking
  - Invite
  - Stats

Each extension provides a set of commands and background tasks useful for managing your discord guild as well as discord bot itself. Every extension has own help page containing brief description and command usage provided by this extension.

### Usage

Install the dependencies via pip

```sh
$ python3 -m pip install -r requirements.txt
```

Create .env file  

```sh
$ cp .env.template .env
$ nano .env
```

Create configuration file  

```sh
$ cp overlord_example.cfg overlord.cfg
$ nano overlord.cfg
```

Start app

```sh
$ python3 src/main.py
```

### Docker

in development...

### Development

Issues and pull requests are highly welcomed!

# Author

Copyright (c) 2020 Daniel [Mathtin](https://github.com/Mathtin/) Shiko
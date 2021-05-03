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

Clone repository

```sh
git clone https://github.com/Mathtin/overlord.git
cd overlord
```

Install the dependencies via pip

```sh
python3 -m pip install -r requirements.txt
```

Create .env file  

```sh
cp .env.template .env
nano .env
```

Create configuration file  

```sh
cp overlord_example.cfg overlord.cfg
nano overlord.cfg
```

Start app

```sh
python3 src/main.py
```

### Docker

Pull latest image from hub

```sh
docker pull mathtin/overlord:latest
```

Create env and configuration files

```sh
wget -O overlord.env https://raw.githubusercontent.com/Mathtin/overlord/master/.env.template
nano overlord.env
wget -O overlord.cfg https://raw.githubusercontent.com/Mathtin/overlord/master/overlord_example.cfg
nano overlord.cfg
```

Run container (attach to network where your db is reachable)

```sh
docker run -d --name overlord-bot \ 
           -e $(pwd)/overlord.env \
           -v $(pwd)/overlord.cfg:/app/overlord.cfg \
           --network=multi-host-network \
           mathtin/overlord:latest
```

Or you can use docker compose (postgres+overlord) using files from repository

```sh
wget https://raw.githubusercontent.com/Mathtin/overlord/master/docker-compose.yml
mkdir scripts && wget -P scripts https://raw.githubusercontent.com/Mathtin/overlord/master/scripts/01_users.sql
wget https://raw.githubusercontent.com/Mathtin/overlord/master/database.env
```

Set password in database.env

Note: `DATABASE_ACCESS_URL=postgresql+asyncpg://root:PASTE_PASSWORD_HERE@postgres_container/overlord`

### Development

Issues and pull requests are highly welcomed!

# Author

Copyright (c) 2020 Daniel [Mathtin](https://github.com/Mathtin/) Shiko

### Contributors

 - Danila [DeadBlasoul](https://github.com/DeadBlasoul/) Popov
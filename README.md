# MyDic

MyDic, your personal language companion.

## INSTALLATION

Add a new user and prepare app dirs:
```sh
sudo useradd -r -d /opt/mydic -s /usr/sbin/nologin mydic

sudo mkdir -p /opt/mydic
cd /opt/mydic

sudo mkdir -p data/db data/lt data/tts/cache
sudo mkdir -p data/tts/piper/voices
sudo mkdir -p data/tts/kokoro/.cache data/tts/kokoro/models

sudo chown -R mydic:mydic data/db data/lt data/tts
```

Optional, but desirable step for running some maintenance scripts without `sudo`:
```sh
sudo usermod -aG mydic {YOURUSER}
```

Deploy package:
```sh
wget -qO - https://github.com/WiseToad/mydic/releases/latest/download/mydic.tar.gz \
| sudo tar -xzf -

sudo chgrp mydic scripts/piper-voices.py scripts/users.sh
```

Configure:
```sh
sudo cp .env.sample .env
```
Edit all TODOs in `.env` file.

Start services:
```sh
docker compose up -d
```

At first startip, it takes some time to build backend and download models.

### Nginx Configuration

Setup reverse proxy with WebSocket support:
```nginx
...
client_max_body_size 10M;

location / {
    proxy_pass http://localhost:8080; # from FRONTEND_EXPOSE in app's .env

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
...
```

### Application Users

If self-registration is disabled (see `REGISTRATION_ENABLED` variable in `.env` file), then add users by hand:

```sh
/opt/mydic/scripts/users.sh add USER [--password PASS]
```

### Piper TTS Voices

Download voices for piper TTS:  
```sh
# For help, run: scripts/piper-voices.py [COMMAND] -h
# or, see the description at the top of scripts/piper-voices.py file
cd /opt/mydic
sudo -u mydic -g mydic scripts/piper-voices.py list --update
sudo -u mydic -g mydic scripts/piper-voices.py download --langs LANG ... [--type {all,medium,high}]
```
sudo options -u and -g are required for file ownership consistency within `data` directory

### TTS Encoder Service

Install background TTS encoder systemd service:
```sh
cd /etc/systemd/system
sudo ln -s /opt/mydic/systemd/encode-tts.service
sudo ln -s /opt/mydic/systemd/encode-tts.timer

sudo systemctl daemon-reload
sudo systemctl enable encode-tts.timer --now

# Inspect job status and logs:
sudo systemctl status encode-tts
sudo journalctl -u encode-tts
```

## UPGRADE

In order to upgrade to a new version, do the following.

Stop services:
```sh
cd /opt/mydic
docker compose down
```

Then:
- deploy package as described in installation instructions above
- apply migration instructions, if any
- start services, as described above

Below there are some common instructions for actions that need to be done depending on changes been made in update.

### Backend

In order to rebuild backend container after source has been updated, do:
```sh
cd /opt/mydic
docker compose build
```

### Systemd Services

If systemd unit files was changed, do:

```sh
sudo systemctl daemon-reload
```

## DEVELOPMENT

### Project Setup

```sh
cp .env.dev-sample .env
cp compose.yaml.dev-sample compose.yaml
```

Edit all TODOs in `.env` file. The `compose.yaml` file typically doesn't require changes.

```sh
docker compose up -d
```

Download Piper TTS voices, if needed, as described above in installation instructions.

Follow setup instructions from README in `backend` and `frontend` subdirs.

### Startup and Usage

Follow startup and usage instructions from README in `backend` and `frontend` subdirs.  
Starting backend and frontend in separate consoles will cleanly provide their logs in runtime.

## RELEASE

First, do not forget to change version number in `VERSION.txt` file before release!

Then, in order to build release package, do:
```sh
./build.sh
```

Target archive is in `build` subdir.

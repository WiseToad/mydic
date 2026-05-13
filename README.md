# MyDic

MyDic, your personal language companion.


## INSTALLATION AND USAGE

Add a new user and prepare app dirs:
```sh
sudo useradd -r -d /opt/mydic -s /usr/sbin/nologin mydic

sudo mkdir -p /opt/mydic
cd /opt/mydic

sudo mkdir -p data/db data/lt data/tts/cache data/tts/piper/voices data/tts/kokoro/cache data/tts/kokoro/models
sudo chown -R mydic:mydic data/db data/lt data/tts
```

Obtain and deploy package:
```sh
wget -q -O - https://github.com/WiseToad/mydic/releases/latest/download/mydic.tar.gz | sudo tar -xzf -

sudo chgrp mydic scripts/piper-voices.py
```

Configure:
```sh
sudo cp .env.sample .env
```
Edit all TODOs in `.env` file.

Start:
```sh
docker compose up -d
```

Download voices for piper TTS:  
_(sudo with -u and -g options is needed for file ownership consistency within data directory)_
```sh
# for help, run: scripts/piper-voices.py [COMMAND] -h
# or, see the descriptin at the top of scripts/piper-voices.py file
sudo -u mydic -g mydic scripts/piper-voices.py list --update
sudo -u mydic -g mydic scripts/piper-voices.py download --langs LANG ... [--type {all,medium,high}]
```

Add users:
```sh
docker exec -it mydic-backend /app/users.py add USER [--password PASS]
```

Setup background TTS encoder worker:

==TODO==

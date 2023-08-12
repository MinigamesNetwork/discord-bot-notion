FROM		python:3.11-alpine

LABEL       author="shoker137"

RUN			apk add git
RUN			adduser container -D -h /home/container
RUN         chown -R container:container /home/container
RUN         chmod -R 766 /home/container
RUN			python -m ensurepip
RUN			python -m pip install pipenv

ENV         USER=container HOME=/home/container
ENV         LANG=en_US.UTF-8
ENV         LANGUAGE=en_US.UTF-8

WORKDIR     /home/container

CMD			rm -rf discord-bot-notion && git clone https://github.com/MinigamesNetwork/discord-bot-notion && cp -rf .env discord-bot-notion/.env && cd discord-bot-notion && pipenv install && pipenv run python discord_bot.py
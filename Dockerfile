FROM alpine:latest

ARG USER=octoprint

RUN adduser --disabled-password "$USER"

RUN apk update && apk upgrade && apk add --update --no-cache python3 py3-pip git py3-virtualenv py3-wheel python3-dev musl-dev linux-headers gcc g++ 	libffi-dev
RUN git clone https://github.com/OctoPrint/OctoPrint

WORKDIR /OctoPrint

RUN pip install -e .[develop,plugins] argh

COPY ./OctoPrint-Printer_poweroff /OctoPrint-Printer_poweroff

WORKDIR /OctoPrint-Printer_poweroff

RUN octoprint dev plugin:install

WORKDIR /OctoPrint

USER "$USER"
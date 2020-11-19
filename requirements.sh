#!/bin/bash
RED='\033[0;31m'
NC='\033[0m' # No Color

red() {
    if [[ -z $1 ]]; then
        return;
    fi
    echo -e "\n\n${RED}$1:$NC"
}

inst() {
    if [[ -z $1 ]]; then
        return;
    fi
    red $1
    sudo apt install -y $1
}

red "Update du apt-get"
sudo apt-get update -y
red "Upgrade du apt-get"
sudo apt-get upgrade -y

inst python

red "pip install discord"
sudo pip3 install discord
red "pip install requests"
sudo pip3 install requests
red "pip install Pillow"
sudo pip3 install Pillow
red "pip install numpy"
sudo pip3 install numpy

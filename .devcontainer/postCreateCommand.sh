#!/bin/bash

ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys
ssh-keygen -f /home/vscode/.ssh/known_hosts -R "[localhost]:2222" || true
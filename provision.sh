#!/bin/bash

yum install -y python-devel
pip install virtualenv

echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

source /etc/profile.d/local_bin.sh

gem install --no-ri --no-rdoc puppet

puppet module install garethr-erlang

puppet apply /home/vagrant/srv/register-publisher/manifests/erlang.pp

puppet module install puppetlabs-rabbitmq

puppet apply /home/vagrant/srv/register-publisher/manifests/rabbit.pp

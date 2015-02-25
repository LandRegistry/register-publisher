yum makecache fast
yum check-update
yum install -y python-devel

echo "export PATH=$PATH:/usr/local/bin" > /etc/profile.d/local_bin.sh

echo "export SETTINGS=config.DevelopmentConfig" >> /home/vagrant/.bashrc

source /etc/profile.d/local_bin.sh

#------------install puppet
gem install --no-ri --no-rdoc puppet

#------------Install erlang runtime and rabbitmq
puppet module install garethr-erlang

puppet apply /vagrant/manifests/erlang.pp

puppet module install puppetlabs-rabbitmq

puppet apply /vagrant/manifests/rabbit.pp



cd /vagrant

source install.sh

gem install --no-ri --no-rdoc foreman

yum check-update
yum makecache fast
yum install -y python-devel

cd /vagrant

source install.sh

gem install --no-ri --no-rdoc foreman

# Register publisher
Beta version of the "Register Publisher".

This service will forward messages from the "System of Record" queue to the "feeder" queue.

* Using the Advanced Message Queuing Protocol (AMQP).
* Messages are received via the default 'direct' exchange.
* They are forwarded to the default 'fanout' exchange - which permits multiple clients.
* A 'direct' type of output exchange should also be possible but may have to be explicitly set.

See the [wiki](https://github.com/LandRegistry/register-publisher/wiki) for design notes, etc.


##dependencies:

- See 'requirements.txt'; in particular, additions for 'kombu' and 'stopit'.
- An AMQP broker is required, typically "RabbitMQ".


##how to run in development

N.B.: for a Windows host m/c:

    git config --global core.autocrlf false

Then use 'Git Bash' console.

Also, for 'vagrant' operation, ensure that "VBoxHeadless.exe" is added to the firewall rules ('private').

```
vagrant up
vagrant ssh
```
Supervisord has been configured to launch this application on start up, but if you want to stop Supervisord running it and run it yourself then:

```
sudo supervisorctl stop register-publisher
./run.sh
```

##how to run tests
In virtual machine ('vagrant'):
* use IP address of host m/c (for Windows, at least).
* in that case the RabbitMQ 'guest' account may not be sufficient.

if executing tests directly on host:
* 'localhost' will be required
* default RabbitMQ 'guest' account will suffice.

```
./test.sh
```

##How to manage rabbitmq:
Status of the server

```
service rabbitmq-server status
```

Stop the server

```
service rabbitmq-server stop
```

Start the server

```
service rabbitmq-server start
```


Dependencies

Redis
Install Redis

brew install redis

Start Redis

redis-sever

This application requires the following environment variables

SETTINGS
REDIS_QUEUE_KEY
REDIS_HOST
SETTINGS
REDIS_QUEUE_KEY
REDIS_URL
PUBLIC_SEARCH_API_URL
PUBLIC_SEARCH_API_ENDPOINT
GEO_API_URL
GEO_API_ENDPOINT
AUTHENTICATED_SEARCH_API_URL
AUTHENTICATED_SEARCH_API_ENDPOINT

local development example:

export SETTINGS='DEVELOPMENT'
export REDIS_QUEUE_KEY='titles_queue'
export REDIS_URL='localhost'
export PUBLIC_SEARCH_API_URL='http://localhost:8003'
export PUBLIC_SEARCH_API_ENDPOINT='/load/public_titles'
export AUTHENTICATED_SEARCH_API_URL='http://localhost:8003'
export AUTHENTICATED_SEARCH_API_ENDPOINT='/load/authenticated_titles'
export GEO_API_URL='http://localhost:8003'
export GEO_API_ENDPOINT='/titles/<title_number>'
export REDIS_QUEUE_KEY='titles_queue'
export REDIS_HOST='redis://user:@localhost:6379'

Run the application

foreman start

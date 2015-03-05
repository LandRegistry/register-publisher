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
- "RabbitMQ", an AMQP broker.
-  A suitable non-guest account for the above, when using more than one machine (even a virtual one).

##environment

This application refers to the following environment variables:


|Name                | Default 'Config' Value                     |Mandatory?|
| ------------- |-------------| -----|
|SETTINGS            |"config.DevelopmentConfig"                  |YES|
|LOG_THRESHOLD_LEVEL |ERROR                                       |NO|
|RP_HOSTNAME         |"amqp://guest:guest@localhost:5672//"       |NO|
|INCOMING_QUEUE      |"INCOMING_QUEUE"                            |NO|
|OUTGOING_QUEUE      |"OUTGOING_QUEUE"                            |NO|


N.B.:  
Even though some of the environment variables are not required, the corresponding 'config' values _will_ be set.  
In particular, the default 'RP_HOSTNAME' value is for development purposes only and the e.v. should be set as appropriate.


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

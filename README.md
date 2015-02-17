# Register publisher
Beta version of the register publisher

This service will forward messages from the land register queue to the feeder queue.

At the moment this repo contains the mint code, as a starting point to write the new service within its own 
virtual machine.

##dependencies:
- tba,

##how to run in development

N.B.: for a Windows host m/c:

    git config --global core.autocrlf false

Then use 'Git Bash' console.

```
vagrant up
```

```
vagrant ssh
```

```
cd /vagrant
```

```
./run.sh -d
```

To the run this in production use the following command

```
./run.sh
```

##how to run tests
In virtual machine

```
./test.sh
```

# mint
Beta version of the register publisher

Currently this service forwards messages from the land register queue
to the feeder queue.

##dependencies:
- tba

##how to run in development

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

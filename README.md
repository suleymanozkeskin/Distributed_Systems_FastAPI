# Implementing raft in python

This is a python implementation of the raft consensus algorithm. It tries to replicate the incoming data within a cluster of nodes. If leader fails, a new leader is elected and remaining follower nodes should replicate the data from the new leader. Currently, the implementation is not complete and is still a work in progress.

## Designing data intensive applications

This application is built to test the raft consensus algorithm. It is not a production ready application. It is built to test the raft consensus algorithm and to display how it works. Several nodes are built within local machine to simulate multiple databases that exists in a cloud environment.

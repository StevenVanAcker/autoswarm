Docker swarm does docker container orchestration well. Unfortunately,
it does not automatically join new nodes.

These scripts will automatically join docker swarm nodes into a cluster.
New docker swarm nodes advertise their existence on a specific SQS queue to
which the swam master listens. Upon receiving a message, the swarm master
sends back the docker swarm join token to the swarm node.


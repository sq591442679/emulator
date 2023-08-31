#!/bin/bash

# echo "arguments: $@"
# echo "number of args: $#"

vtysh

echo "
interface $1
    ip ospf network point-to-point
    ip ospf area 0.0.0.0
    ip ospf hello-interval 1
    ip ospf dead-interval 4
    ip ospf retransmit-interval 2
    ip ospf cost $3

" >> /etc/frr/frr.conf

# echo "$1 configured"

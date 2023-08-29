#!/bin/bash

# echo "arguments: $@"
# echo "number of args: $#"

vtysh

echo "configure terminal
    interface $1
    ip ospf network point-to-point
    ip ospf area 0.0.0.0
    ip ospf hello-interval 1
    ip ospf cost $3
    exit
    exit
    exit
" | vtysh

# echo "$1 configured"

#!/bin/bash

# router_id=$1

systemctl start frr

vtysh

echo "configure terminal
    router ospf
    ospf router-id $1
    exit
    exit
" | vtysh

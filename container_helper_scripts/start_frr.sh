#!/bin/bash

# router_id=$1

echo "
net.ipv4.conf.eth1.rp_filter = 0
net.ipv4.conf.eth2.rp_filter = 0
net.ipv4.conf.eth3.rp_filter = 0
net.ipv4.conf.eth4.rp_filter = 0
" >> /etc/sysctl.conf

sysctl -p

sleep 2

systemctl start frr

sleep 10

vtysh

echo "
configure terminal
router ospf
ospf router-id $1
exit
exit
" | vtysh



#!/bin/bash

# $1: router id
# $2: 

echo "
net.ipv4.conf.eth1.rp_filter = 0
net.ipv4.conf.eth2.rp_filter = 0
net.ipv4.conf.eth3.rp_filter = 0
net.ipv4.conf.eth4.rp_filter = 0
" >> /etc/sysctl.conf

sysctl -p

sleep 2

echo "
router ospf
    ospf router-id $1

" >> /etc/frr/frr.conf

systemctl start frr

sleep 5

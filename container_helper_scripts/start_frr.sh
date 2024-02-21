#!/bin/bash

# $1: router id
# $2: lofi n

echo "
net.ipv4.conf.eth1.rp_filter = 0
net.ipv4.conf.eth2.rp_filter = 0
net.ipv4.conf.eth3.rp_filter = 0
net.ipv4.conf.eth4.rp_filter = 0
" >> /etc/sysctl.conf

sysctl -p

sleep 2

if ["$2" -lt 0]; then
    echo "
    router ospf
        ospf router-id $1

    " >> /etc/frr/frr.conf
else
    echo "
    router ospf
        ospf router-id $1
        ospf lofi $2

    " >> /etc/frr/frr.conf
fi

systemctl start frr

sleep 5

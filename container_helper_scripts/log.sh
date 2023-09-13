#!/bin/bash

touch /var/log/frr/sqsq_ospfd.log

echo "
log file /var/log/frr/sqsq_ospfd.log debugging
" >> /etc/frr/frr.conf


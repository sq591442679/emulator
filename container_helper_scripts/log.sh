#!/bin/bash

# touch /var/log/frr/sqsq_ospfd.log
# chomd 777 /var/log/frr/sqsq_ospfd.log

echo "
log file /var/log/frr/sqsq_ospfd.log
" >> /etc/frr/frr.conf


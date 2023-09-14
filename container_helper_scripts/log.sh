#!/bin/bash

# touch /var/log/frr/sqsq_ospfd.log
# chomd 777 /var/log/frr/sqsq_ospfd.log
# NOTE do not new the log file because frr does it automatically
# NOTE it seems frr can only write logs to /var/log/frr/

echo "
log file /var/log/frr/sqsq_ospfd.log
log record-priority
" >> /etc/frr/frr.conf


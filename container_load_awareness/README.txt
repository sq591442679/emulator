in this folder,
load_awareness.c uses libpcap to capture data packets, and libnl to send netlink messages.
when captures enough packets, it queries the forwarding queue occupation, 
and change the ospf cost configuration in FRRouting if needed.

compile load_awareness.c: gcc load_awareness.c -o sample `pkg-config --cflags --libs libnl-3.0 libnl-route-3.0 libpcap`
#include <netlink/socket.h>
#include <netlink/netlink.h>
#include <netlink/msg.h>
#include <netlink/route/link.h>
#include <netlink/route/tc.h>
#include <netlink/route/qdisc.h>
#include <netlink/utils.h>
#include <netlink/cache.h>
#include <unistd.h>
#include <stdio.h>
#include <math.h>

#define NETLINK_RECV_PACKET	30
#define LOAD_AWARENESS_PID	258258
#define ARRAY_SIZE          4
#define BANDWIDTH           10000000
#define PACKET_SIZE         (1024 * 8)
#define MAX_COST            65535

const char interface_name[4][5] = {"eth1", "eth2", "eth3", "eth4"};
int transmission_cost[5] = {0};     // transmission_cost[0] is the init cost of eth1
int enable_load_awareness = 0;
int forwarding_queue_capacity = 0;  // unit: packet
double delta;
char command[120];
u_int32_t qlen_amplitude_threshold;       // send delta * forwarding_queue_capacity to kernel through netlink messages

/**
 * calculate queuing delay based on bandwidth, avg packet size and qlen
 * bandwidth: bps
 * packet_size: bits
 * return: caculated queuing delay, unit: ms
 */
double estimate_queuing_delay(int bandwidth, int packet_size, int qlen)
{
    return (double)packet_size * (double)qlen / (double)bandwidth * 1000.0;
}

/**
 * change the delay to ospf cost
 * delay: ms
 */
int delay_to_cost(double delay)
{
    return round(delay * 10.0);
}

static int nl_recv_message(struct nl_msg *msg, void *arg) {
    struct nlmsghdr *nlh = nlmsg_hdr(msg);
    int *array_data;
    int ret;

    if (nlh->nlmsg_len < NLMSG_HDRLEN + ARRAY_SIZE * sizeof(int)) {
        printf("Invalid message length\n");
        return -1;
    }

    array_data = (int *)NLMSG_DATA(nlh);

    // printf("Received an int array from netlink message:\n");
    for (int i = 0; i < ARRAY_SIZE; ++i) {
        // printf("cnt:%d Array[%d]: %d\n", recv_cnt, i, array_data[i]);
        // printf("last_time_qlen[%d]:%d  array_data[%d]:%d\n", i, last_time_qlen[i], i, array_data[i]);    
        
        if (enable_load_awareness) {
            if (array_data[i] != -1) {  // array_data == -1 means this interface is down
                // should change spf cost and flood
                double queuing_delay = estimate_queuing_delay(BANDWIDTH, PACKET_SIZE, array_data[i]);
                int new_cost = transmission_cost[i] + delay_to_cost(queuing_delay);
                
                snprintf(command, sizeof(command), "/container_load_awareness/change_ospf_cost.sh %s %d\n", interface_name[i], new_cost);
                // printf(command);
                
                ret = system(command);
                if (ret != 0) {
                    perror("command failed\n");
                    return -1;
                }      
            }
        }
    }

    return 0;
}

/**
 * argv[1]: bool    whether enable load awareness
 * argv[2]: double  parameter delta in LoFi
 * argv[3]: int     forwarding queue capacity
 * argv[4]: int     cost of transmission delay of eth1 (i.e., 134)
 * argv[5]: int     cost of transmission delay of eth2 (i.e., 134)
 * argv[6]: int     cost of transmission delay of eth3 (i.e., 134)
 * argv[7]: int     cost of transmission delay of eth4 (i.e., 134)
 */
int main(int argc, char const *argv[])
{
    struct nl_sock *sk;
    int ret, i;
    struct nl_msg *delta_msg = nlmsg_alloc();
    struct nlmsghdr *hdr;

    if (argc != 8) {
        perror("parameter invalid\n");
        return -1;
    }

    enable_load_awareness = atoi(argv[1]);
    delta = atof(argv[2]);
    forwarding_queue_capacity = atoi(argv[3]);
    for (i = 0; i < ARRAY_SIZE; ++i) {
        transmission_cost[i] = atoi(argv[i + 4]);
    }
    qlen_amplitude_threshold = (u_int32_t)round(delta * forwarding_queue_capacity);

    sk = nl_socket_alloc();

    nl_socket_disable_seq_check(sk);

    nl_socket_set_local_port(sk, LOAD_AWARENESS_PID);

    nl_connect(sk, NETLINK_RECV_PACKET);

   // set callback function for received netlink messages
    nl_socket_modify_cb(sk, NL_CB_MSG_IN, NL_CB_CUSTOM, nl_recv_message, NULL);

    // send qlen_amplitude_threshold to kernel
    hdr = nlmsg_put(delta_msg, LOAD_AWARENESS_PID, NL_AUTO_SEQ, NETLINK_RECV_PACKET, sizeof(qlen_amplitude_threshold), NLM_F_CREATE);
    if (hdr == NULL) {
        perror("nlmsg_put failed\n");
    }
    memcpy(nlmsg_data(hdr), &qlen_amplitude_threshold, sizeof(qlen_amplitude_threshold));
    ret = nl_send_auto(sk, delta_msg);
    if (ret < 0) {
        perror("nl_sned_auto failed\n");
    }
    // printf("netlink data len:%d\n", nlmsg_datalen(hdr));
    printf("sent qlen_amplitude_threshold:%u\n", qlen_amplitude_threshold);

    printf("Listening for netlink messages...\n");

    while (1)
    {
        nl_recvmsgs_default(sk);
    }

    return 0;
}

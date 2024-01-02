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

const char interface_name[4][5] = {"eth1", "eth2", "eth3", "eth4"};
int last_time_qlen[5] = {0};        // last_time_qlen[0] is the last-time qlen of eth1
int transmission_cost[5] = {0};     // transmission_cost[0] is the init cost of eth1
int recv_cnt = 0;
int enable_load_awareness = 0;
int forwarding_queue_capacity = 0;  // unit: packet
double delta;
char command[120];

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
    return round(delay * 10000.0);
}

static int nl_recv_message(struct nl_msg *msg, void *arg) {
    struct nlmsghdr *nlh = nlmsg_hdr(msg);
    int *array_data;
    int ret;

    recv_cnt++;

    if (nlh->nlmsg_len < NLMSG_HDRLEN + ARRAY_SIZE * sizeof(int)) {
        printf("Invalid message length\n");
        return -1;
    }

    array_data = (int *)NLMSG_DATA(nlh);

    printf("Received an int array from netlink message:\n");
    for (int i = 0; i < ARRAY_SIZE; ++i) {
        printf("cnt:%d Array[%d]: %d\n", recv_cnt, i, array_data[i]);
        if (array_data[i] != -1 && enable_load_awareness) { // array_data == -1 means this interface is down
            if ((double)abs(array_data[i] - last_time_qlen[i]) >= delta * (double)forwarding_queue_capacity) {
                // should change spf cost and flood
                double queuing_delay = estimate_queuing_delay(BANDWIDTH, PACKET_SIZE, array_data[i]);
                int new_cost = transmission_cost[i] + delay_to_cost(queuing_delay);

                last_time_qlen[i] = array_data[i];
                
                snprintf(command, sizeof(command), "./change_ospf_cost.sh %s %d", interface_name[i], new_cost);
                
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

    if (argc != 8) {
        perror("parameter invalid\n");
        return -1;
    }

    enable_load_awareness = atoi(argv[1]);
    delta = atoi(argv[2]);
    forwarding_queue_capacity = atoi(argv[3]);
    for (i = 0; i < ARRAY_SIZE; ++i) {
        transmission_cost[i] = atoi(argv[i + 4]);
    }

    sk = nl_socket_alloc();

    nl_socket_disable_seq_check(sk);

    nl_socket_set_local_port(sk, LOAD_AWARENESS_PID);

    nl_connect(sk, NETLINK_RECV_PACKET);

   // 设置回调函数来处理接收到的消息
    nl_socket_modify_cb(sk, NL_CB_MSG_IN, NL_CB_CUSTOM, nl_recv_message, NULL);

    printf("Listening for netlink messages...\n");

    while (1)
    {
        nl_recvmsgs_default(sk);
    }

    return 0;
}

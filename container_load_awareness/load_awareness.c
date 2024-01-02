#include <netlink/socket.h>
#include <netlink/netlink.h>
#include <netlink/msg.h>
#include <netlink/route/link.h>
#include <netlink/route/tc.h>
#include <netlink/route/qdisc.h>
#include <netlink/utils.h>
#include <netlink/cache.h>
#include <unistd.h>

#define NETLINK_RECV_PACKET	30
#define LOAD_AWARENESS_PID	258258
#define ARRAY_SIZE          4

int recv_cnt = 0;

static int nl_recv_message(struct nl_msg *msg, void *arg) {
    struct nlmsghdr *nlh = nlmsg_hdr(msg);
    int *array_data;

    recv_cnt++;

    if (nlh->nlmsg_len < NLMSG_HDRLEN + ARRAY_SIZE * sizeof(int)) {
        printf("Invalid message length\n");
        return -1;
    }

    array_data = (int *)NLMSG_DATA(nlh);

    printf("Received an int array from netlink message:\n");
    for (int i = 0; i < ARRAY_SIZE; ++i) {
        printf("cnt:%d Array[%d]: %d\n", recv_cnt, i, array_data[i]);
    }
}

int main(int argc, char const *argv[])
{
    struct nl_sock *sk;
    int ret;

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

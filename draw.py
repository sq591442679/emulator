import matplotlib.pyplot as plt


avg_drop_rate_list = [17.48, 14.58, 14.87, 13.46, 13.99, 12.58]  # unit: %
avg_delay_list = [63.39, 62.99, 63.59, 64.29, 64.73, 64.37]  # unit: ms
n_list = [0, 1, 2, 3, 4, 5]
ospf_drop_rate = 13.88  
ospf_delay = 64.95


def draw_drop_rate():
    plt.rcParams['axes.titlesize'] = 23
    plt.rcParams['axes.labelsize'] = 23
    plt.rcParams['xtick.labelsize'] = 23
    plt.rcParams['ytick.labelsize'] = 23
    plt.rcParams['legend.fontsize'] = 20

    fig, ax = plt.subplots()

    ax.plot(n_list, avg_drop_rate_list, 'o-', label='LoFi(n,1)', linewidth=2.5, markersize=10)

    ax.axhline(y=ospf_drop_rate, linestyle='--', color='C1', label='OPSPF', linewidth=2.5, markersize=10)

    ax.grid()

    ax.set_ylim(bottom=10, top=18)

    ax.set_xlabel('n')
    ax.set_xticks(n_list, [str(i) for i in n_list])
    ax.set_ylabel('Packet loss ratio (%)')
    
    # plt.show()
    plt.legend()
    plt.tight_layout()

    fig.savefig('./results/drop_rate.pdf', dpi=300, format='pdf')


def draw_delay():
    plt.rcParams['axes.titlesize'] = 23
    plt.rcParams['axes.labelsize'] = 23
    plt.rcParams['xtick.labelsize'] = 23
    plt.rcParams['ytick.labelsize'] = 23
    plt.rcParams['legend.fontsize'] = 20

    fig, ax = plt.subplots()

    ax.plot(n_list, avg_delay_list, 'o-', label='LoFi(n,1)', linewidth=2.5, markersize=10)

    ax.axhline(y=ospf_delay, linestyle='--', color='C1', label='OPSPF', linewidth=2.5, markersize=10)

    ax.grid()

    ax.set_ylim(bottom=55, top=70)

    ax.set_xlabel('n')
    ax.set_xticks(n_list, [str(i) for i in n_list])
    ax.set_ylabel('End-to-end delay (ms)')
    
    # plt.show()
    plt.legend()
    plt.tight_layout()

    fig.savefig('./results/delay.pdf', dpi=300, format='pdf')

if __name__ == '__main__':
    draw_drop_rate()
    draw_delay()

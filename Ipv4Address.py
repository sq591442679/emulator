class Ipv4Address:
    def __init__(self, ip1: int, ip2: int, ip3: int, ip4: int) -> None:
        self.ip1 = ip1
        self.ip2 = ip2
        self.ip3 = ip3
        self.ip4 = ip4

    def getNeighboringInterfaceIPAddress(self):
        if self.ip4 == 1:
            return Ipv4Address(self.ip1, self.ip2, self.ip3, 2)
        else:
            return Ipv4Address(self.ip1, self.ip2, self.ip3, 1)
        
    def __str__(self) -> str:
        return "%d.%d.%d.%d" % (self.ip1, self.ip2, self.ip3, self.ip4)
    
    def __hash__(self) -> int:
        return hash((self.ip1, self.ip2, self.ip3, self.ip4))
    
    def __eq__(self, other) -> bool:
        return isinstance(other, Ipv4Address) and self.ip1 == other.ip1 \
            and self.ip2 == other.ip2 and self.ip3 == other.ip3 and self.ip4 == other.ip4
    
    def __lt__(self, other):
        return (self.ip1, self.ip2, self.ip3, self.ip4) < (other.ip1, other.ip2, other.ip3, other.ip4)
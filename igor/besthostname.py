"""A method to get the best hostname for this machine"""
import socket

def besthostname():
    """A method to get the best hostname for this machine"""
    #
    # First find our preferred network interface address
    #
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('google.com', 9999))
    except socket.gaierror:
        return '127.0.0.1'
    ip, _ = s.getsockname()
    #
    # Now get our hostname, adding '.local' if needed
    #
    hostname = socket.getfqdn()
    if not '.' in hostname:
        hostname = hostname + '.local'
    #
    # See if this hostname matches our external IP address, return if so
    #
    try:
        _, _, ipaddrs = socket.gethostbyname_ex(hostname)
    except socket.gaierror:
        ipaddrs = []
    for extip in ipaddrs:
        if extip == ip:
            return hostname
    #
    # Otherwise try a reverse DNS lookup
    #
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except socket.gaierror:
        pass
    #
    # Otherwise return the IP address
    #
    return ip
    
    

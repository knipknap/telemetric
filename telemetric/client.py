from __future__ import print_function, absolute_import
import json
import zlib
import struct
import socket
from Exscript.util.ipv4 import is_ip as is_ipv4
from Exscript.util.ipv6 import is_ip as is_ipv6
from .util import print_json
from .gpb import GPBDecoder

def init(protos):
    global gpbdecoder #FIXME: create a proper client class that holds this
    gpbdecoder = GPBDecoder(protos)

##############################################################################
# JSON v1 (Pre IOS XR 6.1.0)
##############################################################################
def unpack_v1_message(data):
    while len(data) > 0:
        _type = unpack_int(data)
        data = data[4:]

        if _type == 1:
            data = data[4:]
            yield 1, None
        elif _type == 2:
            msg_length = unpack_int(data)
            data = data[4:]
            msg = data[:msg_length]
            data = data[msg_length:]
            yield 2, msg

def get_v1_message(length, c):
    global v1_deco

    data = b""
    while len(data) < length:
        data += c.recv(length - len(data))

    tlvs = []
    for x in unpack_v1_message(data):
        tlvs.append(x)

    #find the data
    for x in tlvs:
        if x[0] == 1:
            print("  Reset Compressor TLV")
            v1_deco = zlib.decompressobj()
        if x[0] == 2:
            print("  Mesage TLV")
            c_msg = x[1]
            j_msg_b = v1_deco.decompress(c_msg)
            if args.json_dump:
                # Print the message as-is
                print(j_msg_b)
            else:
                # Decode and pretty-print the message
                print_json(j_msg_b)

###############################################################################
# Event handling
############################################################################### 
# Should use enum.Enum but not available in python2.7.1 on EnXR
class TCPMsgType(object):
    RESET_COMPRESSOR = 1
    JSON = 2
    GPB_COMPACT = 3
    GPB_KEY_VALUE = 4

    @classmethod
    def to_string(self, value):
        if value == TCPMsgType.RESET_COMPRESSOR:
            return "RESET_COMPRESSOR (1)"
        elif value == TCPMsgType.JSON:
            return "JSON (2)"
        elif value == TCPMsgType.GPB_COMPACT:
            return "GPB_COMPACT (3)"
        elif value == TCPMsgType.GPB_KEY_VALUE:
            return "GPB_KEY_VALUE (4)"
        else:
            raise ValueError("{} is not a valid TCP message type".format(value))

TCP_FLAG_ZLIB_COMPRESSION = 0x1

def tcp_flags_to_string(flags):
    strings = []
    if flags & TCP_FLAG_ZLIB_COMPRESSION != 0:
        strings.append("ZLIB compression")
    if len(strings) == 0:
        return "None"
    else:
        return "|".join(strings)

def unpack_int(raw_data):
    return struct.unpack_from(">I", raw_data, 0)[0]

def get_message(conn, json_dump=False, print_all=True):
    """
    Handle a received TCP message.

    @type conn: socket
    @param conn: The TCP connection
    """
    print("Getting TCP message")

    # v1 message header (from XR6.0) consists of just a 4-byte length
    # v2 message header (from XR6.1 onwards) consists of 3 4-byte fields:
    #     Type,Flags,Length
    # If the first 4 bytes read is <=4 then it is too small to be a 
    # valid length. Assume it is v2 instead
    t = conn.recv(4)
    msg_type = unpack_int(t)
    if msg_type > 4:
        # V1 message - compressed JSON
        flags = TCP_FLAG_ZLIB_COMPRESSION
        msg_type_str = "JSONv1 (COMPRESSED)"
        length = msg_type
        msg_type = TCPMsgType.JSON
        print("  Message Type: {}".format(msg_type_str))
        return get_v1_message(length, conn)

    # V2 message
    try:
        msg_type_str = TCPMsgType.to_string(msg_type)
        print("  Message Type: {})".format(msg_type_str))
    except:
        print("  Invalid Message type: {}".format(msg_type))

    t = conn.recv(4)
    flags = unpack_int(t)
    print("  Flags: {}".format(tcp_flags_to_string(flags)))
    t = conn.recv(4)
    length = unpack_int(t)
    print("  Length: {}".format(length))
   
    # Read all the bytes of the message according to the length in the header 
    data = b""
    while len(data) < length:
        data += conn.recv(length - len(data))

    # Decompress the message if necessary. Otherwise use as-is
    if flags & TCP_FLAG_ZLIB_COMPRESSION != 0:
        try:
            print("Decompressing message")
            deco = zlib.decompressobj()
            msg = deco.decompress(data)
        except Exception as e:
            print("ERROR: failed to decompress message: {}".format(e))
            msg = None
    else:
        msg = data

    # Decode the data according to the message type in the header
    print("Decoding message")
    try:
        if msg_type == TCPMsgType.GPB_COMPACT:
            gpbdecoder.decode_compact(msg, json_dump=args.json_dump,
                                      print_all=args.print_all)
        elif msg_type == TCPMsgType.GPB_KEY_VALUE:
            gpbdecoder.decode_kv(msg, json_dump=args.json_dump,
                                 print_all=args.print_all)
        elif msg_type == TCPMsgType.JSON:
            if args.json_dump:
                # Print the message as-is
                print(msg)
            else:
                # Decode and pretty-print the message
                print_json(msg)
        elif msg_type == TCPMsgType.RESET_COMPRESSOR:
            deco = zlib.decompressobj()
    except Exception as e:
        print("ERROR: failed to decode TCP message: {}".format(e))

def tcp_loop(tcp_sock, json_dump=False, print_all=True):
    """
    Event Loop. Wait for TCP messages and pretty-print them
    """
    while True:
        print("Waiting for TCP connection")
        conn, addr = tcp_sock.accept()
        print("Got TCP connection")
        try:
            while True:
                 get_message(conn, json_dump=json_dump, print_all=print_all)
        except Exception as e:
            print("ERROR: Failed to get TCP message. Attempting to reopen connection: {}".format(e))

def udp_loop(udp_sock, json_dump=False, print_all=True):
    """
    Event loop. Wait for messages and then pretty-print them
    """
    while True:
        print("Waiting for UDP message")
        raw_message, address = udp_sock.recvfrom(2**16)
        # All UDP packets contain compact GPB messages
        gpbdecoder.decode_compact(raw_message,
                                  json_dump=json_dump,
                                  print_all=print_all)

def open_sockets(ip_address, port):
    # Figure out if the supplied address is ipv4 or ipv6 and set the socet type
    # appropriately
    if is_ipv4(ip_address):
        socket_type = socket.AF_INET
    elif is_ipv6(ip_address):
        socket_type = socket.AF_INET6   
    else:
        raise AttributeError("Invalid ip address ", ip_address)

    # Bind to two sockets to handle either UDP or TCP data
    udp_sock = socket.socket(socket_type, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind((ip_address, port))

    tcp_sock = socket.socket(socket_type)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind((ip_address, port))
    tcp_sock.listen(1)

    return tcp_sock, udp_sock

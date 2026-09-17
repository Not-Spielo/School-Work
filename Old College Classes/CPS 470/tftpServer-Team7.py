import socket
import struct
import os
import sys

# ========================== CONSTANTS ========================================
TFTP_PORT = 69                  # TFTP server listens on well-known port 69
BLOCK_SIZE = 512                # Each data block is 512 bytes (per RFC 1350)
MAX_UDP_PACKET_SIZE = 65535     # Maximum UDP packet size for recvfrom()
MAX_BLOCK_NUMBER = 65535        # Maximum value for a 2-byte unsigned integer

# TFTP Opcodes
OPCODE_RRQ   = 1    # Read Request
OPCODE_WRQ   = 2    # Write Request
OPCODE_DATA  = 3    # Data
OPCODE_ACK   = 4    # Acknowledgement
OPCODE_ERROR = 5    # Error

# TFTP Error Codes
ERR_NOT_DEFINED       = 0
ERR_FILE_NOT_FOUND    = 1
ERR_ACCESS_VIOLATION  = 2
ERR_DISK_FULL         = 3
ERR_ILLEGAL_OPERATION = 4
ERR_UNKNOWN_TID       = 5
ERR_FILE_EXISTS       = 6
ERR_NO_SUCH_USER      = 7


# ========================== HELPER FUNCTIONS =================================

def get_block(file_data, block_number, actual_block_count):
    """
    Retrieves the data for a specific block number from the file data.
    
    Since block numbers can roll over (wrap around) for large files,
    we use actual_block_count to track the true sequential block index.
    
    Parameters:
        file_data (bytes): The entire file content read into memory.
        block_number (int): The TFTP block number (may have rolled over).
        actual_block_count (int): The true sequential block count (1-indexed).
    
    Returns:
        bytes: The chunk of data for this block (0 to 512 bytes).
    """
    # Calculate the byte offset using the actual sequential count
    start = (actual_block_count - 1) * BLOCK_SIZE
    end = start + BLOCK_SIZE
    return file_data[start:end]


def get_total_blocks(file_data):
    """
    Calculates the total number of blocks needed to transfer the file.
    
    If the file size is an exact multiple of 512, an extra empty block
    is needed to signal the end of the transfer.
    
    Parameters:
        file_data (bytes): The entire file content.
    
    Returns:
        int: Total number of blocks.
    """
    file_size = len(file_data)
    total = file_size // BLOCK_SIZE
    # If file size is exact multiple of BLOCK_SIZE, we need one more
    # empty block to signal end of transfer. If not, the partial block
    # at the end already signals termination.
    if file_size % BLOCK_SIZE == 0:
        total += 1
    else:
        total += 1  # Account for the final partial block
    # Simplification: total blocks = ceil(file_size / BLOCK_SIZE)
    # But if file_size is 0, we still need 1 block (an empty one)
    if file_size == 0:
        return 1
    return (file_size + BLOCK_SIZE - 1) // BLOCK_SIZE + (1 if file_size % BLOCK_SIZE == 0 else 0)


def calculate_total_blocks(file_data):
    """
    A cleaner calculation of total blocks.
    
    Parameters:
        file_data (bytes): The entire file content.
    
    Returns:
        int: Total number of data blocks to send.
    """
    file_size = len(file_data)
    if file_size == 0:
        return 1  # Need to send one empty DATA packet to signal end
    total = file_size // BLOCK_SIZE
    if file_size % BLOCK_SIZE != 0:
        total += 1
    else:
        # File is exact multiple of 512; need an extra empty block
        total += 1
    return total


def build_data_packet(block_number, data):
    """
    Constructs a TFTP DATA packet.
    
    Format: 2 bytes (opcode=3) + 2 bytes (block #) + n bytes (data)
    
    Uses struct.pack for the header and concatenates the data bytes,
    as recommended in the assignment hints.
    
    Parameters:
        block_number (int): The block number for this DATA packet.
        data (bytes): The file data for this block (0-512 bytes).
    
    Returns:
        bytes: The complete DATA packet ready to send.
    """
    # Pack opcode and block number as big-endian unsigned shorts
    header = struct.pack('!HH', OPCODE_DATA, block_number)
    # Concatenate header with data payload
    return header + data


def build_error_packet(error_code, error_message):
    """
    Constructs a TFTP ERROR packet.
    
    Format: 2 bytes (opcode=5) + 2 bytes (error code) + string + 1 byte (0)
    
    Parameters:
        error_code (int): The TFTP error code (0-7).
        error_message (str): Human-readable error message.
    
    Returns:
        bytes: The complete ERROR packet ready to send.
    """
    # Pack opcode and error code as big-endian unsigned shorts
    header = struct.pack('!HH', OPCODE_ERROR, error_code)
    # Encode the error message as ASCII bytes, append null terminator
    msg_bytes = error_message.encode('ascii') + b'\x00'
    return header + msg_bytes


def parse_request(data):
    """
    Parses a TFTP RRQ or WRQ packet.
    
    Request format: 2 bytes (opcode) | filename (string) | 0 | mode (string) | 0
    
    The filename and mode are null-terminated ASCII strings. After extracting
    the opcode, we split the remaining bytes on the null byte to get the
    filename and mode.
    
    Parameters:
        data (bytes): The raw packet data received from the client.
    
    Returns:
        tuple: (opcode, filename, mode) where:
            - opcode (int): 1 for RRQ, 2 for WRQ
            - filename (str): The requested filename
            - mode (str): The transfer mode ('netascii' or 'octet')
    """
    # Extract the 2-byte opcode
    opcode = struct.unpack('!H', data[0:2])[0]
    
    # The rest of the packet contains filename\0mode\0
    # Split on null bytes to extract filename and mode
    remaining = data[2:]
    parts = remaining.split(b'\x00')
    
    # parts[0] = filename bytes, parts[1] = mode bytes
    filename = parts[0].decode('ascii')
    mode = parts[1].decode('ascii').lower()  # Mode is case-insensitive
    
    return opcode, filename, mode


def parse_ack(data):
    """
    Parses a TFTP ACK packet.
    
    ACK format: 2 bytes (opcode=4) + 2 bytes (block number)
    
    Parameters:
        data (bytes): The raw ACK packet data.
    
    Returns:
        tuple: (opcode, block_number)
    """
    opcode, block_number = struct.unpack('!HH', data[0:4])
    return opcode, block_number


def parse_error(data):
    """
    Parses a TFTP ERROR packet.
    
    ERROR format: 2 bytes (opcode=5) + 2 bytes (error code) + string + 0
    
    Parameters:
        data (bytes): The raw ERROR packet data.
    
    Returns:
        tuple: (opcode, error_code, error_message)
    """
    opcode, error_code = struct.unpack('!HH', data[0:4])
    # Error message is the rest, minus the trailing null byte
    error_message = data[4:].split(b'\x00')[0].decode('ascii')
    return opcode, error_code, error_message


# ========================== MAIN SERVER LOGIC ================================

def main():
    """
    Main function that runs the TFTP server.
    
    The server:
    1. Creates a UDP socket bound to port 69
    2. Waits for a client RRQ (read request)
    3. Parses the request to extract filename and mode
    4. Reads the requested file into memory
    5. Sends the file block-by-block, waiting for ACKs
    6. Handles duplicate ACKs by retransmitting the appropriate block
    7. Handles block number rollover for large files
    8. Sends error packets for file-not-found or illegal operations
    """
    
    # ---- Step 1: Create and bind the UDP socket ----
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', TFTP_PORT))
    
    print("#" * 30)
    print("Wait for Client's Connection !")
    
    # ---- Step 2: Receive the initial request from the client ----
    data, client_address = server_socket.recvfrom(MAX_UDP_PACKET_SIZE)
    
    # ---- Step 3: Parse the request ----
    opcode, filename, mode = parse_request(data)
    
    # Print the decoded request information (as shown in assignment examples)
    print(f"The decoded file requesting message from client is @{filename}{mode}")
    print(f"Client is using {mode} mode")
    print(f"The client requests downloading file : {filename}")
    
    # ---- Step 4: Verify it is a Read Request (RRQ) ----
    if opcode != OPCODE_RRQ:
        # If it's not a read request, send an error and exit
        print(f"Received opcode {opcode}, expected RRQ (1). Sending error.")
        error_packet = build_error_packet(ERR_ILLEGAL_OPERATION, "Illegal TFTP operation")
        server_socket.sendto(error_packet, client_address)
        server_socket.close()
        sys.exit(1)
    
    # ---- Step 5: Check if the file exists ----
    if not os.path.isfile(filename):
        print(f"File '{filename}' not found. Sending error to client.")
        error_packet = build_error_packet(ERR_FILE_NOT_FOUND, "File not found")
        server_socket.sendto(error_packet, client_address)
        server_socket.close()
        sys.exit(1)
    
    # ---- Step 6: Read the file into memory ----
    # Open in binary mode regardless of transfer mode.
    # The file data is always read as raw bytes; the mode only affects
    # how the client interprets the data.
    with open(filename, 'rb') as f:
        file_data = f.read()
    
    file_size = len(file_data)
    print(f"File size: {file_size} bytes")
    
    # ---- Step 7: Calculate total number of blocks ----
    total_blocks = file_size // BLOCK_SIZE
    if file_size % BLOCK_SIZE != 0:
        total_blocks += 1
    elif file_size == 0:
        total_blocks = 1  # Send one empty DATA packet for a 0-byte file
    else:
        # File size is an exact multiple of 512
        # Need an extra empty block to signal end of transfer
        total_blocks += 1
    
    print(f"Total blocks to send: {total_blocks}")
    
    # ---- Step 8: Send data blocks and wait for ACKs ----
    # actual_block_count tracks the true sequential block (1, 2, 3,...)
    # block_number is the value sent in the TFTP header (rolls over at 65535)
    actual_block_count = 1
    block_number = 1
    
    while actual_block_count <= total_blocks:
        # Get the data for the current block
        block_data = get_block(file_data, block_number, actual_block_count)
        
        # Build the DATA packet
        data_packet = build_data_packet(block_number, block_data)
        
        # Send the DATA packet to the client
        server_socket.sendto(data_packet, client_address)
        print(f"Packet {block_number} has been sent.")
        
        # Wait for ACK from the client
        while True:
            ack_data, ack_address = server_socket.recvfrom(MAX_UDP_PACKET_SIZE)
            
            # Extract the opcode from the received packet
            recv_opcode = struct.unpack('!H', ack_data[0:2])[0]
            
            # ---- Handle ERROR packets from client ----
            if recv_opcode == OPCODE_ERROR:
                _, err_code, err_msg = parse_error(ack_data)
                print(f"Error received from client - Code: {err_code}, Message: {err_msg}")
                server_socket.close()
                sys.exit(1)
            
            # ---- Handle ACK packets ----
            if recv_opcode == OPCODE_ACK:
                _, ack_block = parse_ack(ack_data)
                
                if ack_block == block_number:
                    # Correct ACK received - move to next block
                    print(f"Packet {block_number} has been acked by client.")
                    
                    # Advance to the next block
                    actual_block_count += 1
                    
                    # Handle block number rollover for large files
                    # When block_number reaches MAX_BLOCK_NUMBER (65535),
                    # the next block number wraps around to 0.
                    # The Windows TFTP client typically rolls over to 0.
                    if block_number == MAX_BLOCK_NUMBER:
                        block_number = 0
                    else:
                        block_number += 1
                    
                    break  # Exit the ACK-waiting loop, send next block
                
                else:
                    # ---- Handle duplicate/old ACKs ----
                    # The client is re-acknowledging a previous block,
                    # which means it didn't receive our last DATA packet.
                    # We need to retransmit the current block.
                    print(f"Duplicate ACK received for block {ack_block}. "
                          f"Retransmitting block {block_number}.")
                    
                    # Resend the current DATA packet
                    server_socket.sendto(data_packet, client_address)
                    print(f"Packet {block_number} has been sent.")
            else:
                # Unexpected opcode received
                print(f"Unexpected opcode {recv_opcode} received. Ignoring.")
    
    # ---- Step 9: Transfer complete ----
    print("File transfer complete!")
    
    # ---- Step 10: Close the socket and exit cleanly ----
    server_socket.close()
    print("Socket closed. Server exiting.")


# ========================== ENTRY POINT ======================================
if __name__ == '__main__':
    main()
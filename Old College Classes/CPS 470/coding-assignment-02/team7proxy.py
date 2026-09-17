from socket import *
import sys
import os
from urllib.parse import urlparse

if len(sys.argv) <= 1:
    print('Usage : "python3 ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server]')
    sys.exit(2)

# Create a server socket, bind it to a port and start listening 
# bind address and port
serverIP = sys.argv[1]
serverPort = 8888

# Create a server socket, bind it to a port and start listening
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
tcpSerSock.bind((serverIP, serverPort))
tcpSerSock.listen(5)

print(f"Proxy server listening on {serverIP}:{serverPort}")

while 1:
    # Strat receiving data from the client 
    print('Ready to serve...')
    tcpCliSock, addr = tcpSerSock.accept()
    print('Received a connection from:', addr)
    message = tcpCliSock.recv(4096).decode(errors='ignore')
    if not message:
        tcpCliSock.close()
        continue
    print(message)

    # Extract the filename from the given message
    try:
        url = message.split()[1]
    except Exception:
        tcpCliSock.close()
        continue

    # Parse the URL (supports absolute-URI and origin-form)
    parsed = urlparse(url)
    hostn = parsed.netloc
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query

    if not hostn:
        # Fallback: use Host header when URL is origin-form (e.g., GET /path HTTP/1.1)
        host_header = None
        for line in message.splitlines():
            if line.lower().startswith('host:'):
                host_header = line.split(':', 1)[1].strip()
                break
        hostn = host_header or ''

        # Additionally support requests sent to proxy as http://localhost:8888/<host>/<path>
        # In that case the first path segment is the target host.
        if parsed.path and parsed.path.startswith('/'):
            segs = parsed.path.lstrip('/').split('/', 1)
            if len(segs) >= 1 and ('.' in segs[0] or ':' in segs[0]):
                # treat first segment as remote host
                hostn = segs[0]
                if len(segs) == 2:
                    path = '/' + segs[1]
                else:
                    path = '/'

    print('Remote host:', hostn)

    # Extract filename for cache from path
    filename = path.lstrip('/')
    if filename == '':
        filename = 'index.html'
    fileExist = "false"
    filetouse = "/" + os.path.join(hostn, filename)
    print(filetouse)

    try:
        # Check wether the file exist in the cache 
        with open(filetouse[1:], 'rb') as f:
            outputdata = f.read()
        fileExist = "true"

        # ProxyServer finds a cache hit and generates a response message 
        # We saved the full raw response previously; extract body to send a clean reply
        header_end = outputdata.find(b"\r\n\r\n")
        if header_end == -1:
            header_end = outputdata.find(b"\n\n")
            sep_len = 2
        else:
            sep_len = 4

        if header_end != -1:
            body = outputdata[header_end + sep_len:]
        else:
            body = outputdata

        tcpCliSock.sendall(b"HTTP/1.0 200 OK\r\n")
        tcpCliSock.sendall(f"Content-Length: {len(body)}\r\n".encode())
        tcpCliSock.sendall(b"Content-Type: text/html\r\n\r\n")
        tcpCliSock.sendall(body)
        print('Read from cache')

    # Error handling for file not found in cache 
    except IOError:
        if fileExist == "false":
            # Create a socket on the proxyserver 
            c = socket(AF_INET, SOCK_STREAM)
            hostn_short = hostn.replace("www.", "", 1)
            print(hostn_short)
            try:
                # Connect to the socket to port 80 
                # handle optional port in hostn
                remote_host = hostn
                remote_port = 80
                if ':' in hostn:
                    remote_host, portstr = hostn.split(':', 1)
                    try:
                        remote_port = int(portstr)
                    except ValueError:
                        remote_port = 80

                c.connect((remote_host, remote_port))

                # Create a temporary file on this socket and ask port 80 for the file requested by the client 
                # Use HTTP/1.0 to get a response and close
                get_req = f"GET {path} HTTP/1.0\r\nHost: {hostn}\r\n\r\n"
                c.sendall(get_req.encode())

                # Read the response into buffer 
                response = b""
                while True:
                    data = c.recv(4096)
                    if not data:
                        break
                    response += data

                # Create a new file in the cache for the requested file. 
                # Also send the response in the buffer to client socket and the corresponding file in the cache 
                cache_path = filetouse[1:]
                cache_dir = os.path.dirname(cache_path)
                if cache_dir and not os.path.exists(cache_dir):
                    os.makedirs(cache_dir, exist_ok=True)
                with open(cache_path, 'wb') as tmpFile:
                    tmpFile.write(response)

                tcpCliSock.sendall(response)

            except Exception as e:
                print('Illegal request', e)
        else:
            # HTTP response message for file not found 
            try:
                tcpCliSock.sendall(b"HTTP/1.0 404 Not Found\r\n")
                tcpCliSock.sendall(b"Content-Type: text/html\r\n\r\n")
                tcpCliSock.sendall(b"<html><body><h1>404 Not Found</h1></body></html>")
            except Exception:
                pass

        # Close the client and the server sockets 
        tcpCliSock.close()

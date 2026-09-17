## ex: python3 TCP_server.py 127.0.0.1 5555

import socket
import sys
import threading
import time

class TCPServer:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = None
        self.in_use_connections = {}  # {connection_id: timestamp}
        self.running = True
        self.server_timeout = 300  # 5 minutes
        self.connection_timeout = 60  # 1 minute
        self.last_request_time = time.time()
        
        # Server timeout timer
        self.server_timer = threading.Timer(self.server_timeout, self.server_timeout_handler)
        # Connection ID cleanup timer
        self.cleanup_timer = threading.Timer(60, self.cleanup_old_connections)
        
    def setup_socket(self):
        """Setup TCP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.server_ip, self.server_port))
            self.socket.listen(5)
            self.socket.settimeout(1)  # Set timeout to allow timer checks
        except Exception as e:
            print(f"Error setting up socket: {e}")
            sys.exit(1)
    
    def server_timeout_handler(self):
        """Handle server timeout after 5 minutes of no requests"""
        self.running = False
        self.cleanup()
    
    def cleanup_old_connections(self):
        """Remove connection IDs older than 1 minute"""
        if not self.running:
            return
        
        current_time = time.time()
        expired_ids = [
            conn_id for conn_id, timestamp in self.in_use_connections.items()
            if current_time - timestamp > self.connection_timeout
        ]
        
        for conn_id in expired_ids:
            del self.in_use_connections[conn_id]
        
        # Restart cleanup timer
        self.cleanup_timer = threading.Timer(60, self.cleanup_old_connections)
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()
    
    def restart_server_timer(self):
        """Restart the server timeout timer"""
        self.server_timer.cancel()
        self.server_timer = threading.Timer(self.server_timeout, self.server_timeout_handler)
        self.server_timer.daemon = True
        self.server_timer.start()
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        try:
            client_ip, client_port = client_address
            
            # Receive HELLO message
            data = client_socket.recv(1024)
            if not data:
                client_socket.close()
                return
            
            message = data.decode('utf-8').strip()
            parts = message.split()
            
            if len(parts) != 2 or parts[0] != "HELLO":
                client_socket.close()
                return
            
            connection_id = parts[1]
            
            if connection_id in self.in_use_connections:
                # Connection ID already in use
                response = f"RESET {connection_id}"
                client_socket.send(response.encode('utf-8'))
            else:
                # Connection ID not in use
                self.in_use_connections[connection_id] = time.time()
                response = f"OK {connection_id} {client_ip} {client_port}"
                client_socket.send(response.encode('utf-8'))
            
            client_socket.close()
        
        except Exception as e:
            try:
                client_socket.close()
            except:
                pass
    
    def run(self):
        """Main server loop"""
        self.setup_socket()
        
        # Start cleanup timer
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()
        
        # Start server timeout timer
        self.server_timer.daemon = True
        self.server_timer.start()
        
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                
                # Restart server timeout timer on each request
                self.restart_server_timer()
                self.last_request_time = time.time()
                
                # Handle client in a new thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
            
            except socket.timeout:
                # Continue checking if should exit
                continue
            except Exception as e:
                if self.running:
                    pass
        
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self.server_timer.cancel()
        self.cleanup_timer.cancel()
        if self.socket:
            self.socket.close()

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 TCP_server.py <server_ip> <server_port>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print("Server port must be a valid integer")
        sys.exit(1)
    
    server = TCPServer(server_ip, server_port)
    
    try:
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
    except Exception as e:
        print(f"Server error: {e}")
        server.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()

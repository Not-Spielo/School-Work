## ex: python3 TCP_client.py 127.0.0.1 5555 1111

import socket
import sys

class TCPClient:
    def __init__(self):
        self.socket = None
        self.max_retries = 3
        self.timeout = 60  # 60 seconds
    
    def connect(self, server_ip, server_port, connection_id):
        """Attempt to connect with given connection ID"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            
            # Connect to server
            self.socket.connect((server_ip, server_port))
            
            # Send HELLO message
            message = f"HELLO {connection_id}"
            self.socket.send(message.encode('utf-8'))
            
            # Receive response
            response = self.socket.recv(1024)
            response_text = response.decode('utf-8').strip()
            
            # Parse response
            return self.handle_response(response_text, connection_id)
        
        except socket.timeout:
            return False, "timeout"
        except Exception as e:
            return False, "error"
    
    def handle_response(self, response, connection_id):
        """Handle server response"""
        parts = response.split()
        
        if len(parts) >= 2:
            msg_type = parts[0]
            
            if msg_type == "OK" and len(parts) == 4:
                # OK <connection_id> <client_ip> <client_port>
                returned_id = parts[1]
                client_ip = parts[2]
                client_port = parts[3]
                print(f"Connection established {returned_id} {client_ip} {client_port}")
                return True, None
            
            elif msg_type == "RESET" and len(parts) == 2:
                # RESET <connection_id>
                return False, "reset"
        
        return False, "invalid"
    
    def cleanup(self):
        """Close socket"""
        if self.socket:
            self.socket.close()
    
    def run(self, server_ip, server_port, initial_connection_id):
        """Main client loop with retries"""
        connection_id = initial_connection_id
        
        for attempt in range(self.max_retries):
            success, error_type = self.connect(server_ip, server_port, connection_id)
            self.cleanup()
            
            if success:
                return
            
            # Failed attempt
            if attempt < self.max_retries - 1:
                print(f"Connection Error {connection_id}")
                # Ask for new connection ID
                connection_id = input("Enter new connection ID: ").strip()
        
        # All attempts failed
        print("Connection Failure")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 TCP_client.py <server_ip> <server_port> <connection_id>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print("Server port must be a valid integer")
        sys.exit(1)
    
    connection_id = sys.argv[3]
    
    client = TCPClient()
    
    try:
        client.run(server_ip, server_port, connection_id)
    except KeyboardInterrupt:
        client.cleanup()
    except Exception as e:
        client.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()


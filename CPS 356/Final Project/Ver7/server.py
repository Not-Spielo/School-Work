#server.py
import socket
import json
import hashlib
import os
import threading



class Monitor:
    def __init__(self):
        self.condition = threading.Condition()
        self.is_available = True
        self.credentials = {}
        self.active_clients = {}
        self.memory = {}
        # Initilize Fixed 10 100KB memory segments
        for i in range(10):
            memory_location = "{0:0=2d}".format(i)
            self.memory[f"0x{memory_location}"] = {"size": 100, "used": False}
    
    def allocate_memory(self, data):
        _, size = data.split(':')
        for memory in self.memory:
            if self.memory[memory]["size"] >= size and not self.memory[memory]["used"]:
                return 
            
    def enter_monitor(self):
        with self.condition:
            while not self.is_available:
                self.condition.wait()
            self.is_available = False

    def exit_monitor(self):
        with self.condition:
            self.is_available = True
            self.condition.notify_all()

    def register_user(self, username, password):
        self.enter_monitor()
        response = {}
        if username in self.credentials:
            response = {
                "status": "failure",
                "message": "Username already exists"
            }
        else:
            self.credentials[username] = hash_password(password)
            save_credentials(self.credentials)
            response = {
                "status": "success"
            }
        self.exit_monitor()
        return response
    
    def login(self, username, password, socket):
        self.enter_monitor()
        response = ""
        hashed_password = hash_password(password)
        if username in self.credentials and self.credentials[username] == hashed_password:
            if username in self.active_clients:
                username = None
                response = {
                    "status": "failure",
                    "message": "User already logged in"
                }
            else:
                self.active_clients[username] = socket
                response = {
                    "status": "success"
                }
        else:        
            response = {
                "status": "failure",
                "message": "Incorrect username or password"
            }
            username = None
        self.exit_monitor()
        return response

    def send_message(self, sender, recipient, message):
        response = ""
        self.enter_monitor()
        if sender is None:
            response = {
                "status": "failure",
                "message": "Not currently logged in"
            }
        else:
            if recipient not in self.active_clients:
                response = {
                    "status": "failure",
                    "message": f"{recipient} is currently not logged in"
                }
            else:
                recipient_socket = self.active_clients[recipient]
                data = {
                    "sender": sender,
                    "message": message
                }
                recipient_socket.send(json.dumps(data).encode())
                response = {
                    "status": "success"
                }
        self.exit_monitor()
        print(response)
        return response
    
    def logout(self, username):
        response = {}
        self.enter_monitor()
        if username in self.active_clients:
            del self.active_clients[username]
            response = {
                "status": "success"
            }
        else:
            response = {
                "status": "failure",
                "message": f"User not logged in"
            }
        self.exit_monitor()
        return response
    
    def modify_user(self, action, username, password, optional_params):
        response = ""
        self.enter_monitor()
        try:
            hashed_password = hash_password(password)

            # Verify user credentials
            if username not in self.credentials or self.credentials[username] != hashed_password:
                response = {
                    "status": "failure",
                    "message": "Incorrect username or password"
                }
            else:
                if action == "change":
                    # Extract new username and password, if provided
                    new_username = optional_params['new_username'] if 'new_username' in optional_params and optional_params['new_username'] != "" else username
                    new_password = optional_params['new_password'] if 'new_password' in optional_params and optional_params['new_password'] != "" else password
                    # Update username if different and unique
                    if new_username != username and new_username in self.credentials:
                        response = {
                            "status": "failure",
                            "message": "Username already exists"
                        }
                    else:
                        # Update credentials dictionary
                        if new_username != username:
                            self.credentials[new_username] = self.credentials.pop(username)  # Rename key

                        # Update password if it was changed
                        if new_password != password:
                            self.credentials[new_username] = hash_password(new_password)
                        save_credentials(self.credentials)
                        response = {
                            "status": "success"
                        }

                elif action == "delete":
                    del self.credentials[username]
                    save_credentials(self.credentials)
                    response = {
                        "status": "success"
                    }
        except (ValueError, IndexError) as e:
            response = f"Modification failed. Invalid input format: {e}"
        self.exit_monitor()
        return response

    def client_disconnect(self, username):
        # Handle client disconnection
        if username in self.active_clients:
            del self.active_clients[username]

MONITOR = Monitor()
    
# Load user credentials from users.json
def load_credentials():
    if not os.path.exists("users.json"):
        return {}
    with open("users.json", "r") as file:
        return json.load(file)

# Save user credentials to users.json
def save_credentials(credentials):
    with open("users.json", "w") as file:
        json.dump(credentials, file, indent=4)

# Hash a password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Handle each client connection
def handle_client(client_socket, client_address):
    credentials = load_credentials()
    username = None

    while True:
        try:
            # Receive data from the client
            data = client_socket.recv(1024).decode()
            if not data:
                break
            
            data = json.loads(data)
            print(f"Received from {client_address}: {data}")
            response = "Invalid format. Use 'LOGIN', 'REGISTER', 'MODIFY', 'MESSAGE', or 'LOGOUT'."
            
            # Process REGISTER command
            if data['action'] == "register":
                _username = data['username']
                _password = data['password']
                response = MONITOR.register_user(_username, _password)

            # Process LOGIN command
            elif data['action'] == "login":
                _username = data['username']
                _password = data['password']
                response = MONITOR.login(_username, _password, client_socket)
                if response['status'] == "success":
                    username = _username

            # Process MODIFY command
            elif data['action'] == "modify":
                _action = data['modify_action']
                _username = data['username']
                _password = data['password']
                _optional_params = data['optional_params']
                response = MONITOR.modify_user(_action, _username, _password, _optional_params)

            # Process MESSAGE command
            elif data['action'] == "message":
                _recipient = data['recipient']
                _message = data['message']
                response = MONITOR.send_message(username, _recipient, _message)

            # Process LOGOUT command
            elif data['action'] == "logout":
                response = MONITOR.logout(username)

            response = json.dumps(response)
            # Send response back to client
            client_socket.send(response.encode())

        except ConnectionError:
            break

    MONITOR.client_disconnect(username)
    client_socket.close()
    print(f"Connection with {client_address} closed.")

def start_server():
    global MONITOR
    host = '127.0.0.1'
    port = 6969
    MONITOR.credentials = load_credentials()
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        
        # Start a new thread for each client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    start_server()

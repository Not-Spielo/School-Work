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
    
    def enter_monitor(self):
        with self.condition:
            while not self.is_available:
                self.condition.wait()
            self.is_available = False

    def exit_monitor(self):
        with self.condition:
            self.is_available = True
            self.condition.notify_all()

    def register_user(self, data):
        self.enter_monitor()
        response = ""
        _, new_username, new_password = data.split(':', 2)
        if new_username in self.credentials:
            response = "Registration failed. Username already exists."
        else:
            self.credentials[new_username] = hash_password(new_password)
            save_credentials(self.credentials)
            response = "Registration successful."
        self.exit_monitor()
        return response
    
    def login(self, data, socket):
        self.enter_monitor()
        response = ""
        _, username, password = data.split(':', 2)
        hashed_password = hash_password(password)
        if username in self.credentials and self.credentials[username] == hashed_password:
            if username in self.active_clients:
                username = None
                response = "User already logged in."
            else:
                self.active_clients[username] = socket
                response = "Authentication successful!"
        else:        
            response = "Authentication failed. Incorrect username or password."
            username = None
        self.exit_monitor()
        return username, response

    def send_message(self, data, username):
        response = ""
        self.enter_monitor()
        if username is None:
            response = "Error: You are not logged in."
        else:
            _, recipient, message = data.split(':', 2)
            if recipient not in self.active_clients:
                response = f"Error: {recipient} is not logged in."
            else:
                recipient_socket = self.active_clients[recipient]
                recipient_socket.send(f"Message from {username}: {message}".encode())
                response = f"Message sent to {recipient}: \"{message}\""
        self.exit_monitor()
        return response
    
    def logout(self, username):
        response = ""
        self.enter_monitor()
        if username in self.active_clients:
            del self.active_clients[username]
            response = "Logout successful."
        else:
            response = "Error: You are not logged in."
        self.exit_monitor()
        return response
    
    def modify_user(self, data):
        response = ""
        self.enter_monitor()
        try:
            parts = data.split(':')
            action = parts[1]
            username = parts[2]
            password = parts[3]
            hashed_password = hash_password(password)
            optional_params = parts[4:]  # All extra parts are optional params

            # Verify user credentials
            if username not in self.credentials or self.credentials[username] != hashed_password:
                response = "Modification failed. Incorrect username or password."
            else:
                if action == "change":
                    # Extract new username and password, if provided
                    new_username = optional_params[0] if len(optional_params) > 0 and optional_params[0] else username
                    new_password = optional_params[1] if len(optional_params) > 1 and optional_params[1] else password

                    # Update username if different and unique
                    if new_username != username and new_username in self.credentials:
                        response = "Modification failed. New username already exists."
                    else:
                        # Update credentials dictionary
                        if new_username != username:
                            self.credentials[new_username] = self.credentials.pop(username)  # Rename key

                        # Update password if it was changed
                        if new_password != password:
                            self.credentials[new_username] = hash_password(new_password)
                        save_credentials(self.credentials)
                        response = "Modification successful. Your account has been updated."

                elif action == "delete":
                    del self.credentials[username]
                    save_credentials(self.credentials)
                    response = "Account deletion successful. Your account has been permanently deleted."
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

            print(f"Received from {client_address}: {data}")
            response = "Invalid format. Use 'LOGIN', 'REGISTER', 'MODIFY', 'MESSAGE', or 'LOGOUT'."
            
            # Process REGISTER command
            if data.startswith("REGISTER:"):
                response = MONITOR.register_user(data)

            # Process LOGIN command
            elif data.startswith("LOGIN:"):
                username, response = MONITOR.login(data, client_socket)
                print(username)
                print(response)

            # Process MODIFY command
            elif data.startswith("MODIFY:"):
                response = MONITOR.modify_user(data)

            # Process MESSAGE command
            elif data.startswith("MESSAGE:"):
                response = MONITOR.send_message(data, username)

            # Process LOGOUT command
            elif data == "LOGOUT":
                response = MONITOR.logout(username)

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

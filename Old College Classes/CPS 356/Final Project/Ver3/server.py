import socket
import json
import hashlib
import os
import threading

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

# Dictionary to keep track of logged-in users
logged_in_clients = {}

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
                _, new_username, new_password = data.split(':', 2)
                if new_username in credentials:
                    response = "Registration failed. Username already exists."
                else:
                    credentials[new_username] = hash_password(new_password)
                    save_credentials(credentials)
                    response = "Registration successful."

            # Process LOGIN command
            elif data.startswith("LOGIN:"):
                _, username, password = data.split(':', 2)
                hashed_password = hash_password(password)

                if username in credentials and credentials[username] == hashed_password:
                    if username in logged_in_clients:
                        response = "User already logged in."
                    else:
                        logged_in_clients[username] = client_socket
                        response = "Authentication successful!"
                else:
                    response = "Authentication failed. Incorrect username or password."

            # Process MODIFY command
            elif data.startswith("MODIFY:"):
                try:
                    parts = data.split(':')
                    action = parts[1]
                    username = parts[2]
                    password = parts[3]
                    hashed_password = hash_password(password)
                    optional_params = parts[4:]  # All extra parts are optional params

                    # Verify user credentials
                    if username not in credentials or credentials[username] != hashed_password:
                        response = "Modification failed. Incorrect username or password."
                    else:
                        if action == "change":
                            # Extract new username and password, if provided
                            new_username = optional_params[0] if len(optional_params) > 0 and optional_params[0] else username
                            new_password = optional_params[1] if len(optional_params) > 1 and optional_params[1] else password

                            # Update username if different and unique
                            if new_username != username and new_username in credentials:
                                response = "Modification failed. New username already exists."
                            else:
                                # Update credentials dictionary
                                if new_username != username:
                                    credentials[new_username] = credentials.pop(username)  # Rename key

                                # Update password if it was changed
                                if new_password != password:
                                    credentials[new_username] = hash_password(new_password)
                                save_credentials(credentials)
                                response = "Modification successful. Your account has been updated."

                        elif action == "delete":
                            del credentials[username]
                            save_credentials(credentials)
                            response = "Account deletion successful. Your account has been permanently deleted."
                except (ValueError, IndexError) as e:
                    response = f"Modification failed. Invalid input format: {e}"

            # Process MESSAGE command
            elif data.startswith("MESSAGE:"):
                if username is None:
                    response = "Error: You are not logged in."
                else:
                    _, recipient, message = data.split(':', 2)
                    if recipient not in logged_in_clients:
                        response = f"Error: {recipient} is not logged in."
                    else:
                        recipient_socket = logged_in_clients[recipient]
                        recipient_socket.send(f"Message from {username}: {message}".encode())
                        response = f"Message sent to {recipient}."

            # Process LOGOUT command
            elif data == "LOGOUT":
                if username in logged_in_clients:
                    del logged_in_clients[username]
                    response = "Logout successful."
                    client_socket.send(response.encode())
                    break
                else:
                    response = "Error: You are not logged in."

            # Send response back to client
            client_socket.send(response.encode())

        except ConnectionError:
            break

    # Handle client disconnection
    if username in logged_in_clients:
        del logged_in_clients[username]
    client_socket.close()
    print(f"Connection with {client_address} closed.")

def start_server():
    host = '127.0.0.1'
    port = 6969

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

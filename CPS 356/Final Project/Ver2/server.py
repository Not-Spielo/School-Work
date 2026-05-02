import socket
import json
import hashlib
import os

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

def start_server():
    host = '127.0.0.1'
    port = 6969

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the host and port
    server_socket.bind((host, port))

    # Listen for incoming connections
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        # Receive data from the client
        data = client_socket.recv(1024).decode()
        print(f"Received: {data}")

        credentials = load_credentials()
        response = "Invalid format. Use 'LOGIN', 'REGISTER', or 'MODIFY'."

        if data.startswith("REGISTER:"):
            _, new_username, new_password = data.split(':', 2)
            if new_username in credentials:
                response = "Registration failed. Username already exists."
            else:
                credentials[new_username] = hash_password(new_password)
                save_credentials(credentials)
                response = "Registration successful."

        elif data.startswith("LOGIN:"):
            _, username, password = data.split(':', 2)
            hashed_password = hash_password(password)

            if username in credentials and credentials[username] == hashed_password:
                response = "Authentication successful!"
            else:
                response = "Authentication failed. Incorrect username or password."

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

        client_socket.send(response.encode())
        client_socket.close()

if __name__ == "__main__":
    start_server()

import socket
import json

# Load user credentials from user.json
def load_credentials():
    with open("users.json", "r") as file:
        data = json.load(file)
    return data["username"], data["password"]

def start_server():
    host = '127.0.0.1'  # Localhost
    port = 6969        # Choose an available port, internet says anything above 1000 works

    # Load username and password from the JSON file
    expected_username, expected_password = load_credentials()

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the host and port
    server_socket.bind((host, port))

    # Listen for incoming connections
    server_socket.listen(1)  # Allow only one connection at a time
    print(f"Server listening on {host}:{port}")

    while True:
        # Accept a connection from a client
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        # Receive data from the client
        data = client_socket.recv(1024).decode()  # Receive up to 1024 bytes
        print(f"Received: {data}")

        # Expect the data in "username:password" format
        if ':' in data:
            username, password = data.split(':', 1)

            # TODO:remove this part later - Debugging: Print received and expected values
            print(f"Received username: '{username}', password: '{password}'")
            print(f"Expected username: '{expected_username}', password: '{expected_password}'")

            # Validate credentials
            if username == expected_username and password == expected_password:
                response = "Authentication successful!"
            else:
                response = "Authentication failed. Incorrect username or password."
        else:
            response = "Invalid format. Use 'username:password'."

        # Send a response to the client
        client_socket.send(response.encode())

        # Close the client socket
        client_socket.close()

if __name__ == "__main__":
    start_server()
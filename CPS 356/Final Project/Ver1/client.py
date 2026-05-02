import socket

def start_client():
    host = '127.0.0.1'  # Server address, should be same as server host
    port = 6969          # Server port, should be same as server port

    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    client_socket.connect((host, port))
    print(f"Connected to server on {host}:{port}")

    # Replace with the actual username and password you want to test
    username = "username"
    password = "password"
    message = f"{username}:{password}"
    client_socket.send(message.encode())

    # Receive a response from the server
    response = client_socket.recv(1024)
    print(f"Received from server: {response.decode()}")

    # Close the client socket
    client_socket.close()

if __name__ == "__main__":
    start_client()

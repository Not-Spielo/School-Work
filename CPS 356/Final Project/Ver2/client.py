import socket

def start_client():
    host = '127.0.0.1'
    port = 6969

    while True:
        # Prompt user for action
        action = input("Type (L)ogin to log in, (R)egister to register, (M)odify to delete/change a user, or (Q)uit: ").strip().lower()

        # Check for command
        match action:
            case "quit" | "q" | "exit":
                print("Closing client. Goodbye!")
                break
            case "login" | "l":
                action_type = "LOGIN"
            case "register" | "r":
                action_type = "REGISTER"
            case "modify" | "m":
                action_type = "MODIFY"
            case _:
                print("Invalid input. Please enter (L)ogin, (R)egister, (M)odify, or (Q)uit.")
                continue

        # Prompt for username and password
        username = input("Enter username: ")
        password = input("Enter password: ")

        if action_type == "MODIFY":
            # First, verify the login before allowing modify actions
            login_message = f"LOGIN:{username}:{password}"
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # Connect to the server
                client_socket.connect((host, port))
                print(f"Connected to server on {host}:{port}")

                # Send login request to the server
                client_socket.send(login_message.encode())

                # Receive response from the server
                response = client_socket.recv(1024).decode()
                print(f"Server response: {response}")

                if response != "Authentication successful!":
                    print("Disconnected from server.\n")
                    client_socket.close()
                    continue

            except ConnectionError:
                print("Failed to connect to the server. Please check if the server is running.")
                continue
            finally:
                # Close the socket after login check
                client_socket.close()

            # Now, proceed with asking for change or delete action
            while True:
                modify_action = input(
                    "Type (C)hange to change your username/password, (D)elete to delete your account, or (B)ack to return: "
                ).strip().lower()

                if modify_action in ("change", "c"):
                    new_username = input("Enter new username (or press Enter to keep current): ").strip()
                    new_password = input("Enter new password (or press Enter to keep current): ").strip()
                    # Send message to server for modification
                    message = f"MODIFY:change:{username}:{password}:{new_username or ''}:{new_password or ''}"

                elif modify_action in ("delete", "d"):
                    message = f"MODIFY:delete:{username}:{password}"

                elif modify_action in("back", "b"):
                    print("Disconnected from server.\n")
                    client_socket.close()
                    break

                else:
                    print("Invalid modify action. Please enter '(C)hange', '(D)elete', or '(B)ack'.")
                    continue

                # Send the modify request to the server
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Connect to the server
                    client_socket.connect((host, port))
                    print(f"Connected to server on {host}:{port}")

                    # Send message to the server
                    client_socket.send(message.encode())

                    # Receive response from the server
                    response = client_socket.recv(1024).decode()
                    print(f"Server response: {response}")

                except ConnectionError:
                    print("Failed to connect to the server. Please check if the server is running.")
                finally:
                    # Close the socket after action
                    print("Disconnected from server.\n")
                    client_socket.close()

        else:
            # Standard message format for login and register
            message = f"{action_type}:{username}:{password}"

            # Create the socket for each new connection
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # Connect to the server
                client_socket.connect((host, port))
                print(f"Connected to server on {host}:{port}")

                # Send message to the server
                client_socket.send(message.encode())

                # Receive response from the server
                response = client_socket.recv(1024).decode()
                print(f"Server response: {response}")

            except ConnectionError:
                print("Failed to connect to the server. Please check if the server is running.")
            finally:
                # Close the socket
                client_socket.close()
                print("Disconnected from server.\n")

if __name__ == "__main__":
    start_client()

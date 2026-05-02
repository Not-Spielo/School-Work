import socket
import threading

# Global flag to control listener thread
messageListener = False

def listen_for_messages(client_socket):
    # Continuously listen for incoming messages from the server
    global messageListener
    while messageListener:
        try:
            # Receive and print messages from the server
            message = client_socket.recv(1024).decode()
            if message:
                print(f"\n{message}")
            else:
                break
        except ConnectionAbortedError:
            break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def start_client():
    global messageListener
    host = '127.0.0.1'
    port = 6969

    while True:
        # Prompt user for initial action
        action = input("Type (L)ogin to log in, (R)egister to register, (M)odify to modify your account, or (Q)uit: ").strip().lower()

        if action in {"quit", "q", "exit"}:
            print("Closing client. Goodbye!")
            break
        elif action in {"login", "l"}:
            action_type = "LOGIN"
        elif action in {"register", "r"}:
            action_type = "REGISTER"
        elif action in {"modify", "m"}:
            action_type = "MODIFY"
        else:
            print("Invalid input. Please enter (L)ogin, (R)egister, (M)odify, or (Q)uit.")
            continue

        # Prompt for username and password
        username = input("Enter username: ")
        password = input("Enter password: ")

        # Create a new socket and connect to the server for login, registration, or modify
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print(f"Connected to server on {host}:{port}")

        # Handle REGISTER, LOGIN, and MODIFY separately
        if action_type == "REGISTER":
            message = f"REGISTER:{username}:{password}"
            client_socket.send(message.encode())
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")
            client_socket.close()
        
        elif action_type == "LOGIN":
            # Send LOGIN request
            message = f"LOGIN:{username}:{password}"
            client_socket.send(message.encode())
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")

            # If login is successful, enter logged-in mode
            if response == "Authentication successful!":
                messageListener = True

                # Start a thread to listen for incoming messages
                listener_thread = threading.Thread(target=listen_for_messages, args=(client_socket,))
                listener_thread.daemon = True
                listener_thread.start()

                while messageListener:
                    print("Listening for messages...\n")
                    logged_in_action = input("Type (M)essage to send a message, or (L)ogout: ").strip().lower()

                    if logged_in_action in {"logout", "l"}:
                        client_socket.send("LOGOUT".encode())
                        response = client_socket.recv(1024).decode()
                        print(f"Server response: {response}")
                        messageListener = False  # Set flag to stop listener

                        # Close the socket after logout
                        client_socket.close()
                        break

                    elif logged_in_action in {"message", "m"}:
                        recipient = input("Enter the recipient's username: ").strip()
                        message_content = input("Enter your message: ").strip()
                        message = f"MESSAGE:{recipient}:{message_content}"
                        client_socket.send(message.encode())

                    else:
                        print("Invalid input. Please enter (M)essage or (L)ogout")

                print("Disconnected from server.\n")

            else:
                # Close the socket if login was unsuccessful
                client_socket.close()

        elif action_type == "MODIFY":
            # Verify the user credentials before allowing modifications
            login_message = f"LOGIN:{username}:{password}"
            client_socket.send(login_message.encode())
            response = client_socket.recv(1024).decode()
            print(f"Server response: {response}")

            if response == "Authentication successful!":
                # Modify account options
                while True:
                    modify_action = input("Type (C)hange to change your username/password, (D)elete to delete your account, or (B)ack to return: ").strip().lower()

                    if modify_action in {"change", "c"}:
                        new_username = input("Enter new username (or press Enter to keep current): ").strip()
                        new_password = input("Enter new password (or press Enter to keep current): ").strip()
                        modify_message = f"MODIFY:change:{username}:{password}:{new_username or ''}:{new_password or ''}"
                        client_socket.send(modify_message.encode())
                        response = client_socket.recv(1024).decode()
                        print(f"Server response: {response}")

                        if "Modification successful" in response:
                            username = new_username or username
                            password = new_password or password

                    elif modify_action in {"delete", "d"}:
                        modify_message = f"MODIFY:delete:{username}:{password}"
                        client_socket.send(modify_message.encode())
                        response = client_socket.recv(1024).decode()
                        print(f"Server response: {response}")
                        
                        if "Account deletion successful" in response:
                            client_socket.close()
                            break

                    elif modify_action in {"back", "b"}:
                        break
                    else:
                        print("Invalid modify action. Please enter '(C)hange', '(D)elete', or '(B)ack'.")

            client_socket.close()

if __name__ == "__main__":
    start_client()
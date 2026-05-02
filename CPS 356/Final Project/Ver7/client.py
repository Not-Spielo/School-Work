#client.py
import socket
import threading
import os
import json

# Global flag to control listener thread
messageListener = False
prompt_text = ""  # Global variable for managing prompt display
message_history = []  # To keep a history of messages and actions
awaiting_response = False

def clear_prompt():
    """Clears and refreshes the prompt line with the latest message history and prompt text."""
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the console
    # Print all message history
    for msg in message_history:
        print(msg)
    # Print the current prompt line
    print(f"\n{prompt_text}", end="")

def listen_for_messages(client_socket, stop_event):
    """Continuously listen for incoming messages from the server."""
    global messageListener
    while messageListener:
        try:
            message_packet = client_socket.recv(1024).decode()
            if message_packet:
                message_packet = json.loads(message_packet)
                sender = message_packet['sender']
                message = message_packet['message']
                message_history.append(f"{sender}: {message}")  # Add server message to history
                clear_prompt()  # Refresh display
            else:
                break
        except ConnectionAbortedError:
            break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

#Gets username and password, checks for back or blank
def getUserPassword():
    global prompt_text
    prompt_text = "Enter username (or type (B)ack to return): "
    clear_prompt()
    username = input().strip()
    if username.lower() == "b" or username == "" or username == "back":
        message_history.append("Going back to previous menu")
        clear_prompt()
        return None, None
    else:
        message_history.append(f"Enter username (or type (B)ack to return): {username}")
        clear_prompt()
    
    prompt_text = "Enter password (or type (B)ack to return): "
    clear_prompt()
    password = input().strip()
    if password.lower() == "b" or username == "" or username == "back":
        message_history.append("Going back to previous menu")
        clear_prompt()
        return None, None
    else:
        message_history.append(f"Enter password: {'*' * len(password)}")
        clear_prompt()
    return username, password

def start_client():
    global messageListener, prompt_text, awaiting_response
    host = '127.0.0.1'
    port = 6969

    while True:
        # Set the initial prompt text
        prompt_text = "Type (L)ogin to log in, (R)egister to register, (M)odify to modify your account, or (Q)uit: "
        clear_prompt()
        action = input().strip().lower()
        message_history.append(f"\n{prompt_text}{action}")
        clear_prompt()  # Refresh after capturing input

        if action in {"quit", "q", "exit"}:
            prompt_text = "Closing client. Goodbye!"
            clear_prompt()
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
        
        username, password = getUserPassword()
        if username is None:
            continue
        
        stop_event = threading.Event()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print(f"Connected to server on {host}:{port}")

        if action_type == "REGISTER":
            if username and password:
                message = {
                    "action": "register",
                    "username": username,
                    "password": password
                }
                message = json.dumps(message)
                client_socket.send(message.encode())
                response = client_socket.recv(1024).decode()
                response = json.loads(response)
                if response["status"] == "failure":
                    message = response["message"]
                else:
                    message = "Successfully logged in user"
                message_history.append(f"Server response: {message}") 
            client_socket.close()
            clear_prompt()
        
        elif action_type == "LOGIN":
            if username and password:
                message = {
                    "action": "login",
                    "username": username,
                    "password": password
                }
                message = json.dumps(message)
                client_socket.send(message.encode())
                response = client_socket.recv(1024).decode()
                response = json.loads(response)
                if response["status"] == "failure":
                    message = response["message"]
                else:
                    message = "Successfully logged in user"
                message_history.append(f"Server response: {message}")
                clear_prompt()
    
                if response["status"] == "success":
                    message_history.append("Listening for messages...")
                    messageListener = True
    
                    listener_thread = threading.Thread(target=listen_for_messages, args=(client_socket, stop_event))
                    listener_thread.daemon = True
                    listener_thread.start()
    
                    while messageListener:
                        prompt_text = "Type (M)essage to send a message, or (L)ogout: "
                        clear_prompt()
                        logged_in_action = input().strip().lower()
                        message_history.append(f"{prompt_text}{logged_in_action}")
                        clear_prompt()

                        if logged_in_action in {"message", "m"}:
                            # Update prompt for recipient entry
                            prompt_text = "Enter the recipient's username: "
                            clear_prompt()
                            recipient = input().strip()
                            message_history.append(f"{prompt_text}{recipient}")
                            clear_prompt()
    
                            # Update prompt for message content entry
                            prompt_text = "Enter your message: "
                            clear_prompt()
                            message_content = input().strip()
                            message = {
                                "action": "message",
                                "recipient": recipient,
                                "message": message_content
                            }
                            message = json.dumps(message)
                            client_socket.send(message.encode())
                            clear_prompt()

                        elif logged_in_action in {"logout", "l"}:
                            logout_message = {
                                "action": "logout"
                            }
                            logout_message = json.dumps(logout_message)
                            client_socket.send(logout_message.encode())
                            message = "Logged out user"
                            message_history.append(f"{message}")
                            client_socket.close()
                            messageListener = False
                            break
                        else:
                            message_history.append("Invalid input. Please enter (M)essage or (L)ogout.")
                            clear_prompt()
                        
    
                    message_history.append("Disconnected from server.\n")
                    #clear_prompt()
    
                else:
                    client_socket.close()

        elif action_type == "MODIFY":
            if username and password:
                login_message = {
                    "action": "login",
                    "username": username,
                    "password": password
                }
                login_message = json.dumps(login_message)
                client_socket.send(login_message.encode())
                response = client_socket.recv(1024).decode()
                response = json.loads(response)
                if response["status"] == "failure":
                    message = response["message"]
                else:
                    message = "Successfully logged in user"
                message_history.append(f"Server response: {message}")
                clear_prompt()
    
                if response['status'] == "success":
                    while True:
                        prompt_text = "Type (C)hange to change your username/password, (D)elete to delete your account, or (B)ack to return: "
                        clear_prompt()
                        modify_action = input().strip().lower()
                        message_history.append(f"\n{prompt_text}{modify_action}")
                        clear_prompt()
    
                        if modify_action in {"change", "c"}:
                            new_username = input("Enter new username (or press Enter to keep current): ").strip()
                            message_history.append(f"Enter new username (or press Enter to keep current): {new_username}")
                            new_password = input("Enter new password (or press Enter to keep current): ").strip()
                            message_history.append(f"Enter new password (or press Enter to keep current): {'*' * len(new_password)}")
                            modify_message = {
                                "action": "modify",
                                "modify_action": "change",
                                "username": username,
                                "password": password,
                                "optional_params": {
                                    "new_username": new_username or "",
                                    "new_password": new_password or ""
                                }
                            }
                            modify_message = json.dumps(modify_message)
                            client_socket.send(modify_message.encode())
                            response = client_socket.recv(1024).decode()
                            response = json.loads(response)
                            if response["status"] == "failure":
                                message = response["message"]
                            else:
                                message = "Successfully changed user"
                            message_history.append(f"Server response: {message}")
                            clear_prompt()
    
                            if response['status'] == "success":
                                username = new_username or username
                                password = new_password or password
    
                        elif modify_action in {"delete", "d"}:
                            modify_message = {
                                "action": "modify",
                                "modify_action": "delete",
                                "username": username,
                                "password": password,
                                "optional_params": {}
                            }
                            modify_message = json.dumps(modify_message)
                            client_socket.send(modify_message.encode())
                            response = client_socket.recv(1024).decode()
                            response = json.loads(response)
                            if response["status"] == "failure":
                                message = response["message"]
                            else:
                                message = "Successfully deleted user"
                            message_history.append(f"Server response: {message}")
                            clear_prompt()
                            if "Account deletion successful" in response:
                                client_socket.close()
                                break
    
                        elif modify_action in {"back", "b"}:
                            break
                        else:
                            message_history.append("Invalid modify action. Please enter '(C)hange', '(D)elete', or '(B)ack'.")
                            clear_prompt()
    
                client_socket.close()

if __name__ == "__main__":
    start_client()

import socket
import threading
import sys
import time

#dictionary mapping client sockets to usernames. for commands that don't explicitly use username as argument
socket_to_username = {}

def handle_join_command(client_socket, username):
    #check if no username was supplied
    if not username:
        return "Username cannot be empty. Please provide a valid username."

    #check if the client is already registered
    if client_socket in socket_to_username:
        return "You are already registered."

    #check if the username is already taken
    if username in socket_to_username.values():
        return "Username already taken. Please choose a different username."

    #register the client
    if len(socket_to_username) < 10:
        socket_to_username[client_socket] = username
        print(f"{username} Joined the Chatroom")

        #notify other clients that a new user has joined
        join_notification = f"{username} joined!"
        for sock in socket_to_username.keys():  #iterate over the sockets
            if sock != client_socket:  #don't send to the user who just joined
                sock.send(join_notification.encode('utf-8'))

        return f"{username} joined! Connected to server!"
    else:
        return "Too Many Users"

#LIST command handler
def handle_list_command(client_socket):
    #check if the user is registered
    if client_socket not in socket_to_username:
        return "Unregistered User: Please JOIN the service to use LIST."

    #create a list of registered usernames with each username on a separate line
    user_list = "\n".join(socket_to_username.values())

    return user_list

#MESG command handler
def handle_mesg_command(sender_socket, recipient_username, message):
    #retrieve the sender's username from the socket
    sender_username = socket_to_username.get(sender_socket)

    #check if the sender is registered
    if sender_username is None:
        return "Unregistered User. Please JOIN the service to use MESG."

    #check if the recipient is registered
    if recipient_username not in socket_to_username.values():
        #inform the sender that the recipient is unregistered
        return "Unknown Recipient"

    #find the recipient's socket
    recipient_socket = next((sock for sock, uname in socket_to_username.items() if uname == recipient_username), None)
    
    if recipient_socket is None:
        #this should not happen as we already checked if recipient_username is in values, but just in case
        return "Unknown Recipient"

    #send the message to the recipient
    message_to_send = f"{sender_username}: {message}"
    recipient_socket.send(message_to_send.encode("utf-8"))

    #no output on success
    return ""

#BCST command handler
def handle_bcst_command(sender_socket, message):
    #retrieve the sender's username from the socket
    sender_username = socket_to_username.get(sender_socket)

    #check if the sender is registered
    if sender_username is None:
        return "Unregistered User. Please JOIN the service to use BCST."

    #relay the message to all registered clients (except the sender)
    for sock, username in socket_to_username.items():
        if sock != sender_socket:
            message_to_send = f"{sender_username}: {message}"
            sock.send(message_to_send.encode("utf-8"))

    #send a status message back to the sender
    return f"{sender_username} is sending a broadcast"

#QUIT command handler
def handle_quit_command(client_socket):
    #check if the client is registered and get the username
    username = socket_to_username.get(client_socket)

    if username is not None:
        quit_message = f"{username} is quitting the chat server"
        #send quit confirmation to the quitting client
        client_socket.send(quit_message.encode('utf-8'))

        #short pause to ensure the message is sent
        time.sleep(0.5)        
        
        #notify other clients that this user is quitting
        quit_notification = f"{username} left"
        for sock in socket_to_username:
            if sock != client_socket:
                sock.send(quit_notification.encode('utf-8'))
        
        #remove the client from the socket_to_username dictionary
        socket_to_username.pop(client_socket)

    #close the client's socket
    client_socket.close()

def handle_client(client_socket):
    try:
        while True:
            #receive a message from the client
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break  #client has disconnected

            #split the message to identify the command and its arguments
            command_parts = message.split(' ', 1)  # Splitting only on the first space
            command = command_parts[0]

            #basic command handling
            if command == "JOIN":
                response = handle_join_command(client_socket, command_parts[1] if len(command_parts) > 1 else "")
            elif command == "LIST":
                #if there are other arguments after LIST command
                if len(command_parts) > 1:
                    response = "Invalid LIST command format"
                #call list handler
                else:
                    response = handle_list_command(client_socket)
            elif command == "MESG":
                #extract recipient_username and message from command_parts
                if len(command_parts) > 1:
                    args = command_parts[1].split(' ', 1)
                    if len(args) == 2:
                        recipient_username, message = args
                        response = handle_mesg_command(client_socket, recipient_username, message)
                    #expected to yeild esactly two parts
                    else:
                        response = "Invalid MESG command format."
                #if arguments not exactly 2
                else:
                    response = "Invalid MESG command format."
            elif command == "BCST":
                #extract the message from command_parts
                if len(command_parts) > 1:
                    message = command_parts[1]
                    response = handle_bcst_command(client_socket, message)
                else:
                    response = "Invalid BCST command format."
            elif command == "QUIT":
                handle_quit_command(client_socket)
                break  #exit the loop to end handling this client
            else:
                response = "Unknown Message"

            #send the response back to the client, except for QUIT command
            if command != "QUIT":
                client_socket.send(response.encode('utf-8'))

    except ConnectionResetError:
        print("Client disconnected unexpectedly")
    finally:
        client_socket.close()

def main():
    #check if the correct number of command-line arguments are provided
    if len(sys.argv) != 2:
        print("Usage: python3 server.py <svr_port>")
        sys.exit(1)

    #convert the command line argument to an integer for the port number
    port = int(sys.argv[1])

    #create a socket object using TCP (SOCK_STREAM) on the INET domain
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #bind the socket to an address and port
    # '' means the socket is reachable by any address the machine happens to have
    server.bind(('', port))

    #set the socket to listen for incoming connections, with a specified backlog
    server.listen(5)  # 5 is the number of unaccepted connections before refusing new ones
    print(f"Server listening on port {port}")
    
    #indicate that the chat server has started
    print("The Chat Server Started")

    try:
        while True:
            #accept an incoming connection; this is a blocking call
            client, address = server.accept()
            print(f"Connected with {address}")

            #spawning a new thread for each connected client
            client_thread = threading.Thread(target=handle_client, args=(client,))
            client_thread.start()
    except KeyboardInterrupt:
        #graceful shutdown on keyboard interrupt (Ctrl+C)
        print("Server shutting down.")
    finally:
        #ensure the socket is closed on exit
        server.close()

if __name__ == "__main__":
    main()

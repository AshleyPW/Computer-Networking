import socket
import sys
import threading

def listen_for_messages(sock):
    while True:
        message = sock.recv(1024).decode('utf-8')
        if message:
            print(message)
            #check for a special message to break the loop, if necessary
            if message == "SPECIAL_EXIT_MESSAGE":
                break

def main(server_host, server_port):
    #create a socket object using TCP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #connect to the server
    try:
        client_socket.connect((server_host, server_port))
    except ConnectionError as e:
        print(f"Unable to connect to the server: {e}")
        sys.exit(1)

    #start the thread to listen for messages
    threading.Thread(target=listen_for_messages, args=(client_socket,), daemon=True).start()

    #prompt user to issue JOIN command
    join_command = input("Enter JOIN followed by your username: ")
    client_socket.send(join_command.encode('utf-8'))

    #main loop to send commands to the server
    while True:
        #prompt for the next command
        message = input("")

        #send the message to the server
        client_socket.send(message.encode('utf-8'))

        if message.strip().upper() == "QUIT":
            #wait for server's final response before exiting
            final_response = client_socket.recv(1024).decode('utf-8')
            print(final_response)
            break  #break out of the loop after receiving the final response

    #close the socket
    client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 client.py <server_host> <server_port>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    main(host, port)

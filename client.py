import os
import pathlib
import selectors
import socket
import sys
import time

# Innitial info
host, port = "127.0.0.1", 65432  # default host, port
keep_running = True
sent_file_info = False
my_file = None
total_sent = 0
my_sel = selectors.DefaultSelector()

# Checking command-line arguments passed to the script
if len(sys.argv) == 3:
    host, port = sys.argv[1], int(sys.argv[2])
elif len(sys.argv) == 1:
    if not host and not port:
        print("No default host and port in script.")
        sys.exit(1)
else:
    print("Usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

# Creating a socket and connecting to a server
sock = socket.socket()
print(f"Connecting to server: {host, port}")
sock.connect((host, port))
sock.setblocking(False)

# Setting up events and registering connection
events = selectors.EVENT_READ | selectors.EVENT_WRITE
my_sel.register(sock, events)
my_sel.modify(sock, selectors.EVENT_READ)

# Handles user inputed file validation and file reading
def file_handler():
    def check_f_input():
        user_input = input("Provide filename: ")
        script_dir = os.path.dirname(__file__)
        if pathlib.Path(user_input).exists():
            return user_input
        else:
            joined_f_path = os.path.join(script_dir, user_input)
            if pathlib.Path(joined_f_path).exists():
                return joined_f_path
            else:
                print("File does not exists.")
                new_input = check_f_input()
                return new_input

    user_f = check_f_input()
    f_size = os.path.getsize(user_f)
    f_name = os.path.basename(user_f)
    with open(user_f, "rb") as f:
        my_file = f.read()
    return str(f_size) + "|" + f_name, my_file


# Creates progress bar with file info
def create_progress_bar(f_name, f_size, total_sent):
    n_bar = 10
    progr_r = total_sent / f_size
    progress_bar = f"Sending {f_name}: [{'=' * int(n_bar * progr_r):{n_bar}s}] {int(100 * progr_r)}%"
    return progress_bar


# Custom input function with validation
def custom_user_input(msg, valid_inputs):
    user_input = input(msg)
    if user_input in valid_inputs:
        return user_input
    else:
        print(f"Wrong input. Valid inputs: {valid_inputs}")
        new_user_input = custom_user_input(msg, valid_inputs)
        return new_user_input


while keep_running:
    for key, mask in my_sel.select(timeout=1):
        conn = key.fileobj
        client_addr = conn.getpeername()

        # Reading(receiving) information from server
        if mask & selectors.EVENT_READ:
            data = conn.recv(1024)
            if data:
                decoded_data = data.decode("utf-16")
                if decoded_data == "yc":
                    print("Server accepted connection.")
                    my_sel.modify(sock, selectors.EVENT_WRITE)
                elif decoded_data == "nc":
                    print("Server declined connection.")
                    keep_running = False
                elif decoded_data == "yf":
                    print("Server accepted to receive a file.")
                    my_sel.modify(sock, selectors.EVENT_WRITE)
                elif decoded_data == "nf":
                    print("Server declined to receive a file.")
                    user_action = custom_user_input(
                        "Would you like to exit(e) or try(t) again? ", ["e", "t"]
                    )
                    if user_action == "e":
                        keep_running = False
                    elif user_action == "t":
                        sent_file_info = False
                        my_file = None
                        my_sel.modify(sock, selectors.EVENT_WRITE)

        # Writing(sending) information to server
        if mask & selectors.EVENT_WRITE:
            # Checking if the file information
            # is sent and file is opened.
            if not sent_file_info and not my_file:
                file_info, my_file = file_handler()
                # Extracting filename and file size information
                f_name = file_info.split("|")[-1]
                f_size = int(file_info.split("|")[0])
                print("Sending file info to server.")
                while file_info:
                    sent = sock.send(file_info.encode("utf-16"))
                    file_info = file_info[sent:]
                sent_file_info = True
                # Switching event to read because we need to
                # know if the server will accept or decline a file.
                my_sel.modify(sock, selectors.EVENT_READ)
            else:
                if my_file:
                    # Sending a file to a server
                    sent = sock.send(my_file)
                    total_sent += sent
                    my_file = my_file[sent:]
                    progress_bar = create_progress_bar(f_name, f_size, total_sent)
                    sys.stdout.write("\r")
                    sys.stdout.write(progress_bar)
                    sys.stdout.flush()
                else:
                    print("\nFile have been sent.")
                    # Setting up default values
                    total_sent = 0
                    sent_file_info = False
                    # Deciding what to do next
                    conn_close_q = custom_user_input(
                        "Would you like to close connection(y/n)? ", ["y", "n"]
                    )
                    if conn_close_q == "y":
                        keep_running = False
                    elif conn_close_q == "n":
                        continue
                        # file_info, my_file = file_handler()
                        # f_name = file_info.split("|")[-1]
                        # f_size = int(file_info.split("|")[0])

print("Shutting down")
my_sel.unregister(conn)
conn.close()
my_sel.close()

import os
import selectors
import socket
import sys
import types

# innitial info
host, port = "127.0.0.1", 65432  # default host, port
script_dir = os.path.dirname(os.path.realpath(__file__))
my_sel = selectors.DefaultSelector()
keep_running = True
total_conn = 0
f_keep_a = True
progress_dict = {}


# Validation of user y/n input
def check_y_n_input(msg=None, arg=None):
    if msg:
        user_input = input(msg).lower()
    else:
        user_input = arg
    valid_inputs = ["y", "n"]
    invalid_y_n_msg = f"Wrong input. Valid inputs: {valid_inputs}"
    if user_input.split()[0] in valid_inputs:
        return user_input
    else:
        print(invalid_y_n_msg)
        new_input = check_f_acpt_input()
        return new_input


# Validation of y/n answer and/or path input
def check_f_acpt_input(filename=None):
    user_input = input(f"Would you like to accept file '{filename}'(y/n)? ").lower()
    invalid_path_msg = "Invalid input. Your specified file path does not exists"
    invalid_args_msg = "Invalid input. Example of valid input: y /home/user/Desktop/"
    s_user_input = user_input.split()

    y_n = check_y_n_input(arg=s_user_input[0])
    if len(s_user_input) == 1:
        return y_n
    elif len(s_user_input) == 2:
        f_save_path = s_user_input[-1]
        valid_path = os.path.exists(f_save_path)
        if not valid_path:
            print(invalid_path_msg)
            new_input = check_f_acpt_input()
            return new_input
        else:
            return y_n, f_save_path
    else:
        print(invalid_args_msg)
        new_input = check_f_acpt_input()
        return new_input


# Checking if the filename exists in specified dir
# and creating a new (or leaving the same) filename
def create_filename(filename, file_path):
    all_files = os.listdir(file_path)
    if filename in all_files:
        i = 0
        while True:
            if "." in filename:
                dot_pos = filename.rfind(".")
                new_filename = filename[:dot_pos] + "_" + str(i) + filename[dot_pos:]
            else:
                new_filename = filename + "_" + str(i)
            if new_filename in all_files:
                i += 1
            else:
                return new_filename
    else:
        return filename


# Creates progress bar with file info
def create_progress_bar(f_name, f_size, total_recv):
    n_bar = 10
    progr_r = total_recv / int(f_size)
    progress_bar = f"Receiving {f_name}: [{'=' * int(n_bar * progr_r):{n_bar}s}] {int(100 * progr_r)}%"
    return progress_bar


# Receiving and saving data
def read(key, mask):
    global keep_running
    global total_conn
    global progress_dict

    conn = key.fileobj
    conn_data = key.data
    client_address = conn.getpeername()
    data = conn.recv(1024)
    if data:
        # Accepting/declining incoming file
        if conn_data.f_keep_a:
            conn_data.f_size, conn_data.f_name = data.decode("utf-16").split("|")
            user_input = check_f_acpt_input(filename=conn_data.f_name)
            sys.stdout.write("\x1b[1A\x1b[2K")
            f_acc_q = user_input[0]
            if len(user_input) == 2:
                conn_data.f_save_path = user_input[-1]
            if f_acc_q == "y":
                # Sending a positive answer to client
                conn.send("yf".encode("utf-16"))
                conn_data.f_keep_a = False
            elif f_acc_q == "n":
                # Sending a negative answer to client
                conn.send("nf".encode("utf-16"))

            conn_data.f_name = create_filename(conn_data.f_name, conn_data.f_save_path)
        else:
            # Saving file
            with open(os.path.join(conn_data.f_save_path, conn_data.f_name), "ab") as f:
                f.write(data)
            # Getting file size
            saved_f_size = os.path.getsize(
                os.path.join(conn_data.f_save_path, conn_data.f_name)
            )
            # Creating progress bar
            progress_bar = create_progress_bar(
                conn_data.f_name, conn_data.f_size, saved_f_size
            )
            # Iterating over all progress bars, moving up cursor
            # and deleting whole line
            for _ in range(len(progress_dict)):
                sys.stdout.write("\x1b[1A\x1b[2K")
            # Adding/replacing current progress bar to progress dict
            progress_dict[conn_data.id] = progress_bar
            # Iterating over all progress bars and printing it
            for key, val in progress_dict.items():
                sys.stdout.write(val + "\n")

            if saved_f_size == int(conn_data.f_size):
                for _ in range(len(progress_dict)):
                    sys.stdout.write("\x1b[1A\x1b[2K")
                # Printing downloaded file progress bar last time
                # before deleting from progress dict
                sys.stdout.write(progress_dict[conn_data.id] + "\n")
                # Deleting downloaded file progress bar
                del progress_dict[conn_data.id]
                for key, val in progress_dict.items():
                    sys.stdout.write(val + "\n")
                # print("Finished")
                # Setting up default values
                conn_data.f_keep_a = True
                conn_data.f_name = None
                conn_data.f_size = None
                conn_data.f_save_path = script_dir
    else:
        # conn_data.f_keep_a = True
        # Closing connection
        print(f"Closing connection: {client_address}")
        my_sel.unregister(conn)
        conn.close()
        total_conn -= 1
        if total_conn == 0:
            conn_close_msg = "There are no active connections left. Would you like to close server(y/n)? "
            conn_close_q = check_y_n_input(msg=conn_close_msg)
            if conn_close_q == "y":
                keep_running = False


# Accepting new connections
def accept(sock):
    global total_conn
    # Accepting new connection
    new_conn, addr = sock.accept()
    conn_acpt_msg = f"Would you like to accept connection from {addr}(y/n)? "
    conn_acpt = check_y_n_input(msg=conn_acpt_msg)
    if conn_acpt == "y":
        # Sending a positive answer to client
        new_conn.send("yc".encode("utf-16"))
        print(f"Accepted new connection: {addr}")
        new_conn.setblocking(False)
        total_conn += 1
        # Setting up default data for every connection
        data = types.SimpleNamespace(
            f_keep_a=True,
            f_name=None,
            f_size=None,
            f_save_path=script_dir,
            id=total_conn,
        )
        my_sel.register(new_conn, selectors.EVENT_READ, data=data)
    elif conn_acpt == "n":
        # Sending a negative answer to client
        new_conn.send("nc".encode("utf-16"))
        print(f"Declined connection: {addr}")
        # Closing connection
        new_conn.close()


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

# Starting up a server
print(f"Starting up multiconn server on host: {host}, port: {port}")
server = socket.socket()
server.setblocking(False)
server.bind((host, port))
server.listen()

my_sel.register(server, selectors.EVENT_READ, data=None)


def main():
    while keep_running:
        events = my_sel.select(timeout=1)
        for key, mask in events:
            if key.data is None:
                accept(key.fileobj)
            else:
                read(key, mask)

    print("Shutting down!")
    my_sel.close()


if __name__ == "__main__":
    main()

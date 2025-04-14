#!/usr/bin/env python3

import socket
import threading
import sys
import os
import time
import logging
import argparse
try:
    import paramiko
    from paramiko.py3compat import decodebytes
except ImportError:
    print("Error: Paramiko library not found.")
    print("Please install it using: pip install paramiko cryptography")
    sys.exit(1)

# --- Configuration ---
DEFAULT_PORT = 2222
DEFAULT_HOST = '0.0.0.0'
HOST_KEY_FILE = 'host_key.pem'
KEY_BITS = 2048 # Strength for generated RSA key
LOG_LEVEL = logging.INFO
MAX_USERNAME_LEN = 16
ENCODING = 'utf-8'

# --- ANSI Color Codes ---
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"

# --- Global State ---
clients = {}  # {channel: {'name': username, 'addr': address}}
client_lock = threading.Lock() # To protect access to the clients dictionary

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def generate_or_load_host_key():
    """Generates an RSA host key if it doesn't exist, otherwise loads it."""
    if os.path.exists(HOST_KEY_FILE):
        logging.info(f"Loading host key from {HOST_KEY_FILE}")
        try:
            host_key = paramiko.RSAKey.from_private_key_file(HOST_KEY_FILE)
            return host_key
        except paramiko.PasswordRequiredException:
            logging.error(f"Host key {HOST_KEY_FILE} is encrypted and password protected. "
                          "Please use an unencrypted key or remove it to regenerate.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to load host key {HOST_KEY_FILE}: {e}")
            sys.exit(1)
    else:
        logging.info(f"No host key found. Generating new RSA key ({KEY_BITS} bits)...")
        try:
            host_key = paramiko.RSAKey.generate(KEY_BITS)
            host_key.write_private_key_file(HOST_KEY_FILE)
            logging.info(f"New host key saved to {HOST_KEY_FILE}")
            return host_key
        except Exception as e:
            logging.error(f"Failed to generate or save host key: {e}")
            sys.exit(1)

def broadcast(message, sender_channel=None):
    """Sends a message to all connected clients, optionally excluding the sender."""
    with client_lock:
        # Create a list of channels to iterate over to avoid issues if clients disconnect during broadcast
        receivers = list(clients.keys())
        for channel in receivers:
            if channel != sender_channel and channel in clients: # Check if still connected
                try:
                    channel.sendall(message.encode(ENCODING))
                except Exception as e:
                    logging.warning(f"Failed to send message to {clients.get(channel, {}).get('name', 'Unknown')}: {e}")
                    # Consider removing the client here if the error is persistent (e.g., broken pipe)
                    # but the main loop should handle disconnection more robustly.

def format_message(username, message, color=COLOR_CYAN):
    """Formats a user message with timestamp and color."""
    timestamp = time.strftime("%H:%M:%S")
    return f"{COLOR_YELLOW}[{timestamp}]{COLOR_RESET} {color}{COLOR_BOLD}{username}{COLOR_RESET}: {message}\n"

def format_system_message(message, color=COLOR_GREEN):
    """Formats a system message."""
    timestamp = time.strftime("%H:%M:%S")
    return f"{COLOR_YELLOW}[{timestamp}]{COLOR_RESET} {color}*** {message} ***{COLOR_RESET}\n"

# --- Paramiko Server Interface ---
class ChatServerInterface(paramiko.ServerInterface):
    """Handles SSH authentication (allows none/password) and channel requests."""
    def __init__(self):
        self.event = threading.Event() # Used to signal channel open

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_none(self, username):
        # Allow connection without authentication initially
        # We'll ask for the name after the channel is established
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
       # Allow connection via password (but don't actually check it)
       # We'll ask for the name after the channel is established
       return paramiko.AUTH_SUCCESSFUL

    # You might want to implement check_auth_publickey if you need key-based auth
    # def check_auth_publickey(self, username, key):
    #     return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        # Allow both 'none' and 'password' methods
        return "none,password"


# --- Client Handler Thread ---
def handle_client(client_socket, addr, host_key):
    """Handles a single client connection in a separate thread."""
    logging.info(f"Incoming connection from {addr}")
    transport = None
    channel = None
    username = None

    try:
        # Setup Paramiko transport
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)

        # Start SSH server session
        server_interface = ChatServerInterface()
        transport.start_server(server=server_interface)

        # Wait for a channel to open (e.g., 'session')
        channel = transport.accept(20) # Timeout after 20 seconds
        if channel is None:
            logging.warning(f"No channel requested from {addr}. Closing connection.")
            return

        # --- Get Username ---
        channel.sendall(f"\n{COLOR_BOLD}{COLOR_MAGENTA}Welcome to the SSH Chatroom!{COLOR_RESET}\n".encode(ENCODING))
        channel.sendall(f"{COLOR_YELLOW}Please enter your desired username:{COLOR_RESET} ".encode(ENCODING))
        raw_username = b''
        while True:
            try:
                byte = channel.recv(1)
                if not byte or byte in (b'\r', b'\n'):
                    break
                if len(raw_username) < MAX_USERNAME_LEN:
                     # Basic backspace handling (might not work on all terminals)
                    if byte == b'\x7f' or byte == b'\x08':
                        if raw_username:
                            raw_username = raw_username[:-1]
                            # Erase character on client terminal (optional)
                            channel.sendall(b'\x08 \x08')
                    else:
                        raw_username += byte
                        channel.sendall(byte) # Echo typed character
                # Else: ignore input if max length reached

            except (socket.timeout, EOFError, ConnectionResetError):
                logging.warning(f"Connection closed by {addr} during username entry.")
                return
            except Exception as e:
                logging.error(f"Error receiving username from {addr}: {e}")
                return

        username = raw_username.decode(ENCODING, errors='ignore').strip()

        if not username or username.isspace():
            username = f"User_{addr[1]}" # Default username if none provided
            channel.sendall(f"\n{COLOR_RED}No valid username entered. Using default: {username}{COLOR_RESET}\n".encode(ENCODING))
        else:
             channel.sendall(b'\n') # Move to next line after username input

        # Check for duplicate username
        with client_lock:
            existing_users = [data['name'] for data in clients.values()]
            if username in existing_users:
                 channel.sendall(f"{COLOR_RED}Username '{username}' is already taken. Please reconnect with a different name.{COLOR_RESET}\n".encode(ENCODING))
                 logging.warning(f"Duplicate username attempt '{username}' from {addr}. Disconnecting.")
                 return # Disconnect the client


        # --- Client Joined ---
        logging.info(f"User '{username}' ({addr}) joined.")
        with client_lock:
            clients[channel] = {'name': username, 'addr': addr}
            current_users = ", ".join([data['name'] for data in clients.values()])

        # Notify others and welcome the new user
        join_msg = format_system_message(f"{username} has joined the chat!")
        broadcast(join_msg, sender_channel=channel) # Notify others

        welcome_msg = f"{COLOR_GREEN}Welcome, {username}!{COLOR_RESET}\n"
        welcome_msg += format_system_message(f"Currently connected users: {current_users}", color=COLOR_BLUE)
        channel.sendall(welcome_msg.encode(ENCODING))

        # --- Main Message Loop ---
        while True:
            try:
                # Set a timeout to allow checking transport status
                channel.settimeout(1.0)
                message_bytes = b''
                try:
                    # Read byte by byte to handle line breaks better in raw SSH
                    while True:
                        byte = channel.recv(1)
                        if not byte: # Connection closed
                           raise EOFError("Connection closed by client")
                        message_bytes += byte
                        # Basic line break detection (\n or \r\n)
                        if byte == b'\n':
                            break
                        if byte == b'\r':
                            # Peek for \n
                            next_byte = channel.recv(1)
                            if next_byte == b'\n':
                                message_bytes += next_byte
                            else:
                                # Put the byte back if it wasn't \n (less common)
                                # This part is tricky and might not be perfect across all clients
                                # Often better to just treat \r as end-of-line too
                                channel.send(next_byte) # Try to send it back? Risky.
                            break

                except socket.timeout:
                    # No data received, check if transport is still active
                    if not transport.is_active():
                        logging.info(f"Transport for {username} ({addr}) is inactive.")
                        break
                    continue # Go back to recv
                except (EOFError, ConnectionResetError, paramiko.SSHException) as e:
                    logging.info(f"Connection closed for {username} ({addr}): {e}")
                    break # Exit loop on disconnection

                message = message_bytes.decode(ENCODING, errors='ignore').strip()

                if message: # Don't broadcast empty lines
                    logging.info(f"Message from {username}: {message}")
                    formatted_msg = format_message(username, message)
                    broadcast(formatted_msg, sender_channel=channel) # Send to others

            except Exception as e:
                logging.error(f"Error in client loop for {username} ({addr}): {e}")
                break # Exit loop on unexpected error

    except paramiko.SSHException as ssh_e:
        logging.warning(f"SSH negotiation failed with {addr}: {ssh_e}")
    except socket.error as sock_e:
        logging.warning(f"Socket error with {addr}: {sock_e}")
    except Exception as e:
        # Catch other potential errors during setup
        logging.error(f"Unhandled exception for connection {addr}: {e}", exc_info=True)
    finally:
        # --- Cleanup ---
        if channel:
             with client_lock:
                 if channel in clients:
                     del clients[channel]
             if username:
                 logging.info(f"User '{username}' ({addr}) disconnected.")
                 leave_msg = format_system_message(f"{username} has left the chat.", color=COLOR_RED)
                 broadcast(leave_msg) # Notify others
             try:
                 channel.close()
             except Exception:
                 pass # Ignore errors during close
        if transport:
            try:
                transport.close()
            except Exception:
                pass # Ignore errors during close
        logging.debug(f"Closed resources for {addr}")


# --- Main Server ---
def main():
    parser = argparse.ArgumentParser(description="SSH Chatroom Server")
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument('-H', '--host', type=str, default=DEFAULT_HOST,
                        help=f"Host interface to bind to (default: {DEFAULT_HOST})")
    parser.add_argument('--host-key', type=str, default=HOST_KEY_FILE,
                        help=f"Path to the SSH host key file (default: {HOST_KEY_FILE})")
    args = parser.parse_args()

    global HOST_KEY_FILE # Allow modification by command line arg
    HOST_KEY_FILE = args.host_key
    host_key = generate_or_load_host_key()

    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((args.host, args.port))
        server_socket.listen(5) # Listen for up to 5 queued connections
        logging.info(f"SSH Chat Server started on {args.host}:{args.port}")
        print(f"Server listening on {args.host}:{args.port}...")
        print("Users can connect via: ssh <any_user>@{server_ip} -p {port}")
        print("Press Ctrl+C to stop the server.")

        while True:
            try:
                client_socket, client_addr = server_socket.accept()
                # Start a new thread to handle this client
                client_thread = threading.Thread(target=handle_client,
                                                 args=(client_socket, client_addr, host_key),
                                                 daemon=True) # Daemon threads exit when main program exits
                client_thread.start()
            except socket.error as e:
                logging.error(f"Error accepting connection: {e}")
            except Exception as e:
                 logging.error(f"Unexpected error in accept loop: {e}", exc_info=True)


    except OSError as e:
        logging.error(f"Failed to bind to {args.host}:{args.port}: {e}")
        print(f"Error: Could not bind to port {args.port}. Is it already in use or do you lack permissions?")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Shutdown signal received (Ctrl+C).")
        print("\nShutting down server...")
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
    finally:
        if server_socket:
            server_socket.close()
            logging.info("Server socket closed.")
        print("Closing client connections...")
        with client_lock:
            channels_to_close = list(clients.keys()) # Create copy to avoid modification during iteration
            for channel in channels_to_close:
                try:
                    channel.sendall(format_system_message("Server is shutting down.", color=COLOR_RED).encode(ENCODING))
                    channel.close()
                except Exception:
                    pass # Ignore errors during shutdown cleanup
        print("Server shut down gracefully.")

if __name__ == "__main__":
    main()

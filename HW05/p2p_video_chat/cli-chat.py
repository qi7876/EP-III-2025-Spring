# chat_server.py
import asyncio
import random

# --- Configuration ---
HOST = "0.0.0.0"  # Listen on all available network interfaces
PORT = 8888  # Port for clients to connect to

# --- ANSI Color Codes ---
# Basic colors
RESET = "\033[0m"
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
# Bright versions
BRIGHT_BLACK = "\033[90m"  # Often appears grey
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Bold style
BOLD = "\033[1m"

# Available colors for usernames (excluding black/white/grey for visibility)
USER_COLORS = [
    RED,
    GREEN,
    YELLOW,
    BLUE,
    MAGENTA,
    CYAN,
    BRIGHT_RED,
    BRIGHT_GREEN,
    BRIGHT_YELLOW,
    BRIGHT_BLUE,
    BRIGHT_MAGENTA,
    BRIGHT_CYAN,
]

# --- Server State ---
clients = {}  # Dictionary to store connected clients: {writer: {"username": str, "color": str}}
active_usernames = set()  # Keep track of usernames currently in use


# --- Helper Functions ---
def get_random_color():
    """Selects a random color for a new user."""
    return random.choice(USER_COLORS)


async def broadcast(message, sender_writer=None):
    """Sends a message to all connected clients, optionally excluding the sender."""
    print(f"Broadcasting: {message.strip()}")  # Log message to server console
    encoded_message = (message + "\n").encode("utf-8")  # Add newline and encode

    # Create a list of writers to send to avoid issues if clients dict changes during iteration
    writers_to_send = list(clients.keys())

    for writer in writers_to_send:
        if (
            writer is sender_writer
        ):  # Don't send the message back to the original sender
            continue
        if writer.is_closing():  # Skip writers whose connections are closing
            cleanup_client(writer)
            continue
        try:
            writer.write(encoded_message)
            await writer.drain()  # Ensure the message is sent
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            print(f"{BRIGHT_BLACK}Error sending to a client: {e}. Cleaning up.{RESET}")
            cleanup_client(writer)  # Remove problematic client
        except Exception as e:
            print(f"{RED}Unexpected error sending message: {e}{RESET}")
            cleanup_client(writer)  # Attempt cleanup on other errors too


def cleanup_client(writer):
    """Removes a client from the lists upon disconnection or error."""
    if writer in clients:
        username = clients[writer]["username"]
        color = clients[writer]["color"]
        print(f"{BRIGHT_BLACK}Cleaning up client: {username}{RESET}")
        del clients[writer]
        if username in active_usernames:
            active_usernames.remove(username)
        # Don't try to broadcast disconnect message if the writer is already problematic
        # Instead, let the next broadcast or client action handle showing they left.
        # We *could* try broadcasting here, but it might fail if the server is stressed.
        # asyncio.create_task(broadcast(f"{YELLOW}[System] {color}{username}{RESET}{YELLOW} has left the chat.{RESET}"))
    if not writer.is_closing():
        try:
            writer.close()
            # await writer.wait_closed() # Can uncomment, but might delay cleanup
        except Exception as e:
            print(f"{BRIGHT_BLACK}Error during writer close for cleanup: {e}{RESET}")


# --- Main Client Handler ---
async def handle_client(reader, writer):
    """Manages a single client connection."""
    addr = writer.get_extra_info("peername")
    print(f"{GREEN}New connection from {addr}{RESET}")
    username = None
    color = None

    try:
        # 1. Get Username
        while True:
            writer.write(f"{CYAN}Enter your username: {RESET}".encode("utf-8"))
            await writer.drain()
            try:
                # Read up to 100 bytes for the username
                data = await asyncio.wait_for(reader.read(100), timeout=60.0)
                potential_username = data.decode("utf-8").strip()

                if not potential_username:
                    continue  # Ignore empty input

                if potential_username in active_usernames:
                    writer.write(
                        f"{RED}Username '{potential_username}' is already taken. Try another.{RESET}\n".encode(
                            "utf-8"
                        )
                    )
                    await writer.drain()
                elif not potential_username.isalnum():  # Basic validation
                    writer.write(
                        f"{RED}Username can only contain letters and numbers.{RESET}\n".encode(
                            "utf-8"
                        )
                    )
                    await writer.drain()
                else:
                    username = potential_username
                    active_usernames.add(username)
                    color = get_random_color()
                    clients[writer] = {"username": username, "color": color}
                    print(
                        f"{GREEN}User {color}{username}{RESET}{GREEN} joined from {addr}{RESET}"
                    )
                    break  # Username accepted
            except asyncio.TimeoutError:
                writer.write(
                    f"\n{RED}Timeout waiting for username. Disconnecting.{RESET}\n".encode(
                        "utf-8"
                    )
                )
                await writer.drain()
                return  # Disconnect client
            except (UnicodeDecodeError, ConnectionResetError, BrokenPipeError) as e:
                print(
                    f"{BRIGHT_BLACK}Error reading username from {addr}: {e}. Disconnecting.{RESET}"
                )
                return  # Disconnect client

        # 2. Welcome message and notify others
        writer.write(
            f"\n{BOLD}{GREEN}Welcome to the chat, {color}{username}{RESET}{BOLD}{GREEN}!{RESET}\n".encode(
                "utf-8"
            )
        )
        # Show currently connected users (excluding self)
        if len(clients) > 1:
            other_users = ", ".join(
                [
                    f"{c['color']}{c['username']}{RESET}"
                    for w, c in clients.items()
                    if w != writer
                ]
            )
            writer.write(
                f"{YELLOW}Currently online: {other_users}{RESET}\n".encode("utf-8")
            )
        else:
            writer.write(
                f"{YELLOW}You are the first one here!{RESET}\n".encode("utf-8")
            )
            writer.write(("-" * 40 + "\n").encode("utf-8"))
        await writer.drain()

        await broadcast(
            f"{YELLOW}[System] {color}{username}{RESET}{YELLOW} has joined the chat!{RESET}",
            sender_writer=writer,
        )

        # 3. Chat Loop
        while True:
            try:
                # Read up to 1024 bytes for a message
                data = await asyncio.wait_for(
                    reader.read(1024), timeout=None
                )  # No timeout for reading chat messages
                message = data.decode("utf-8").strip()

                if not message:  # Client likely disconnected if empty message received
                    print(
                        f"{BRIGHT_BLACK}Empty message received from {color}{username}{RESET}{BRIGHT_BLACK}, likely disconnect.{RESET}"
                    )
                    break  # Exit loop to disconnect

                # Prepare colored message for broadcasting
                formatted_message = f"{BOLD}{color}{username}{RESET}: {message}"
                await broadcast(formatted_message, sender_writer=writer)

            except (
                asyncio.IncompleteReadError,
                ConnectionResetError,
                BrokenPipeError,
                ConnectionAbortedError,
            ):
                print(f"{BRIGHT_BLACK}Connection lost for {color}{username}{RESET}")
                break  # Exit loop to disconnect
            except UnicodeDecodeError:
                print(
                    f"{RED}Received non-utf8 data from {color}{username}{RESET}. Ignoring."
                )
                # Optionally send an error back to the client?
                # writer.write(f"{RED}[System] Error: Please send UTF-8 text only.{RESET}\n".encode('utf-8'))
                # await writer.drain()
            except Exception as e:
                print(f"{RED}Unexpected error for client {color}{username}{RESET}: {e}")
                break  # Exit loop on unexpected errors

    except Exception as e:
        print(f"{RED}General error handling client {addr}: {e}{RESET}")
    finally:
        # 4. Cleanup when client disconnects or error occurs
        print(
            f"{BRIGHT_BLACK}Disconnecting client {addr} (User: {clients.get(writer, {}).get('username', 'N/A')}){RESET}"
        )
        if writer in clients:
            username = clients[writer]["username"]
            color = clients[writer]["color"]
            cleanup_client(writer)
            # Notify others only if username was set
            if username:
                await broadcast(
                    f"{YELLOW}[System] {color}{username}{RESET}{YELLOW} has left the chat.{RESET}"
                )
        else:
            # Ensure writer is closed even if it was never added to clients (e.g., failed username prompt)
            if not writer.is_closing():
                try:
                    writer.close()
                    # await writer.wait_closed()
                except Exception as e:
                    print(
                        f"{BRIGHT_BLACK}Error closing writer during final cleanup: {e}{RESET}"
                    )

        print(
            f"{BRIGHT_BLACK}Connection closed for {addr}. Remaining clients: {len(clients)}{RESET}"
        )


# --- Server Entry Point ---
async def main():
    """Starts the asyncio chat server."""
    server = await asyncio.start_server(handle_client, HOST, PORT)

    addr = server.sockets[0].getsockname()
    print(f"{BOLD}{GREEN}Chat Server started on {addr[0]}:{addr[1]}{RESET}")
    print(f"{YELLOW}Waiting for connections... Press Ctrl+C to stop.{RESET}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Server shutting down gracefully...{RESET}")

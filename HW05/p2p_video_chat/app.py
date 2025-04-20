import cv2
import zmq
import threading
import time
import socket
import base64
import json
import queue
import argparse
import logging
import os  # Needed for secret key and potentially restart logic if added later
from flask import (
    Flask,
    Response,
    render_template,
    request,
    jsonify,
    stream_with_context,
    redirect,
    url_for,
)

# --- Configuration ---
BROADCAST_PORT = 30001  # UDP port for discovery broadcasts
HEARTBEAT_INTERVAL = 5  # Seconds between discovery heartbeats
PEER_TIMEOUT = 15  # Seconds before considering a peer disconnected
MAX_FRAME_QUEUE_SIZE = 10  # Max frames to buffer per peer for SSE
JPEG_QUALITY = 70  # JPEG quality (0-100)
DEFAULT_FLASK_PORT = 5000  # Default port for the local Flask web server

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
)

# --- Global State (Thread Safety Considerations) ---
peers = {}  # { peer_id: {'name': str, 'addr': (ip, zmq_port), 'last_seen': time.time()} }
peers_lock = threading.Lock()
frame_queues = {}  # { peer_id: queue.Queue(maxsize=MAX_FRAME_QUEUE_SIZE) }
frame_queues_lock = threading.Lock()
sse_clients = []  # List of Server-Sent Event queues to push updates to clients
sse_clients_lock = threading.Lock()
my_info = {}  # Populated after setup form submission { 'name': str, 'room': str, 'ip': str, 'zmq_port': int, 'peer_id': str }
my_info_lock = threading.Lock()  # Protect access/modification of my_info
shutdown_flag = threading.Event()  # To signal threads to stop
threads = []  # Keep track of running background threads
threads_started = (
    threading.Event()
)  # Use an event to signal if threads are running/should run
# Add a lock specific for the switching/joining process to prevent races
config_lock = threading.Lock()


# --- Flask App ---
app = Flask(__name__)
# Secret key is needed for session management if we ever use flask session cookies more extensively
# In a real app, use a proper secret key management strategy (e.g., environment variable)
app.secret_key = os.urandom(24)


# --- Helper Functions ---


def get_local_ip():
    """Gets the local IP address used for outgoing connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        try:
            # Fallback for systems where the above fails (e.g., no default route)
            hostname = socket.gethostname()
            IP = socket.gethostbyname(hostname)
        except Exception:
            IP = "127.0.0.1"  # Final fallback
    finally:
        s.close()
    return IP


def generate_peer_id(ip, port):
    """Generates a unique ID for a peer."""
    return f"{ip}:{port}"


def notify_sse_clients(event_type, data):
    """Sends an event to all connected SSE clients."""
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with sse_clients_lock:
        # Iterate over a copy in case a client disconnects during iteration
        for client_queue in list(sse_clients):
            try:
                client_queue.put_nowait(message)
            except queue.Full:
                logging.warning(
                    f"SSE client queue full for event {event_type}. Skipping."
                )
            except Exception as e:
                logging.error(
                    f"Error putting message in SSE client queue: {e}. Removing queue."
                )
                # Remove problematic queue
                try:
                    sse_clients.remove(client_queue)
                except ValueError:
                    pass  # Already removed


# --- Thread Functions ---


def discovery_thread():
    """Handles broadcasting presence and discovering peers."""
    # Wait until my_info is populated and threads are officially started
    threads_started.wait()
    if shutdown_flag.is_set():
        return  # Check if shutdown happened while waiting

    # Fetch config for this run of the thread
    with my_info_lock:
        if not my_info:
            logging.error("Discovery: my_info not set.")
            return
        room_number = my_info["room"]
        name = my_info["name"]
        zmq_port = my_info["zmq_port"]
        my_ip = my_info["ip"]
        my_peer_id = my_info["peer_id"]
    room_tag = f"[Discovery-{room_number}-{name[:5]}]"  # Short identifier for logs
    logging.info(f"{room_tag} Thread starting.")

    broadcast_addr = ("<broadcast>", BROADCAST_PORT)
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_sock.settimeout(1.0)  # Timeout for listening

        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(("", BROADCAST_PORT))  # Listen on all interfaces
        logging.info(f"{room_tag} Listening on UDP port {BROADCAST_PORT}")
    except OSError as e:
        logging.error(
            f"{room_tag} Could not bind to UDP port {BROADCAST_PORT}: {e}. Thread exiting."
        )
        return  # Cannot continue without sockets

    last_heartbeat_time = 0
    while not shutdown_flag.is_set():
        # 1. Broadcast Heartbeat
        current_time = time.time()
        if current_time - last_heartbeat_time > HEARTBEAT_INTERVAL:
            # Use the config fetched at the start of this thread's run
            message = f"ALIVE|{room_number}|{name}|{zmq_port}|{my_peer_id}"
            try:
                broadcast_sock.sendto(message.encode("utf-8"), broadcast_addr)
                last_heartbeat_time = current_time
            except OSError as e:
                logging.warning(f"{room_tag} Could not send broadcast heartbeat: {e}")

        # 2. Listen for Peer Messages
        try:
            data, addr = listen_sock.recvfrom(1024)
            message = data.decode("utf-8")
            sender_ip = addr[0]

            # Ignore self messages robustly
            if sender_ip == my_ip:
                try:
                    parts_check = message.split("|")
                    if len(parts_check) >= 4 and int(parts_check[3]) == zmq_port:
                        continue  # It's definitely me
                except (ValueError, IndexError):
                    pass  # Ignore malformed

            parts = message.split("|")
            if len(parts) == 5 and parts[0] == "ALIVE":
                msg_type, peer_room, peer_name, peer_zmq_port_str, peer_id_rcv = parts
                # IMPORTANT: Only process if the message is for the room this thread instance is managing
                if peer_room == room_number:
                    try:
                        peer_zmq_port_int = int(peer_zmq_port_str)
                        peer_addr = (sender_ip, peer_zmq_port_int)
                        # Calculate expected peer_id based on sender IP and claimed ZMQ port
                        expected_peer_id = generate_peer_id(
                            sender_ip, peer_zmq_port_int
                        )

                        # Verify received peer_id matches calculated one
                        if expected_peer_id != peer_id_rcv:
                            logging.warning(
                                f"{room_tag} Peer ID mismatch from {sender_ip}. Expected {expected_peer_id}, got {peer_id_rcv}. Ignoring."
                            )
                            continue

                        now = time.time()
                        is_new_peer = False
                        peer_id_to_process = expected_peer_id  # Use the verified ID

                        with peers_lock:
                            if peer_id_to_process not in peers:
                                is_new_peer = True
                                logging.info(
                                    f"{room_tag} Discovered new peer: {peer_name} ({peer_id_to_process})"
                                )
                            # Always update last_seen and potentially name/addr
                            peers[peer_id_to_process] = {
                                "name": peer_name,
                                "addr": peer_addr,
                                "last_seen": now,
                            }

                        if is_new_peer:
                            # Notify web clients about the new peer
                            notify_sse_clients(
                                "peer_join",
                                {"peer_id": peer_id_to_process, "name": peer_name},
                            )
                            # Create frame queue for this new peer
                            with frame_queues_lock:
                                if peer_id_to_process not in frame_queues:
                                    frame_queues[peer_id_to_process] = queue.Queue(
                                        maxsize=MAX_FRAME_QUEUE_SIZE
                                    )
                                    logging.debug(
                                        f"{room_tag} Created frame queue for {peer_id_to_process}"
                                    )

                    except ValueError:
                        logging.warning(
                            f"{room_tag} Invalid port number received from {sender_ip}: {peer_zmq_port_str}"
                        )
                    except Exception as e:
                        logging.error(
                            f"{room_tag} Error processing discovery message from {sender_ip}: {e}",
                            exc_info=True,
                        )

        except socket.timeout:
            pass  # Normal timeout, continue loop
        except OSError as e:  # Handle potential socket errors during recvfrom
            if not shutdown_flag.is_set():  # Avoid logging errors during shutdown
                logging.error(f"{room_tag} Error receiving discovery message: {e}")
                time.sleep(1)  # Avoid busy-looping on recv error
        except Exception as e:
            if not shutdown_flag.is_set():
                logging.error(
                    f"{room_tag} Unexpected error in discovery listening: {e}",
                    exc_info=True,
                )
                time.sleep(1)

        # 3. Check for Timed-out Peers
        now = time.time()
        timed_out_peers = []
        with peers_lock:
            # Iterate over copy of items in case dict changes during iteration elsewhere (less likely here but safer)
            for peer_id, info in list(peers.items()):
                if now - info["last_seen"] > PEER_TIMEOUT:
                    timed_out_peers.append((peer_id, info["name"]))
                    # Remove directly here while holding lock
                    del peers[peer_id]
                    # Also remove frame queue immediately
                    with frame_queues_lock:
                        if peer_id in frame_queues:
                            del frame_queues[peer_id]
                            logging.debug(
                                f"{room_tag} Removed frame queue for timed out peer {peer_id}"
                            )

        # Process timeouts outside the peers_lock
        for peer_id, peer_name in timed_out_peers:
            logging.info(f"{room_tag} Peer timed out: {peer_name} ({peer_id})")
            notify_sse_clients("peer_leave", {"peer_id": peer_id, "name": peer_name})
            # Frame queue already removed above

    # Cleanup
    logging.info(f"{room_tag} Thread shutting down.")
    broadcast_sock.close()
    listen_sock.close()


def video_publisher_thread():
    """Captures video, encodes it, and publishes via ZMQ PUB."""
    threads_started.wait()
    if shutdown_flag.is_set():
        return

    with my_info_lock:
        if not my_info:
            logging.error("Publisher: my_info not set.")
            return
        zmq_pub_port = my_info["zmq_port"]
        room_number = my_info["room"]
        my_peer_id = my_info["peer_id"]
    room_tag = f"[Publisher-{room_number}-{my_peer_id[:8]}]"
    logging.info(f"{room_tag} Thread starting.")

    context = zmq.Context.instance()  # Use instance() for shared context potentially
    pub_socket = context.socket(zmq.PUB)
    cap = None

    try:
        pub_socket.bind(f"tcp://*:{zmq_pub_port}")
        logging.info(f"{room_tag} ZMQ Publisher bound to tcp://*:{zmq_pub_port}")
    except zmq.ZMQError as e:
        logging.error(
            f"{room_tag} Could not bind ZMQ PUB socket to port {zmq_pub_port}: {e}. Thread exiting."
        )
        # pub_socket.close() # Socket might not be valid
        # context.term() # Don't terminate shared context here
        return

    try:
        cap = cv2.VideoCapture(0)  # Use camera 0
        if not cap.isOpened():
            raise IOError("Cannot open webcam")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Optional: Check actual resolution set
        actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logging.info(
            f"{room_tag} Webcam opened with resolution {actual_width}x{actual_height}"
        )

    except Exception as e:
        logging.error(f"{room_tag} Error opening webcam: {e}. Thread exiting.")
        if cap:
            cap.release()
        pub_socket.close()
        # context.term()
        return

    # Topic uses the room and peer_id for this specific thread run
    topic = f"{room_number}|{my_peer_id}".encode("utf-8")

    while not shutdown_flag.is_set() and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            logging.warning(f"{room_tag} Failed to grab frame from camera")
            time.sleep(0.1)  # Avoid busy loop if camera fails temporarily
            continue

        # Encode frame as JPEG
        ret_enc, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )
        if not ret_enc:
            logging.warning(f"{room_tag} Failed to encode frame")
            continue

        # Publish: topic + frame data
        try:
            # Send topic first, then the image bytes
            pub_socket.send_multipart(
                [topic, buffer.tobytes()], zmq.DONTWAIT
            )  # Use DONTWAIT to avoid blocking if HWM reached
        except zmq.Again:
            # High water mark likely reached, message dropped by ZMQ
            # logging.debug(f"{room_tag} ZMQ PUB High Water Mark reached, frame dropped.")
            time.sleep(0.01)  # Small sleep if overloaded
        except zmq.ZMQError as e:
            if not shutdown_flag.is_set():  # Avoid errors during shutdown
                logging.warning(f"{room_tag} Error sending frame via ZMQ PUB: {e}")
                time.sleep(0.5)  # Back off if error sending

        # Limit frame rate server-side
        time.sleep(1 / 25)  # Aim for ~25 fps max publish rate

    # Cleanup
    logging.info(f"{room_tag} Thread shutting down.")
    if cap:
        cap.release()
    pub_socket.close()
    # Don't terminate shared context here: context.term()


def video_subscriber_thread():
    """Subscribes to peers' video streams and pushes frames to queues."""
    threads_started.wait()
    if shutdown_flag.is_set():
        return

    with my_info_lock:
        if not my_info:
            logging.error("Subscriber: my_info not set.")
            return
        room_number = my_info["room"]
        my_peer_id = my_info[
            "peer_id"
        ]  # Needed to potentially ignore self-loopback if discovery fails
    room_tag = f"[Subscriber-{room_number}]"
    logging.info(f"{room_tag} Thread starting.")

    context = zmq.Context.instance()
    sub_socket = context.socket(zmq.SUB)
    sub_socket.setsockopt(
        zmq.RCVTIMEO, 1000
    )  # Timeout for receiving messages (milliseconds)
    # Subscribe based on the room number for this run
    topic_filter = f"{room_number}|".encode("utf-8")
    sub_socket.setsockopt(zmq.SUBSCRIBE, topic_filter)
    logging.info(f"{room_tag} Subscribed to topic filter: {topic_filter.decode()}")

    connected_peer_addrs = set()  # Keep track of ZMQ connect() calls: {(ip, port), ...}

    while not shutdown_flag.is_set():
        # Dynamically connect/disconnect based on current peer list
        target_peer_addrs = set()
        with peers_lock:
            # Get addresses of peers currently known for *any* room (discovery manages room filtering)
            # We only need the addresses to connect the SUB socket
            target_peer_addrs = {info["addr"] for info in peers.values()}

        # Connect to new peers
        new_connections = target_peer_addrs - connected_peer_addrs
        for ip, port in new_connections:
            connect_addr = f"tcp://{ip}:{port}"
            try:
                logging.info(f"{room_tag} Connecting ZMQ SUB to {connect_addr}")
                sub_socket.connect(connect_addr)
                connected_peer_addrs.add((ip, port))
            except zmq.ZMQError as e:
                logging.error(
                    f"{room_tag} Failed to connect ZMQ SUB to {connect_addr}: {e}"
                )

        # Disconnect from disappeared peers
        disconnected = connected_peer_addrs - target_peer_addrs
        for ip, port in disconnected:
            disconnect_addr = f"tcp://{ip}:{port}"
            try:
                logging.info(f"{room_tag} Disconnecting ZMQ SUB from {disconnect_addr}")
                sub_socket.disconnect(disconnect_addr)
                connected_peer_addrs.remove((ip, port))
            except zmq.ZMQError as e:
                # Can happen if connection already closed, usually safe to ignore warning
                logging.warning(
                    f"{room_tag} Error disconnecting ZMQ SUB from {disconnect_addr}: {e}"
                )

        # Receive messages
        try:
            multipart_msg = (
                sub_socket.recv_multipart()
            )  # Blocks until timeout or message
            if len(multipart_msg) == 2:
                topic, frame_data = multipart_msg
                try:
                    topic_str = topic.decode("utf-8")
                    topic_parts = topic_str.split("|")

                    if len(topic_parts) == 2:
                        rcv_room, sender_peer_id = topic_parts

                        # Check if the message is for the room this thread is managing
                        if rcv_room == room_number:
                            # Check if sender is still considered an active peer (mitigates late messages)
                            peer_exists = False
                            with peers_lock:
                                peer_exists = sender_peer_id in peers

                            if peer_exists:
                                # Put frame in the corresponding queue for SSE
                                with frame_queues_lock:
                                    if sender_peer_id in frame_queues:
                                        try:
                                            # Store raw frame data bytes
                                            frame_queues[sender_peer_id].put_nowait(
                                                frame_data
                                            )
                                        except queue.Full:
                                            # Queue is full, drop the frame (shows client UI is lagging)
                                            logging.debug(
                                                f"{room_tag} Frame queue full for {sender_peer_id}, dropping frame."
                                            )
                                            pass
                                    # else: Queue might have been removed just before this check, ignore.
                            # else: logging.debug(f"{room_tag} Received frame from inactive/unknown peer {sender_peer_id}. Ignoring.")
                        # else: Message received for a different room, ZMQ filter might have race condition on unsubscribe? Ignore.

                except UnicodeDecodeError:
                    logging.warning(f"{room_tag} Received message with non-UTF8 topic.")
                except Exception as e:  # Catch errors processing message parts
                    logging.error(
                        f"{room_tag} Error processing received ZMQ message parts: {e}"
                    )

        # else: Received message with unexpected part count

        except zmq.Again:
            pass  # Normal receive timeout, loop continues
        except zmq.ZMQError as e:
            if (
                e.errno == zmq.ETERM or shutdown_flag.is_set()
            ):  # Context terminated or shutting down
                break
            logging.error(f"{room_tag} ZMQ SUB socket error: {e}")
            time.sleep(1)  # Avoid busy-looping on persistent error
        except Exception as e:
            if not shutdown_flag.is_set():
                logging.error(
                    f"{room_tag} Unexpected error in ZMQ Subscriber loop: {e}",
                    exc_info=True,
                )
                time.sleep(1)

    # Cleanup
    logging.info(f"{room_tag} Thread shutting down.")
    sub_socket.close()
    # Don't terminate shared context here: context.term()


def sse_frame_distributor_thread():
    """Periodically checks frame queues and sends updates via SSE."""
    threads_started.wait()
    if shutdown_flag.is_set():
        return
    logging.info("[SSE Distributor] Thread starting.")

    while not shutdown_flag.is_set():
        frames_to_send = {}
        with frame_queues_lock:
            # Get one frame from each non-empty queue
            # Iterate over a copy of keys in case dict changes during iteration
            for peer_id in list(frame_queues.keys()):
                q = frame_queues.get(peer_id)  # Get queue again safely
                if q:
                    try:
                        frame_data = q.get_nowait()  # Get raw jpg bytes
                        # Encode to base64 for JSON embedding in SSE
                        b64_frame = base64.b64encode(frame_data).decode("utf-8")
                        frames_to_send[peer_id] = b64_frame
                    except queue.Empty:
                        continue  # No new frame for this peer
                    except Exception as e:
                        logging.error(
                            f"[SSE Distributor] Error processing frame from queue for {peer_id}: {e}"
                        )

        # Send collected frames via SSE
        if frames_to_send:
            # Use a non-blocking approach or thread pool if notify becomes slow?
            # For now, assume notify_sse_clients is fast enough
            for peer_id, b64_frame in frames_to_send.items():
                notify_sse_clients(
                    "video_update", {"peer_id": peer_id, "frame": b64_frame}
                )

        # Adjust sleep time based on desired update rate for the web UI
        time.sleep(1 / 30)  # ~30 Hz update rate target

    logging.info("[SSE Distributor] Thread shutting down.")


# --- Thread Management ---


def start_background_threads():
    """Starts all necessary background threads IF they aren't running."""
    global threads
    # Ensure this function is thread-safe if called concurrently (using config_lock externally)
    if threads_started.is_set():
        logging.warning("Attempted to start threads when already started.")
        return

    with my_info_lock:  # Read current info for logging/setup
        if not my_info:
            logging.error("Cannot start threads: my_info is not configured.")
            return
        room = my_info.get("room", "N/A")
        name = my_info.get("name", "N/A")

    logging.info(f"Starting background threads for room='{room}', name='{name}'...")
    shutdown_flag.clear()  # Ensure flag is clear before starting new threads
    threads.clear()  # Clear previous thread list

    # Define threads
    disc_thread = threading.Thread(
        target=discovery_thread, name="DiscoveryThread", daemon=True
    )
    pub_thread = threading.Thread(
        target=video_publisher_thread, name="VideoPublisherThread", daemon=True
    )
    sub_thread = threading.Thread(
        target=video_subscriber_thread, name="VideoSubscriberThread", daemon=True
    )
    sse_dist_thread = threading.Thread(
        target=sse_frame_distributor_thread, name="SSEDistributorThread", daemon=True
    )

    threads.extend([disc_thread, pub_thread, sub_thread, sse_dist_thread])

    # Start threads
    for t in threads:
        t.start()

    threads_started.set()  # Signal that threads are (attempting to) run
    logging.info("Background threads initiated.")


def stop_background_threads():
    """Signals all background threads to stop and waits for them, clearing state."""
    global threads
    # Ensure this function is thread-safe if called concurrently (using config_lock externally)
    if not threads_started.is_set():
        # logging.info("No background threads currently running to stop.")
        return

    with my_info_lock:
        room = my_info.get("room", "N/A")
    logging.info(f"Stopping background threads for room {room}...")
    shutdown_flag.set()  # Signal threads to stop via the event

    # Wait for threads to finish
    active_threads = list(threads)  # Copy list for safe iteration
    for t in active_threads:
        try:
            t.join(timeout=2.0)  # Wait for 2 seconds per thread
            if t.is_alive():
                logging.warning(f"Thread {t.name} did not shut down gracefully.")
        except Exception as e:
            logging.error(f"Error joining thread {t.name}: {e}")

    threads_started.clear()  # Signal that threads are stopped
    threads.clear()  # Clear the list

    # Clear state associated with the session
    with peers_lock:
        peers.clear()
    with frame_queues_lock:
        frame_queues.clear()
    # Note: SSE clients might still be connected briefly, they will error out or timeout.
    # We could explicitly close their queues here if needed, but maybe not necessary.
    logging.info("Background threads stopped and state cleared.")


# --- Flask Routes ---


@app.route("/")
def main_page():
    """Displays setup form or chat interface based on state."""
    with my_info_lock:
        # Check if my_info has been populated (implies setup complete)
        is_setup = bool(my_info)

    if is_setup and threads_started.is_set():
        # User is joined, show chat interface
        with my_info_lock:  # Fetch current info safely
            room_num = my_info.get("room", "N/A")
            my_name = my_info.get("name", "N/A")
        return render_template("index.html", room_number=room_num, my_name=my_name)
    else:
        # Not joined or threads stopped, show setup form
        # Ensure threads are stopped if we somehow got here incorrectly
        if threads_started.is_set():
            logging.warning(
                "Accessing root '/' but threads were running. Stopping threads."
            )
            # Use the lock to ensure safe stop/clear
            with config_lock:
                stop_background_threads()
                with my_info_lock:
                    my_info.clear()  # Clear info if showing setup
        else:
            # Ensure info is clear if threads aren't running
            with my_info_lock:
                my_info.clear()

        return render_template("setup.html")


@app.route("/join", methods=["POST"])
def join_chat():
    """Processes the initial setup form submission."""
    # Use config_lock to ensure atomicity of join operation
    with config_lock:
        room = request.form.get("room_id")
        name = request.form.get("username")

        if not room or not name:
            # Consider flashing a message back to the setup page
            return "Room ID and Name are required.", 400

        # If already running (e.g., user manually POSTs again), stop first
        if threads_started.is_set():
            logging.warning("'/join' called while threads running. Stopping first.")
            stop_background_threads()

        # Configure my_info for the first time
        zmq_pub_port = app.config.get(
            "ZMQ_PORT", 0
        )  # Get from app config or use default
        if zmq_pub_port == 0:
            # Assign a random port if not specified
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_ip_for_bind = (
                get_local_ip()
            )  # Use local IP hint for binding ephemeral port
            temp_sock.bind((local_ip_for_bind, 0))
            zmq_pub_port = temp_sock.getsockname()[1]
            temp_sock.close()
            app.config["ZMQ_PORT"] = zmq_pub_port  # Store globally for consistency
            logging.info(f"Using randomly assigned ZMQ PUB port: {zmq_pub_port}")

        with my_info_lock:
            my_info.clear()  # Ensure clean slate
            my_info["name"] = name
            my_info["room"] = room
            my_info["ip"] = get_local_ip()
            my_info["zmq_port"] = zmq_pub_port
            my_info["peer_id"] = generate_peer_id(my_info["ip"], zmq_pub_port)
            logging.info(
                f"Joining chat: Room='{room}', Name='{name}', PeerID={my_info['peer_id']}"
            )

        # Start the background threads now that info is set
        start_background_threads()

    # Redirect to the main page, which will now show the chat interface
    return redirect(url_for("main_page"))


@app.route("/switch_room", methods=["POST"])
def switch_room():
    """Handles request to change room or username mid-session."""
    # Ensure user is already in a session before allowing switch
    if not threads_started.is_set() or not my_info:
        return jsonify({"status": "error", "message": "Not currently in a room."}), 400

    # Use config_lock to prevent races with join/leave/other switches
    with config_lock:
        try:
            data = request.get_json()
            if not data:
                return jsonify(
                    {"status": "error", "message": "Invalid request format."}
                ), 400

            new_room = data.get("room_id")
            new_name = data.get("username")

            # Basic validation
            if (
                not new_room
                or not isinstance(new_room, str)
                or not new_name
                or not isinstance(new_name, str)
            ):
                return jsonify(
                    {
                        "status": "error",
                        "message": "Valid New Room ID and Name are required.",
                    }
                ), 400

            new_room = new_room.strip()
            new_name = new_name.strip()
            if not new_room or not new_name:  # Check after stripping
                return jsonify(
                    {
                        "status": "error",
                        "message": "New Room ID and Name cannot be empty.",
                    }
                ), 400

            with my_info_lock:
                current_room = my_info.get("room")
                current_name = my_info.get("name")
                # Keep the same peer ID (IP and ZMQ port)
                peer_id = my_info.get("peer_id")

            # Check if there's actually a change
            if new_room == current_room and new_name == current_name:
                return jsonify({"status": "ok", "message": "No changes detected."})

            logging.info(
                f"Switching room/name for {peer_id}: From Room='{current_room}' Name='{current_name}' TO Room='{new_room}' Name='{new_name}'"
            )

            # ---- Reconfiguration Process ----
            # 1. Stop current threads & clear state
            stop_background_threads()  # This now clears peers and frame_queues

            # 2. Update configuration in my_info (keep IP, ZMQ port, peer_id)
            with my_info_lock:
                my_info["room"] = new_room
                my_info["name"] = new_name
                # Peer ID remains the same as ZMQ port is reused

            # 3. Restart threads with the new configuration
            # Give a tiny pause for OS/network resources to potentially release if needed
            time.sleep(0.2)
            start_background_threads()
            # ---- Reconfiguration Complete ----

            return jsonify({"status": "ok", "message": "Switched successfully."})

        except Exception as e:
            logging.error(f"Error during room switch: {e}", exc_info=True)
            # Attempt to rollback state? Difficult. Best to force back to setup.
            try:
                if threads_started.is_set():
                    stop_background_threads()
                with my_info_lock:
                    my_info.clear()  # Clear info to force setup page on next access
            except Exception as cleanup_e:
                logging.error(f"Error during switch cleanup: {cleanup_e}")

            return jsonify(
                {
                    "status": "error",
                    "message": f"Internal server error during switch: {e}",
                }
            ), 500


@app.route("/leave")
def leave_chat():
    """Stops the threads and clears session info, returning to setup."""
    # Use config_lock for atomicity
    with config_lock:
        user_name, room_name = "N/A", "N/A"
        with my_info_lock:
            user_name = my_info.get("name", user_name)
            room_name = my_info.get("room", room_name)
            my_info.clear()  # Clear user info state first

        logging.info(
            f"User '{user_name}' leaving room '{room_name}'. Stopping threads."
        )
        stop_background_threads()  # Stop associated threads

    # Redirect back to setup page
    return redirect(url_for("main_page"))


# --- Video Feed and SSE Routes ---


def gen_self_frames():
    """Generator function for streaming own video feed."""
    # Check if threads are supposed to be running
    if not threads_started.is_set():
        logging.warning("Attempted to get self video feed when not joined/running.")
        # Optionally yield a placeholder image or just stop immediately
        # For simplicity, just stop here
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("Cannot open webcam for self-view stream.")
        return

    # Reduced resolution for self-view is often fine
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    logging.info("[SelfFeed] Starting video capture loop.")
    while threads_started.is_set() and not shutdown_flag.is_set() and cap.isOpened():
        success, frame = cap.read()
        if not success:
            logging.warning("[SelfFeed] Failed to get frame for self-view.")
            time.sleep(0.5)  # Wait a bit if capture fails
            continue
        else:
            # Encode with slightly lower quality for self-view perhaps
            ret, buffer = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY - 10]
            )
            if not ret:
                logging.warning("[SelfFeed] Failed to encode self-view frame.")
                continue
            frame_bytes = buffer.tobytes()
            # Yield the frame in the format required by multipart/x-mixed-replace
            try:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            except GeneratorExit:
                # Client disconnected
                logging.info("[SelfFeed] Client disconnected from self feed.")
                break  # Exit loop cleanly
            # Control streaming rate
            time.sleep(1 / 20)  # Aim for ~20 fps for self view

    logging.info("[SelfFeed] Stopping self-view stream.")
    cap.release()


@app.route("/video_feed_self")
def video_feed_self():
    """Video streaming route for the client's own camera."""
    return Response(
        gen_self_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/events")
def events():
    """Server-Sent Events endpoint for peer updates and video frames."""
    # Check if the user should be connected (threads running implies setup complete)
    if not threads_started.is_set():
        logging.warning(
            "SSE connection attempt refused: Threads not running (user likely not joined)."
        )
        # Return an empty response with an error status or a retry header?
        # Let's return Forbidden, client JS should handle this.
        return Response("Not joined.", status=403)

    # Each client gets their own queue for SSE messages
    client_queue = queue.Queue(maxsize=50)  # Buffer for this specific client connection
    with sse_clients_lock:
        sse_clients.append(client_queue)
    logging.info(
        f"SSE client connected: {request.remote_addr} (Total: {len(sse_clients)})"
    )

    # Immediately send current list of peers to the new client
    current_peers_data = []
    with peers_lock:
        current_peers_data = [
            {"peer_id": pid, "name": pinfo["name"]} for pid, pinfo in peers.items()
        ]

    for peer_data in current_peers_data:
        try:
            # Format message correctly
            initial_peer_msg = f"event: peer_join\ndata: {json.dumps(peer_data)}\n\n"
            client_queue.put_nowait(initial_peer_msg)
        except queue.Full:
            logging.warning(
                f"SSE client queue full while sending initial peer list to {request.remote_addr}."
            )
            # Client might miss initial peers if queue fills instantly

    @stream_with_context
    def event_stream():
        """Generator for the SSE stream for this client."""
        client_disconnected = False
        while (
            not client_disconnected and threads_started.is_set()
        ):  # Continue as long as main threads are running
            try:
                # Wait for a message on this client's queue
                message = client_queue.get(
                    timeout=30
                )  # Timeout helps detect inactive connections/queues
                yield message
            except queue.Empty:
                # Send a keep-alive comment to prevent connection timeouts by proxies/browsers
                try:
                    yield ": keepalive\n\n"
                except Exception:  # Catch potential errors yielding keepalive if client closed connection
                    client_disconnected = True
            except Exception as e:
                # Catch potential errors yielding message if client closed connection
                logging.warning(f"Error yielding SSE message: {e}")
                client_disconnected = True

        logging.info(f"SSE event stream closing for {request.remote_addr}.")
        # End of stream generation (either due to client disconnect or threads stopping)

    # Ensure response object is created outside the generator
    response = Response(event_stream(), mimetype="text/event-stream")
    # Add headers to prevent caching
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"  # Useful for Nginx buffering issues

    # Register cleanup for when client disconnects (though finally block in generator handles queue removal)
    @response.call_on_close
    def on_close():
        logging.info(f"SSE client disconnected (on_close): {request.remote_addr}")
        with sse_clients_lock:
            try:
                sse_clients.remove(client_queue)
                logging.debug(f"Removed SSE queue for {request.remote_addr}")
            except ValueError:
                pass  # Queue already removed (e.g., by generator's finally block)

    return response


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P LAN Video Chat")
    # Keep port arguments, remove room/name
    parser.add_argument(
        "--flask-port",
        type=int,
        default=DEFAULT_FLASK_PORT,
        help=f"Port for the local Flask web server (default: {DEFAULT_FLASK_PORT})",
    )
    parser.add_argument(
        "--zmq-port",
        type=int,
        default=0,
        help="Specific ZMQ PUB port to bind (default: random available)",
    )
    args = parser.parse_args()

    # Store ZMQ port choice in Flask app config for access in routes
    # If 0, it will be determined randomly on first join
    app.config["ZMQ_PORT"] = args.zmq_port
    flask_port = args.flask_port

    # Start Flask app (runs indefinitely until interrupted)
    local_ip = get_local_ip()
    logging.info("Flask server starting...")
    logging.info(
        f" ----> Access setup at: http://127.0.0.1:{flask_port} or http://{local_ip}:{flask_port} <----"
    )
    try:
        # Running Flask with debug=False and threaded=True is suitable for this multi-threaded app
        # Use 'werkzeug' for production-like scenarios if needed, but default is fine for local use
        app.run(host="0.0.0.0", port=flask_port, debug=False, threaded=True)

    except KeyboardInterrupt:
        logging.info("Ctrl+C received. Initiating shutdown...")
    except Exception as e:
        logging.error(f"Flask server failed to start or crashed: {e}", exc_info=True)
    finally:
        # Ensure threads are stopped cleanly on exit
        logging.info("Ensuring background threads are stopped before exit.")
        with config_lock:  # Ensure atomicity with other operations
            stop_background_threads()
        logging.info("Application exiting.")

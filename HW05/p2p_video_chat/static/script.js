console.log("Script loaded.");

// --- Configuration ---
const STATUS_ELEMENT_ID = 'status';
const VIDEO_GRID_ID = 'video-grid';
const SELF_VIDEO_ID = 'self-video-feed';
const SELF_VIDEO_TITLE_ID = 'self-video-title'; // ID for the H2 containing self name
const CURRENT_ROOM_ID = 'current-room';
const CURRENT_NAME_ID = 'current-name';
const NEW_ROOM_INPUT_ID = 'new_room_id';
const NEW_NAME_INPUT_ID = 'new_username';
const UPDATE_BUTTON_ID = 'update-settings-btn';

// --- DOM Elements ---
const statusElement = document.getElementById(STATUS_ELEMENT_ID);
const videoGrid = document.getElementById(VIDEO_GRID_ID);
const selfVideoTitleElement = document.getElementById(SELF_VIDEO_TITLE_ID);
const currentRoomElement = document.getElementById(CURRENT_ROOM_ID);
const currentNameElement = document.getElementById(CURRENT_NAME_ID);
const newRoomInput = document.getElementById(NEW_ROOM_INPUT_ID);
const newNameInput = document.getElementById(NEW_NAME_INPUT_ID);
const updateButton = document.getElementById(UPDATE_BUTTON_ID);


// --- State ---
let eventSource = null;
const peerVideoElements = {}; // Keep track of peer video elements { peerId: imgElement }

// --- Functions ---

/**
 * Updates the status message displayed to the user.
 * @param {string} message - The message to display.
 */
function updateStatus(message) {
    if (statusElement) {
        statusElement.textContent = message;
    }
    console.log("Status:", message);
}

/**
 * Clears all peer video containers from the grid.
 */
function clearPeerVideoGrid() {
    console.log("Clearing peer video grid.");
    // Remove elements from tracking object
    for (const peerId in peerVideoElements) {
        const container = document.getElementById(`video-container-${peerId}`);
        if (container) {
            container.remove();
        }
        delete peerVideoElements[peerId];
    }
    // Double-check DOM (though above should be sufficient)
    const peerContainers = videoGrid.querySelectorAll('.video-container:not(.self-video)');
    peerContainers.forEach(container => container.remove());
}

/**
 * Creates or updates a video container for a peer.
 * @param {string} peerId - The unique identifier for the peer.
 * @param {string} peerName - The display name of the peer.
 */
function ensurePeerVideoContainer(peerId, peerName) {
    if (!peerVideoElements[peerId]) {
        console.log(`Creating video container for peer: ${peerName} (${peerId})`);
        const container = document.createElement('div');
        container.classList.add('video-container');
        container.id = `video-container-${peerId}`;
        const title = document.createElement('h2');
        title.textContent = peerName;
        container.appendChild(title);
        const img = document.createElement('img');
        img.id = `video-${peerId}`;
        img.alt = `Video feed from ${peerName}`;
        container.appendChild(img);
        videoGrid.appendChild(container);
        peerVideoElements[peerId] = img;
    }
    const titleElement = document.querySelector(`#video-container-${peerId} h2`);
    if (titleElement && titleElement.textContent !== peerName) {
        titleElement.textContent = peerName;
    }
}

/**
 * Removes the video container for a disconnected peer.
 * @param {string} peerId - The unique identifier for the peer.
 */
function removePeerVideoContainer(peerId) {
    if (peerVideoElements[peerId]) {
        console.log(`Removing video container for peer: ${peerId}`);
        const container = document.getElementById(`video-container-${peerId}`);
        if (container) {
            container.remove();
        }
        delete peerVideoElements[peerId];
    }
}

/**
 * Updates the video frame for a specific peer.
 * @param {string} peerId - The unique identifier for the peer.
 * @param {string} frameData - Base64 encoded JPEG frame data.
 */
function updatePeerVideoFrame(peerId, frameData) {
    const imgElement = peerVideoElements[peerId];
    if (imgElement) {
        imgElement.src = `data:image/jpeg;base64,${frameData}`;
    } else {
        // console.warn(`Received frame for unknown peer ID: ${peerId}. Container might not be ready yet.`);
    }
}

/**
 * Connects to the Server-Sent Events endpoint.
 */
function connectEventSource() {
    if (eventSource) {
        console.log("Closing existing SSE connection.");
        eventSource.close();
    }

    updateStatus("Connecting to event stream...");
    eventSource = new EventSource('/events'); // Flask endpoint for SSE

    eventSource.onopen = function() {
        updateStatus("Connected. Waiting for peers...");
        console.log("SSE connection opened.");
    };

    eventSource.onerror = function(error) {
        updateStatus("Connection error. Check console."); // Don't automatically retry here, might be intended disconnect
        console.error("EventSource failed:", error);
        eventSource.close();
        // Consider informing user they might need to manually rejoin or refresh if errors persist
    };

    eventSource.addEventListener('peer_join', function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("Peer joined:", data);
            updateStatus(`Peer joined: ${data.name}`);
            ensurePeerVideoContainer(data.peer_id, data.name);
        } catch (e) { console.error("Failed to parse peer_join event:", e, event.data); }
    });

    eventSource.addEventListener('peer_leave', function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("Peer left:", data);
            updateStatus(`Peer left: ${data.name}`);
            removePeerVideoContainer(data.peer_id);
        } catch (e) { console.error("Failed to parse peer_leave event:", e, event.data); }
    });

    eventSource.addEventListener('video_update', function(event) {
        try {
            const data = JSON.parse(event.data);
            updatePeerVideoFrame(data.peer_id, data.frame);
        } catch (e) { /* Ignore if parsing fails - might happen during transitions */ }
    });

    eventSource.onmessage = function(event) {
        console.log("Generic SSE message:", event.data);
    };
}

/**
 * Handles the click on the "Update & Switch" button.
 */
async function handleUpdateSettingsClick() {
    const newRoom = newRoomInput.value.trim();
    const newName = newNameInput.value.trim();

    if (!newRoom && !newName) {
        updateStatus("Please enter a new Room ID or Name to update.");
        return;
    }

    // Use current values if inputs are left blank
    const finalRoom = newRoom || currentRoomElement.textContent;
    const finalName = newName || currentNameElement.textContent;


    updateStatus(`Switching to Room: ${finalRoom}, Name: ${finalName}...`);
    updateButton.disabled = true; // Prevent double-clicks

    try {
        const response = await fetch('/switch_room', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room_id: finalRoom,
                username: finalName
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to switch room: ${response.status} ${errorText}`);
        }

        const result = await response.json();

        if (result.status === 'ok') {
            console.log("Successfully switched room/name.");
            updateStatus(`Switched to Room: ${finalRoom}. Waiting for peers...`);

            // Update UI display
            if (currentRoomElement) currentRoomElement.textContent = finalRoom;
            if (currentNameElement) currentNameElement.textContent = finalName;
            if (selfVideoTitleElement) selfVideoTitleElement.textContent = `Me (${finalName})`;
            document.title = `P2P Video Chat - Room ${finalRoom}`; // Update page title

            // Clear old peers from the grid
            clearPeerVideoGrid();

            // Clear input fields
            newRoomInput.value = '';
            newNameInput.value = '';

            // Reconnect SSE (optional, backend changes might handle this, but explicit reconnect is safer)
            // Note: The existing SSE connection might break anyway when Flask restarts threads/handles request.
            // Reconnecting ensures we get updates for the new room.
            // connectEventSource(); // Let's rely on the existing connection or error handling for now.
            // The browser should attempt to reconnect if the connection drops.

        } else {
            throw new Error(result.message || "Unknown error during switch.");
        }

    } catch (error) {
        console.error("Error switching room:", error);
        updateStatus(`Error: ${error.message}. Please try again.`);
    } finally {
        updateButton.disabled = false; // Re-enable button
    }
}


// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed.");
    if (!document.getElementById(SELF_VIDEO_ID)) {
        console.error(`Self video element with ID '${SELF_VIDEO_ID}' not found!`);
    }
    if (updateButton) {
        updateButton.addEventListener('click', handleUpdateSettingsClick);
        console.log("Update settings button listener added.");
    } else {
        console.error("Update settings button not found!");
    }
    connectEventSource(); // Initial connection
});

// Optional: Clean up SSE connection on page unload
window.addEventListener('beforeunload', () => {
    if (eventSource) {
        console.log("Closing SSE connection on page unload.");
        eventSource.close();
    }
});
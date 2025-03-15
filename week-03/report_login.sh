#!/bin/bash

# Swaks mail settings.
SWAKS_MAIL_TO="qi7876@outlook.com"  # Receiver.
SWAKS_MAIL_FROM="2023010905015@std.uestc.edu.cn"  # Send from.
SWAKS_MAIL_SERVER="mail.std.uestc.edu.cn"  # SMTP server.
SWAKS_MAIL_PORT="25"  # SMTP port.
SWAKS_MAIL_USER="2023010905015@std.uestc.edu.cn"  # User.
SWAKS_MAIL_PASSWORD="tYjxiq-qimrat-8biqsu"  # Password.

# Cache variable to store the last detected log entry
LAST_LOG_ENTRY=""

# Send Mail using swaks
send_swaks_mail() {
  local user="$1"
  local status="$2"
  local ip="$3"
  local auth_method="$4"
  local original_log="$5"
  
  # Create a more detailed message
  local message="Login Event Details:\n\n"
  message+="User: ${user}\n"
  message+="Status: ${status}\n"
  message+="Authentication Method: ${auth_method:-Unknown}\n"
  message+="Source IP: ${ip:-local system}\n"
  message+="Timestamp: $(date '+%Y-%m-%d %H:%M:%S')\n\n"
  message+="Original Log Entry:\n${original_log}\n\n"
  
  # Adjust subject based on the login status
  local subject="[IMPORTANT] Login ${status} for ${user}"
  
  if command -v swaks &> /dev/null; then
    swaks --to "${SWAKS_MAIL_TO}" \
          --from "${SWAKS_MAIL_FROM}" \
          --server "${SWAKS_MAIL_SERVER}" \
          --port "${SWAKS_MAIL_PORT}" \
          --auth-user "${SWAKS_MAIL_USER}" \
          --auth-password "${SWAKS_MAIL_PASSWORD}" \
          --header "Subject: ${subject}" \
          --body "${message}" \
          &> /dev/null
          
    local exit_code=$?
    
    if [ ${exit_code} -eq 0 ]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks: Successfully send to ${SWAKS_MAIL_TO}"
      return 0
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks: Failed to send, exit code: ${exit_code}"
      return 1
    fi
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks: Failed to send, the system does not have the swaks command installed."
    return 1
  fi
}

# Monitor login events
monitor_login_events() {
  echo "========================================================================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Start monitoring login events, using log source: journalctl"
  echo "========================================================================================================"
  
  journalctl -n 0 -f -u "ssh" -o cat | while read line; do
    process_log_line "$line"
}

# Process each log line
process_log_line() {
  local line="$1"
  local user=""
  local status=""
  local ip=""
  local auth_method=""
  local original_log="$line"
  
  # More comprehensive pattern matching for SSH logins
  if echo "$line" | grep -q "sshd.*Accepted"; then
    user=$(echo "$line" | grep -o "Accepted [^ ]* for [^ ]*" | awk '{print $4}')
    auth_method=$(echo "$line" | grep -o "Accepted [^ ]* for" | awk '{print $2}')
    status="Accepted"
    ip=$(echo "$line" | grep -o "from [0-9.]*" | awk '{print $2}')
  elif echo "$line" | grep -q "sshd.*Failed"; then
    user=$(echo "$line" | grep -o "Failed [^ ]* for [^ ]*" | awk '{print $4}')
    # Handle invalid user cases
    if [ -z "$user" ] && echo "$line" | grep -q "invalid user"; then
      user=$(echo "$line" | grep -o "invalid user [^ ]*" | awk '{print $3}')
    fi
    auth_method=$(echo "$line" | grep -o "Failed [^ ]* for" | awk '{print $2}')
    status="Failed"
    ip=$(echo "$line" | grep -o "from [0-9.]*" | awk '{print $2}')
  # Local login detection
  elif echo "$line" | grep -q "login.*pam_unix"; then
    if echo "$line" | grep -q "session opened"; then
      user=$(echo "$line" | grep -o "session opened for user [^ ]*" | awk '{print $5}')
      status="Accepted"
      auth_method="local"
    elif echo "$line" | grep -q "authentication failure"; then
      user=$(echo "$line" | grep -o "user=[^ ]*" | cut -d'=' -f2)
      status="Failed"
      auth_method="local"
    fi
  fi

  # Send notifications if user login is detected.
  if [ ! -z "$user" ] && [ ! -z "$status" ]; then
    # Create a unique identifier for this log event
    current_log_entry="${user}:${status}:${auth_method}:${ip:-local}:${original_log}"
    
    # Check if this is a duplicate of the last log entry
    if [ "$current_log_entry" = "$LAST_LOG_ENTRY" ]; then
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping duplicate log entry"
      echo "========================================================================================================"
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Detected that $user tried to login in. Status: $status. Method: $auth_method. From: ${ip:-local}"
      
      # Send notification and email
      send_swaks_mail "$user" "$status" "${ip:-local}" "$auth_method" "$original_log"
      
      # Update the cache with this log entry
      LAST_LOG_ENTRY="$current_log_entry"
      
      echo "========================================================================================================"
    fi
  fi
}

# Start monitoring
monitor_login_events

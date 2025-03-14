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

# Function to find the appropriate log file.
find_auth_log() {
  # Common log file locations across different distributions.
  local log_files=(
    "/var/log/auth.log"     # Debian/Ubuntu
    "/var/log/secure"       # RHEL/CentOS/Fedora
    "/var/log/messages"     # Some older systems
    "/var/adm/auth.log"     # Some Unix variants
    "/var/adm/messages"     # Solaris
    "/var/log/syslog"       # Alternative for some systems
  )
  
  for log_file in "${log_files[@]}"; do
    if [ -f "$log_file" ] && [ -r "$log_file" ]; then
      echo "$log_file"
      return 0
    fi
  done
  
  # If we couldn't find a log file, try using journalctl for systemd-based systems.
  if command -v journalctl &> /dev/null; then
    echo "journalctl"
    return 0
  fi
  
  echo ""
  return 1
}

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
  local log_source=$(find_auth_log)
  
  if [ -z "$log_source" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Error: Unable to find available authentication log file"
    echo "========================================================================================================"
    exit 1
  fi
  
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Start monitoring login events, using log source: $log_source"
  echo "========================================================================================================"
  
  if [ "$log_source" = "journalctl" ]; then
    # Use journalctl for systemd-based systems
    journalctl -n 0 -f -u "sshd.service" -o cat | while read line; do
      process_log_line "$line"
    done
  else
    # Use traditional log files
    tail -n 0 -f "$log_source" | while read line; do
      process_log_line "$line"
    done
  fi
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

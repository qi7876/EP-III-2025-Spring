#!/bin/bash

# Swaks mail settings
SWAKS_MAIL_TO="qi7876@outlook.com"  # swaks邮件收件人
SWAKS_MAIL_FROM="2023010905015@std.uestc.edu.cn"  # swaks邮件发件人
SWAKS_MAIL_SERVER="mail.std.uestc.edu.cn"  # swaks邮件服务器
SWAKS_MAIL_PORT="25"  # swaks邮件服务器端口
SWAKS_MAIL_USER="2023010905015@std.uestc.edu.cn"  # swaks邮件用户名
SWAKS_MAIL_PASSWORD=""  # swaks邮件密码

# Wechat
WECHAT_CORPID=""  # 企业微信 CorpID
WECHAT_CORPSECRET="" # CorpSecret
WECHAT_AGENTID="" # AgentId

# Function to find the appropriate log file
find_auth_log() {
  # Common log file locations across different distributions
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
  
  # If we couldn't find a log file, try using journalctl for systemd-based systems
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
  local message="用户 ${user} ${status} 登录，IP/终端：${ip}"
  local subject="[系统通知]登录事件"
  
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
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks邮件: 成功发送到 ${SWAKS_MAIL_TO}"
      return 0
    else
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks邮件: 发送失败，退出码: ${exit_code}"
      return 1
    fi
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Swaks邮件: 发送失败，系统未安装swaks命令"
    return 1
  fi
}

# Send Wechat
send_wechat_message() {
  local user="$1"
  local status="$2"
  local ip="$3"
  local message="用户 ${user} ${status} 登录，IP/终端：${ip}"

  access_token=$(curl -s "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=${WECHAT_CORPID}&corpsecret=${WECHAT_CORPSECRET}" | jq -r '.access_token')

  if [ -z "$access_token" ] || [ "$access_token" = "null" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 企业微信通知: 获取 access_token 失败"
    return 1
  fi

  msg_body=$(cat <<EOF
{
   "touser" : "@all",
   "msgtype" : "text",
   "agentid" : ${WECHAT_AGENTID},
   "text" : {
       "content" : "${message}"
   },
   "safe":0
}
EOF
)

  local response=$(curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${access_token}" -d "${msg_body}")
  local errcode=$(echo "$response" | jq -r '.errcode')

  if [ "$errcode" = "0" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 企业微信通知: 成功发送"
    return 0
  else
    local errmsg=$(echo "$response" | jq -r '.errmsg')
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 企业微信通知: 发送失败 - 错误码: $errcode, 错误信息: $errmsg"
    return 1
  fi
}

# Monitor login events
monitor_login_events() {
  local log_source=$(find_auth_log)
  
  if [ -z "$log_source" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 错误: 无法找到可用的认证日志文件"
    exit 1
  fi
  
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始监控登录事件，使用日志源: $log_source"
  
  if [ "$log_source" = "journalctl" ]; then
    # Use journalctl for systemd-based systems
    journalctl -f -u "sshd.service" -o cat | while read line; do
      process_log_line "$line"
    done
  else
    # Use traditional log files
    tail -f "$log_source" | while read line; do
      process_log_line "$line"
    done
  fi
}

# Process each log line
process_log_line() {
  local line="$1"
  
  # 使用 awk 提取信息
  local user=$(echo "$line" | awk '/sshd/ && /Accepted/ {print $9}')
  local status="成功"
  local ip=$(echo "$line" | awk '/sshd/ && /Accepted/ {print $11}')

  if [ -z "$user" ]; then
    user=$(echo "$line" | awk '/sshd/ && /Failed/ {print $9}')
    status="失败"
    ip=$(echo "$line" | awk '/sshd/ && /Failed/ {print $11}')
  fi

  # 如果提取到用户信息，则发送通知
  if [ ! -z "$user" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检测到 $user $status 登录尝试，来自 $ip"
    
    send_swaks_mail "$user" "$status" "$ip"
    # send_wechat_message "$user" "$status" "$ip"
    
    echo "----------------------------------------------"
  fi
}

# Start monitoring
monitor_login_events

# 工程实践创新项目 III 任务一实验报告

**第一小组**

| 成员 | 任科吉        | 汪琦          | 熊昱晶        |
| ---- | ------------- | ------------- | ------------- |
| 学号 | 2023270903008 | 2023010905015 | 2023310101020 |

**指导教师：郝家胜**

## 一、实验项目名称

基于 Linux 命令和 Shell 脚本实现的用户登陆实时监测通知

## 二、任务完成摘要

本实验项目旨在基于 Linux 命令和 Shell 脚本，实现对用户登录行为的实时监测，并在检测到登录事件时立即发送邮件通知。我们完成了以下关键任务：

1. 实现了 SSH 远程登录的实时监测：通过 `journalctl` 命令结合 `grep` 过滤，实时监听 SSH 日志，捕获用户 SSH 远程登录的成功和失败事件。
2. 实现了本地控制台登录的实时监测：利用 `inotifywait` 命令高效监控 `/var/log/secure` 日志文件的修改，并结合 `tail` 和 `grep` 命令，识别本地控制台登录事件。
3. 完成邮件自动推送功能：采用 `swaks` 命令行工具，配置 SMTP 服务器，编写 Shell 函数实现了登录事件的邮件自动推送通知，邮件内容包含登录用户、状态、登录方式、IP 地址、时间和原始日志等详细信息。
4. 解决运行中遇到的问题：针对脚本启动时推送历史信息和重复推送邮件的问题，通过优化 `journalctl` 命令参数和引入日志去重机制，解决了上述问题。
5. 实现了开机自启动配置：通过编写 `systemd` 服务 unit 文件，并使用 `systemctl` 命令进行管理，成功配置了登录监测脚本的开机自启动。
6. 实验测试：设计了本地登录成功/失败、SSH 登录成功/失败等多种测试，验证了用户登录实时监测通知系统的可靠性。

## 三、实验原理

1. `journalctl` 是用于查询和显示 systemd 日志管理器 `journald` 收集的日志数据的命令行工具。
1. `/var/log/auth.log` 是 Linux 系统中记录用户身份验证和授权相关事件 (例如用户登录、sudo 命令使用等) 的关键安全日志文件。
1. `inotifywait` 是一个命令行工具，用于等待 `inotify` 文件系统事件并输出事件信息，常用于监控文件或目录的修改、访问等操作。
1. `swaks` (Swiss Army Knife SMTP) 是一款强大的命令行 SMTP 工具，用于发送、测试和验证电子邮件，支持各种 SMTP 功能和选项，常用于邮件系统调试和性能测试。
1. Systemd 服务是 Linux 系统中由 systemd 初始化和管理的基本单元，用于定义和控制后台进程 (daemons) 的运行方式，包括启动、停止、重启和监控等生命周期管理。

## 四、实验目标

利用 Linux 命令和 Shell 脚本，实时监测用户登陆情况，自动立即推送

## 五、实验内容

1. 检测登录日志；
2. 邮件自动推送通知；
3. 配置开机自启动。

## 六、实验器材

1. Openeuler 开发环境；
2. Bash 终端；
3. Linux 中的常用命令。

## 七、实验步骤

### 1 监测登录日志
#### 1.1 监测 SSH 远程登录

- 方法：

  - 使用 `journalctl -u sshd -o cat -f` 实时监听 SSH 日志；
  - 用 `grep` 过滤出 `Accepted password` 和 `Failed password`。

- 代码：
  ```bash
  journalctl -u sshd -o cat -f | grep --line-buffered -E "Accepted 	password|Failed password" | while read line; do
  	process_ssh_log "$line"
  done &
  ```
- 分析：

  - 先是监听 `sshd` 相关日志，`-f` 选项表示持续跟踪，`-o cat` 选项简化日志格式，方便 `grep` 解析；
  - `grep --line-buffered -E "Accepted password|Failed password"` 过滤出成功或失败的 SSH 登录事件

- SSH 登录所监测的日志附图
  [![pEaQaz8.png](https://s21.ax1x.com/2025/03/14/pEaQaz8.png)](https://imgse.com/i/pEaQaz8)

#### 1.2 监测本地控制台登录

- 方法：
  - 监听 `/var/log/secure` 本地登录日志；
  - 使用 `inotifywait` 代替 `tail -f`，提高时效性；
  - 筛选 `ROOT LOGIN ON tty` 和 `FAILED LOGIN`，过滤成功和失败的事件。
- 代码：
  ```bash
  inotifywait -m -e modify /var/log/secure | while read path action file; do
      tail -n 1 /var/log/secure | grep -E "ROOT LOGIN ON tty|pam_unix\(login:session\): session opened|FAILED LOGIN" | while read line; do
          process_local_log "$line"
      done
  done &
  ```
- 分析：
  - `inotifywait -m -e modify /var/log/secure` 实时监听 `/var/log/secure`，当日志文件被修改时触发事件；
  - `tail -n 1 /var/log/secure | grep -E "ROOT LOGIN ON tty|pam_unix\(login:session\): session opened|FAILED LOGIN"` 保证只获取最新的一行日志，避免了 `tail -f` 的重复读取问题，然后过滤出本地登录的成功和失败的事件。

- 本地登录所监测的日志附图：
  [![pEaQ2WV.png](https://s21.ax1x.com/2025/03/14/pEaQ2WV.png)](https://imgse.com/i/pEaQ2WV)

### 2 邮件自动推送通知

- 使用 `swaks` 命令，通过 SMTP 服务器发送邮件：

  ```bash
  swaks --to "管理员邮箱" --from "来自" --server "SMTP 服务器" --auth-user "用户" --auth-password "密码" --body "通知内容"
  ```

- 代码：

  ```bash
  send_swaks_mail() {
      local user="$1"
      local status="$2"
      local ip="$3"
      local auth_method="$4"
      local original_log="$5"
  
      local message="SSH/Login Notification:\n\n"
      message+="User: ${user}\n"
      message+="Status: ${status}\n"
      message+="Auth Method: ${auth_method}\n"
      message+="IP: ${ip}\n"
      message+="Time: $(date '+%Y-%m-%d %H:%M:%S')\n\n"
      message+="Log Entry:\n${original_log}\n\n"
  
      swaks --to " " \
            --from " " \
            --server " " \
            --port " " \
            --auth-user " " \
            --auth-password " " \
            --header "Subject: SSH/Login ${status} - User: ${user}" \
            --header "Content-Type: text/plain; charset=UTF-8" \
            --body "${message}" \
            --tls \
            &> /tmp/swaks_log.txt
  }
  ```
- 分析：
  - `swaks --to "email@example.com"` 设置收件人邮箱；
  - `--server " " --port " "` 设置使用的服务器和端口；
  - `--auth-user` 和 `--auth-password` 提供邮箱账号和授权码 (如果是 QQ 邮箱的话则需要授权码)；
  - `--body "${message}"` 里面表示邮件内容包括了：用户、状态、登录方式、IP、时间、原始日志。


### 3 解决遇到的问题

#### 3.1 脚本启动时推送历史信息

- 问题：在启动脚本时，脚本会自动推送历史日志中最近的推送记录。
- 分析：`journalctl -u sshd -o cat -f` 会输出一些历史日志，造成了该问题。
- 解决方案：把 `journalctl -u sshd -o cat -f` 修改成 `journalctl -n 0 -u sshd -o cat -f`，加入 `-n 0` 使其不加载历史日志，仅监听新的日志。

#### 3.2 推送重复邮件

- 问题：当检测到一条日志时，有时会重复发送多条相同邮件。
- 分析：由于检测速度过快，可能新日志还未产生，旧日志就被多次重复检测。

- 解决方案：
  - 记录已经发送的日志，防止重复邮件；
  - 维护 ```/tmp/last_ssh_log.txt``` 和 ```/tmp/last_local_log.txt``` 文件。
- 代码：
  ```bash
  if grep -Fxq "$line" "/tmp/last_ssh_log.txt" 2>/dev/null; then
      echo "[DEBUG] Duplicate SSH log detected, skipping email."
      return
  fi
  echo "$line" > "/tmp/last_ssh_log.txt"
  ```
- 分析：
  - `grep -Fxq "$line" "/tmp/last_ssh_log.txt"` 检查是否已经发送过这个日志内容；
  - `echo "$line" > "/tmp/last_ssh_log.txt"` 记录最新的日志，防止下一次重复发送。


### 4 设定开机自启动
#### 4.1 创建 ```systemd``` 服务

- 代码：
	```
	sudo nano /etc/systemd/system/report_login.service
	```
	添加内容：
	```bash
	[Unit]
	Description=Monitor SSH and Local Logins
	After=network.target
	
	[Service]
	ExecStart=/root/report_login.sh
	Restart=always
	User=root
	
	[Install]
	WantedBy=multi-user.target
	```
- 分析：
  - `Description` 指令用于设置服务的描述信息，方便用户理解该服务的功能。
  - `After` 指令定义了当前服务应该在哪个 target 之后启动。
  - `ExecStart` 指令定义了服务启动时要执行的主要命令或脚本。
  - `Restart` 指令定义了服务在退出后是否需要自动重启以及重启策略。
  - `User` 指令定义了运行服务进程的用户身份。
  - `WantedBy` 指令定义了当前服务希望被哪个 target “需要”，从而决定了服务在系统启动时的启动时机。`multi-user.target` 是 systemd 中一个常用的 target，它代表多用户、非图形界面的系统运行级别，通常在系统启动到可以进行用户登录的阶段。

#### 4.2 启动服务

- 代码：
  ```
  sudo systemctl daemon-reload
  sudo systemctl enable report_login.service
  sudo systemctl start report_login.service
  sudo systemctl status report_login.service
  ```
- 分析：
  - `sudo systemctl daemon-reload`：重新加载 systemd 的守护进程管理器配置，使得 systemd 能够识别新安装或修改过的 unit 文件。
  - `sudo systemctl enable report_login.service`：启用 `report_login.service` 服务，使其在系统启动时自动启动。
  - `sudo systemctl start report_login.service`：立即启动 `report_login.service` 服务。
  - `sudo systemctl status report_login.service`：查看 `report_login.service` 服务的当前状态，包括是否正在运行、进程 ID、启动时间、日志信息等。


## 八、实验数据及结果分析

| **测试场景** | **预期效果** | **实际效果** |
| :----------- | :----------- | :----------- |
| 本地登录成功 | 发送一次邮件 | 发送一次邮件 |
| 本地登录失败 | 发送一次邮件 | 发送一次邮件 |
| 首次SSH失败  | 发送一次邮件 | 发送一次邮件 |
| 首次SSH失败  | 发送一次邮件 | 发送一次邮件 |
| 新建SSH失败  | 发送一次邮件 | 发送一次邮件 |
| 新建SSH成功  | 发送一次邮件 | 发送一次邮件 |

**实际接收到的邮件截图 (顺序按照上述六种情况)：**
[![pEaQiMF.jpg](https://s21.ax1x.com/2025/03/14/pEaQiMF.jpg)](https://imgse.com/i/pEaQiMF)

## 九、实验结论

本次实验成功设计并实现了一个基于 Linux 命令和 Shell 脚本的用户登录实时监测通知系统。实验结果表明，该系统能够准确监测 SSH 远程登录和本地控制台登录两种用户登录场景，并在第一时间通过邮件发送登录通知。在各种测试场景下，系统均能稳定可靠地按照预期效果运行，及时发送邮件通知，保证了登录事件的实时告警。

## 十、总结及心得体会

### 总结

本次实验项目成功地基于 Linux 命令和 Shell 脚本，构建了一套用户登录实时监测通知系统，能够实时监测 SSH 远程登录和本地控制台登录事件，并在检测到登录行为后立即通过邮件发出通知。为了实现这一目标，我们学习和应用了 `journalctl`、`inotifywait`、`swaks` 等关键 Linux 命令，并掌握了 systemd 服务的配置方法。通过解决历史信息推送和邮件重复发送两个问题，我们提升了系统的稳定性，最终达到了预期的实验目标。

### 心得体会

#### 1 从 `mailx` 迁移到 `swaks` 解决邮件发送报错

- 问题：最初采用比较常用的 `mailx` 发送邮件。虽然每次成功发送邮件，并且目标邮箱成功收到邮件，但是会返回 `message not sent` 错误，导致脚本无法判断邮件是否真的发送成功，影响后续的调试。具体情况如附图所示，虽然实际收到了邮件，但是返回为未发送。
  [![pEalmwj.png](https://s21.ax1x.com/2025/03/14/pEalmwj.png)](https://imgse.com/i/pEalmwj)

- 分析：

   - 在某些 Linux 发行版中，`mailx` 会默认使用 `Sendmail/Postfix` 作为邮件代理，可能底层部件的配置出现了问题；
   - 对于服务器，如果没有完整配置 SMTP，也可能导致成功投递到邮件服务器，但是 SMTP 认证失败，或者邮件确实成功发送，但 `mailx` 误判成失败。
   - `mailx` 缺少明确的 SMTP 交互反馈，错误不好查明。

- 解决方案：采用 `swaks`，它直接与 SMTP 服务器通信，不依赖于本地 `Sendmail/Postfix`，并且返回详细的 SMTP 交互日志，方便调试，支持 SSL/TLS 加密连接，适用于 Gmail、QQ 等云端邮箱，还支持身份验证，可以兼容各种邮件服务器。

- 改进：

   -  邮件日志可以追朔 `/tmp/swaks_log.txt`，如果失败，可以排查是认证失败，还是 SMTP 服务器拒收，还是 TLS 连接失败；

   -  解决了 ```message not sent``` 的误判，返回了明确的服务器响应

      ```bash
      if swaks ... &> /tmp/swaks_log.txt; then
      	echo "Email sent successfully!"
      else
      	echo "Email sending failed!"
      	cat /tmp/swaks_log.txt
      fi
      ```
   

#### 2 寻找 SSH 登录 IP 的正确日志

- 问题：原本预期 SSH 的 IP 会记录在 ```/var/log/secure```，但发现里面没有 IP 信息，经查找后发现只有 ```journalctl``` 里的 ```sshd``` 相关日志才包含 IP 地址

- 分析：

    - `/var/log/secure` 只记录认证过程，而不记录完整的 SSH 连接信息。其记录的内容为：本地登录 (`ROOT LOGIN ON tty`) 和 SSH 认证 (`pam_unix(login:session): session opened`)，而缺失了 IP 地址；内容仅包含了登录是否成功，例如：`Mar 14 12:30:01 server sshd[1234]: Accepted password for user1`；

    - `journalctl -u sshd` 记录完整的 SSH 连接日志，包括 IP。正确的 SSH 连接信息存储在 `systemd` 的日志系统中，而不是 `/var/log/secure`，例如：`Mar 14 12:30:01 server sshd[1234]: Accepted password for user1 from 192.168.1.100 port 56789 ssh2`

- 解决方案：

    - 使用 `journalctl -u sshd -o cat -f` 实时监测 SSH 登录

    - 提取 IP：

        ```bash
        journalctl -u sshd -o cat -f | grep --line-buffered -E "Accepted password|Failed password" | while read line; do
        	process_ssh_log "$line"
        done &
        ```

    - 解析 SSH 登录日志，例如：`Mar 14 12:30:01 server sshd[1234]: Accepted password for user1 from 192.168.1.100 port 56789 ssh2`；

    - 提取 IP：`ip=$(echo "$line" | awk '{for(i=1;i<=NF;i++) if($i=="from") print $(i+1)}')`
>查找求证后得知，出现这个问题的根本原因是不同 Linux 版本的日志管理机制不同。
>
>现代 Linux 采用 systemd 作为默认的初始化系统，它管理服务 (包括 sshd)，并接管了日志存储，因此 SSH 登录的详细日志 (包含 IP 地址) 被 systemd-journald 记录，而不是被储存在传统的/var/log/secure 中，而在老版本 Linux (如 CentOS 6、RHEL 6) 或未使用 systemd 的 Linux 中，日志系统通常由 syslog 或 rsyslog 管理，SSH 登录日志默认存入/var/log/secure。
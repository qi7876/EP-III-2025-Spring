# ROS 双节点

运行命令进行部署

```
docker build -t ros_with_tutorials .
docker compose up -d
```

![Screenshot 2025-04-12 at 21.00.59](http://image-bed-qi7876.oss-cn-chengdu.aliyuncs.com/image/Screenshot%202025-04-12%20at%2021.00.59.png)

查看日志

```
docker logs ros-talker-1 -n 5
docker logs ros-listener-1 -n 5
```

![Screenshot 2025-04-12 at 20.58.01](http://image-bed-qi7876.oss-cn-chengdu.aliyuncs.com/image/Screenshot%202025-04-12%20at%2020.58.01.png)
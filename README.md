# DG-LAB-V3-SOCKET-To-V2-BLE
### DG-LAB-E-STIM-Power-Box-V3-SOCKET-Protocol-To-V2-Bluetooth-Protocol-Converter

# 该项目已重构，具体信息请点击[此处](/Reconstruction-Announcement.md)查看。

## 介绍：

这是一个 Python 脚本，用于让2.0主机支持 socket 控制

## 需要安装的依赖列表：

 - Python 3.6+
 - PySide6
 - qasync
 - websockets
 - bleak
 - pyqtgraph

###### *离线编译构建在计划中，以后可能不再需要安装依赖和使用终端命令行启动*

### 安装指令：

```bash
pip install pyside6 qasync websockets bleak pyqtgraph
```

## 预览图：

![PV1 0 0semver](https://github.com/user-attachments/assets/c89893bb-31cb-4d10-a38f-d178d345a2b5)

## ToDoList：

 - [x] 修复回调数据（有待验证）
 - [ ] 修复重新扫描设备时的错误
 - [ ] 手动控制：测试增加强度后等待10秒自动清零强度
 - [ ] 添加更多语言
 - [ ] 添加检查更新和自动更新
 - [ ] 添加开源许可证

## 辅助工具：

[在线QR码识别器](https://cli.im/deqr)

## 使用的文档：

[郊狼官方V2蓝牙协议支持文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/coyote/v2/README_V2.md)

[郊狼官方V3蓝牙协议支持文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/coyote/v3/README_V3.md)

[郊狼官方SOCKETV3控制协议支持文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/socket/README.md)

## 其他杂项：

[介绍和教程视频](https://www.bilibili.com/video/BV1uMQzYaEZK/)

# 为防止郊狼官方给我寄律师函，声明一下：本项目作者完全理解并认同官方仓库中的“禁止商用”条款，本项目作者绝对不会以及强烈反对将该项目的任何一切资源（包括但不限于代码、文档、图片等）用于商业用途，如果官方发现该项目的任何资源被用于了商业用途，绝非本项目作者指使/协助/支持，请勿制裁我，可直接制裁将该项目资源用于商业用途的人

~~注：该脚本编写时用到了人工智能，如果您反感或看不起使用人工智能编写代码的人，请勿使用该脚本~~

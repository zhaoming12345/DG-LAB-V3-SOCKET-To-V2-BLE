# DG-LAB-V3-SOCKET-To-V2-BLE
### DG-LAB-E-STIM-Power-Box-V3-SOCKET-Protocol-To-V2-Bluetooth-Protocol-Converter

## 介绍：

这是一个简单的Python脚本，用于让2.0主机支持socket控制

它目前还有许多问题，比如当前强度数据没有回传到服务器等等，总之，欢迎提出pr

## 需要安装的依赖列表：

 - Python 3.7+

 - PySide6

 - qasync

 - websockets

 - bleak

### 安装指令：

```bash
pip install pyside6 qasync websockets bleak
```

## 预览图：

![PV](https://github.com/user-attachments/assets/34605fe6-b148-4664-a574-34d16e75a0a2)

## ToDoList：

 - [ ] 控制台和指令输入支持
 - [ ] 波形显示
 - [ ] 保存配置和配置文件
 - [ ] 修复回调数据
 - [ ] 显示设备电池电量
 - [ ] 深色模式

## 辅助工具：

[在线QR码识别器](https://cli.im/deqr)

## 使用的文档：

[郊狼官方V2蓝牙协议支持文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/coyote/v2/README_V2.md)

[郊狼官方V3蓝牙协议支持文档](https://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/coyote/v3/README_V3.md)

[郊狼官方SOCKETV3控制协议支持文档](socket/README.mdhttps://github.com/DG-LAB-OPENSOURCE/DG-LAB-OPENSOURCE/blob/main/socket/README.md)

## 其他杂项：

[介绍和教程视频](https://www.bilibili.com/video/BV1uMQzYaEZK/)

~~注：该脚本编写时用到了deepseek，如果您反感或看不起使用人工智能编写代码的人，请勿使用该脚本~~

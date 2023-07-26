#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project：     sonarGUI 
@File：        decodeThread.py
@Author：      wzj
@Description:  数据解析线程：
                1. 解析txt文件并产生raw图片流
                2. 解析udp包并产生raw图片流
               当数据源选择为raw_data或探鱼仪实时数据时，此线程启动；选择其它数据源时，此线程终止。
@Created：     2023/7/18
@Modified:     
"""

from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal
from modules.logger import Logger
import numpy as np
import cv2
import os
import time


class DecodeThread(QThread):
    send_raw = pyqtSignal(np.ndarray)   # raw图片流;  decode线程只send_raw，不send_img
    send_msg = pyqtSignal(str)          # 状态栏更新、打印日志等
    send_percent = pyqtSignal(int)      # 播放进度
    send_fps = pyqtSignal(str)          # fps

    def __init__(self):
        super(DecodeThread, self).__init__()
        self.source = '0'
        self.raw_screen_size = [800, 1048]      # [height, width]
        self.raw_img_size = [800, 1048]         # [height, width]
        self.jump_out = False
        self.is_continue = True
        self.speed = 0

    # 输入文件转为mat
    def file_to_mat(self, file_name, start_line, read_row_num):
        pass

    # run函数
    def run(self):
        try:
            # load data
            if self.source.lower().endswith(".txt"):
                self.send_msg.emit('decode_thread >> 当前加载的是txt文件')
            else:
                self.send_msg.emit('decode_thread >> 当前加载的不是txt文件')

            while True:
                if self.jump_out:
                    if hasattr(self, 'out'):
                        self.out.release()
                    self.send_msg.emit('decode_thread >> jump_out')
                    break

                if self.is_continue:
                    pass

        except Exception as e:
            self.send_msg.emit('%s' % e)

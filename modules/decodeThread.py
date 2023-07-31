#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project：     sonarGUI 
@File：        decodeThread.py
@Author：      wzj
@Description:  通过队列实现生产者线程、消费者线程之间的通信。数据解析线程为生产者，目标检测线程为消费者.
                Ref >> https://www.cnblogs.com/Triomphe/p/12729644.html
                       https://geek-docs.com/pyqt/pyqt-questions/184_pyqt_communication_between_threads_in_pyside.html
                本线程功能：
                1. 解析txt文件并产生raw图片，放入img_queue
                2. 解析udp包并产生raw图片，放入img_queue
               当数据源选择为raw_data或探鱼仪实时数据时，此线程启动；选择其它数据源时，此线程终止。
@Created：     2023/7/18
@Modified:     
"""
import math

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from modules.logger import Logger
import numpy as np
import cv2
import os
import time
import math


class DecodeThread(QThread):
    send_msg = pyqtSignal(str)          # 状态栏更新、打印日志等
    send_percent = pyqtSignal(int)      # 播放进度
    send_fps = pyqtSignal(str)          # fps

    def __init__(self, img_queue):
        super(DecodeThread, self).__init__()
        self.source = '0'
        self.screen_size = [800, 1400]          # [height, width]
        self.raw_img = np.zeros((800, 1400, 3), dtype=np.uint8)
        self.current_path = '0'                 # 已缓存的原始数据路径
        self.data_buffer = np.zeros((800, 20000, 3), dtype=np.uint8)  # 原始数据缓存
        self.total_line_num = 0                 # 数据缓存中有效列数
        self.percent_length = 0                 # 进度条
        self.total_line_num_dec_percent = 0     # 总列数的1/percent_length（为加快计算速度而单独拎出来）
        self.jump_out = False
        self.is_continue = True
        self.speed = 0                          # 控制帧速，取值：0,1
        self.next_start_line = 0                # 下一帧图片在data_buffer中的首行行号
        self.img_queue = img_queue
        self.color_bar = {                      # index值到color的映射字典（index=data/20），注意：排序为RGB
                                                # Ref >> https://www.sioe.cn/yingyong/yanse-rgb-16/
            0: (112, 25, 25),       # 午夜蓝
            1: (225, 105, 65),      # 皇家蓝
            2: (237, 149, 100),     # 矢车菊蓝
            3: (255, 255, 0),       # 青色
            4: (209, 206, 0),       # 深绿宝石
            5: (50, 205, 50),       # 酸橙绿
            6: (47, 255, 173),      # 绿黄色
            7: (0, 255, 255),       # 纯黄
            8: (0, 165, 255),       # 橙色
            9: (80, 127, 255),      # 珊瑚
            10: (0, 69, 255),       # 橙红色
            11: (92, 92, 205),      # 印度红
            12: (0, 0, 255),        # 纯红
            13: (34, 34, 178),      # 耐火砖
            14: (0, 0, 139),        # 深红色
            15: (0, 0, 128)         # 栗色

            # 0: (90, 90, 90),
            # 1: (100, 100, 100),
            # 2: (110, 110, 110),
            # 3: (120, 120, 120),
            # 4: (130, 130, 130),
            # 5: (140, 140, 140),
            # 6: (150, 150, 150),
            # 7: (160, 160, 160),
            # 8: (170, 170, 170),
            # 9: (180, 180, 180),
            # 10: (190, 190, 190),
            # 11: (200, 200, 200),
            # 12: (210, 210, 210),
            # 13: (220, 220, 220),
            # 14: (230, 230, 230),
            # 15: (240, 240, 240)
        }

    # 将数据文件加载至内存
    def load_data_to_mem(self):
        with open(self.source, 'r') as f:
            lines = f.readlines()
            if len(lines) < 20000:      # 最多缓存20000行
                self.total_line_num = len(lines) - 1
            else:
                self.total_line_num = 19999
        self.total_line_num_dec_percent = math.floor(self.total_line_num/self.percent_length)

        for i in range(self.total_line_num):
            line_str = lines[i]
            pkg_len = int(line_str[14:16], 16)*256 + int(line_str[12:14], 16)      # 大小端反转
            for j in range(pkg_len):
                data_tmp = int(line_str[18+j*4:20+j*4], 16)*256 + int(line_str[16+j*4:18+j*4], 16)
                if data_tmp > 2000:
                    index = int((data_tmp-2000)/2000.0*16)
                else:
                    index = 0
                self.data_buffer[j, i, :] = self.color_bar[index]

    def progress_slider_changed(self, x):
        print('progress_slider_changed >> %d' % x)
        self.next_start_line = self.total_line_num_dec_percent * x

    # run函数
    def run(self):
        # 加载数据至内存
        if self.source.lower().endswith(".txt"):
            if self.current_path != self.source:
                self.current_path = self.source
                self.send_msg.emit('decode_thread >> 数据加载中')
                self.load_data_to_mem()
                self.send_msg.emit('decode_thread >> 数据源变更为' + self.source)

        try:
            while True:
                if self.jump_out:
                    if hasattr(self, 'out'):
                        self.out.release()
                    self.send_msg.emit('decode_thread >> jump_out')
                    break

                if self.is_continue:
                    self.msleep(50)
                    self.raw_img = self.data_buffer[:, self.next_start_line:self.next_start_line+1399, :]
                    if self.next_start_line < self.total_line_num - 1400:
                        self.next_start_line += 1
                        if self.next_start_line % self.total_line_num_dec_percent == 0:
                            self.send_percent.emit(int(self.next_start_line / self.total_line_num_dec_percent))
                        # print('进度 %d ' % int(self.next_start_line / self.total_line_num_dec_percent))
                    else:
                        self.next_start_line = 0
                        self.send_percent.emit(self.percent_length)
                        break

                    self.img_queue.put(self.raw_img)
                    # print('decode_thread.run() >> 当前队列长度 %d\n' % self.img_queue.qsize())

        except Exception as e:
            self.send_msg.emit('decode_thread.run() >> %s' % e)

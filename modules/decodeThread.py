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
        self.pkg_len = 0                        # 包长度
        self.raw_img = np.full((800, 1400, 3), [65,65,65], dtype=np.uint8)
        self.current_path = '0'                 # 已缓存的原始数据路径
        self.data_tmp_buffer = np.zeros((800, 20000), dtype=np.int16)    # 原始数据缓存
        self.total_line_num = 0                 # 数据缓存中有效列数
        self.percent_length = 0                 # 进度条
        self.total_line_num_dec_percent = 0     # 总列数的1/percent_length（为加快计算速度而单独拎出来）
        self.jump_out = False
        self.is_continue = True
        self.gain = 60                          # 数字增益
        self.speed = 2                          # 控制帧速，1表示x轴方向每帧前进1像素，以此类推
        self.new_line_num = 0                   # 下一帧图片是当前帧左移self.speed行，再用新数据填充最后self.speed行。
                                                # self.new_line_num为新数据第一行在的self.data_tmp_buffer中的行号
        self.img_queue = img_queue
        self.color_bar = {                      # index值到color的映射字典（index=data/20），注意：排序为BGR
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
            15: (0, 0, 128),         # 栗色
            16: (0, 0, 50)          # max
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
            if i == 0:
                self.send_msg.emit('decode_thread >> 数据加载中：0%')
            elif i % math.floor(self.total_line_num/10) == 0:
                tmp = int(i*10 / math.floor(self.total_line_num/10))
                self.send_msg.emit('decode_thread >> 数据加载中：' + str(tmp) + '%')

            line_str = lines[i]
            self.pkg_len = int(line_str[14:16], 16)*256 + int(line_str[12:14], 16)      # 大小端反转

            for j in range(self.pkg_len):
                self.data_tmp_buffer[j,i] = int(line_str[18+j*4:20+j*4], 16)*256 + int(line_str[16+j*4:18+j*4], 16)

        print('max:' + str(np.max(self.data_tmp_buffer)))

    def progress_slider_changed(self, x):
        self.new_line_num = self.total_line_num_dec_percent * x + 1399
        print('progress_slider_changed: self.new_line_num: ' + str(self.new_line_num))

    # run函数
    def run(self):
        # 加载数据至内存
        if self.source.lower().endswith(".txt"):
            if self.current_path != self.source:
                self.current_path = self.source
                self.load_data_to_mem()
                file_name = os.path.split(os.path.splitext(self.source)[0])[-1] + os.path.splitext(self.source)[-1]    # 获取不带路径的文件名
                self.send_msg.emit('decode_thread >> 历史文件回放中：' + file_name)

        try:
            count = 0
            start_time = time.time()

            while True:
                if self.jump_out:
                    if hasattr(self, 'out'):
                        self.out.release()
                    break

                if self.is_continue:
                    self.msleep(50)
                    if self.new_line_num + self.speed < self.total_line_num:
                        self.new_line_num += self.speed
                        if self.new_line_num % self.total_line_num_dec_percent == 0:
                            self.send_percent.emit(int(self.new_line_num / self.total_line_num_dec_percent))
                    else:
                        self.new_line_num = 0
                        self.send_percent.emit(self.percent_length)
                        break

                    denominator = np.max(self.data_tmp_buffer) * self.gain / 100  # 阈值为max的一定比例
                    threshold = np.max(self.data_tmp_buffer) - denominator

                    # 将raw_img左移
                    self.raw_img[:, :1399-self.speed, :] = self.raw_img[:, self.speed:1399, :]
                    # 填充末尾行
                    for i in range(self.new_line_num, self.new_line_num+self.speed):
                        # print('i=' + str(i) + ',  new_line_num=' + str(self.new_line_num))
                        for j in range(self.pkg_len):
                            if self.data_tmp_buffer[j, i] > threshold:
                                index = int((self.data_tmp_buffer[j, i] - threshold) / denominator * 16)
                            else:
                                index = 0
                            self.raw_img[j, i-self.new_line_num+1399-self.speed, :] = self.color_bar[index]

                    self.img_queue.put(self.raw_img)
                    # print('decode_thread.run() >> 当前队列长度 %d\n' % self.img_queue.qsize())
                    count += 1
                    if count % 10 == 0 and count >= 10:
                        fps = int(10 / (time.time() - start_time))
                        self.send_fps.emit('FPS: ' + str(fps) + ' ')
                        start_time = time.time()

        except Exception as e:
            self.send_msg.emit('decode_thread.run() >> %s' % e)

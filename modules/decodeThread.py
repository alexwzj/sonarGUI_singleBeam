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

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
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

    def __init__(self, img_queue):
        super(DecodeThread, self).__init__()
        self.source = '0'
        self.raw_screen_size = [800, 1048]      # [height, width]
        self.raw_img_size = [800, 1048]         # [height, width]
        self.jump_out = False
        self.is_continue = True
        self.speed = 0                          # 控制帧速，取值：0,1
        self.cnt_time = 0
        self.img_queue = img_queue

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
                    self.msleep(10)
                    self.cnt_time = self.cnt_time + 1
                    origin_img = cv2.imread('results/fmiri.jpg')

                    mean = 0        # 设置高斯分布的均值和方差
                    sigma = 100     # 设置高斯分布的标准差
                    gauss = np.random.normal(mean, sigma, (768, 1024, 3))   # 根据均值和标准差生成符合高斯分布的噪声
                    noisy_img = origin_img + gauss      # 给图片添加高斯噪声
                    noisy_img = np.clip(noisy_img, a_min=0, a_max=255)      # 设置图片添加高斯噪声之后的像素值的范围
                    noisy_img = noisy_img.astype(np.uint8)                  # 数据类型改为opencv支持的类型
                    self.img_queue.put(noisy_img)

        except Exception as e:
            self.send_msg.emit('%s' % e)

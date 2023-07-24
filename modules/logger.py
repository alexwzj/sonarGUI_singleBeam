#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project：     sonarGUI
@File：        logger.py
@Author：      wzj
@Description:  日志类
@Created：     2023/7/18
@Modified:
"""

# logger.py

import time
import os
import logging
from logging import handlers


formater = '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'


# 路径管理
def log_path_check():
    log_path = os.getcwd() + '/logs/'
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    day = time.strftime('%Y-%m-%d', time.localtime())
    log_name = log_path + day + '.log'
    return log_name


class Logger(object):
    def __init__(self, filename=log_path_check(), when='D', backCount=3, fmt=formater):
        self.logger = logging.getLogger()
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        self.logger.setLevel(logging.NOTSET)
        # 往文件中输出
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount, encoding='GBK')
        # 设置handler级别
        th.setLevel(logging.NOTSET)
        # 往文件里写入#指定间隔时间自动生成文件的处理器
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时
        # D 天
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)
        # 设置文件里写入的格式
        self.logger.addHandler(th)  # 把对象加到logger里


if __name__ == '__main__':
    log = Logger('all.log', level='debug')
    log.logger.debug('debug')
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.critical('严重')
    Logger('error.log', level='error').logger.error('error')

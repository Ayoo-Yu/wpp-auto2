#!/usr/bin/env python3
# 简单的测试脚本，用于验证PM2能否正确启动

import time
import os
import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_script.log')
    ]
)

logger = logging.getLogger('test_script')

# 记录脚本启动信息
logger.info("测试脚本已启动")
logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"脚本路径: {os.path.abspath(__file__)}")
logger.info(f"环境变量: {dict(os.environ)}")

# 每10秒记录一次时间戳
count = 0
try:
    while True:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"测试脚本正在运行: {current_time}, 计数: {count}")
        count += 1
        time.sleep(10)
except KeyboardInterrupt:
    logger.info("测试脚本被手动停止")
except Exception as e:
    logger.error(f"测试脚本发生错误: {e}", exc_info=True)
finally:
    logger.info("测试脚本已退出") 
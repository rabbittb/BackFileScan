#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import asyncio
import sys
import time
import logging
from urllib.parse import urlparse
import aiohttp

__all__ = ['g']
g = dict()
urls_cache = {}


if sys.platform == 'win32':
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


suffixes = ['.rar', '.zip', '.sql', '.gz', '.sql.gz', '.tar.gz', '.bak', '.sql.bak']

def get_logger():
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y/%d/%m %H:%M:%S %p"
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    logger = logging.getLogger('asyncio')
    return logger


logger = get_logger()


async def request(url, func, **requests):
    async with g['semaphore']:
        netloc = urlparse(url).netloc
        if netloc in urls_cache:
            session = urls_cache.get(netloc)
        if netloc not in urls_cache:
            session = aiohttp.ClientSession()
            urls_cache[netloc] = session
        try:
            async with session.request("GET", url=url, timeout=5, **requests) as response:
                return await func(url, response)
        except Exception as e:
            # logger = get_logger()
            # logger.info(e.args)
            return None


async def session_closed(url): #session close
    netloc = urlparse(url).netloc
    if netloc in urls_cache:
        session = urls_cache.get(netloc)
        await session.close()
        del urls_cache[netloc]


async def selfscan(url, response): # 判断返回内容
    if response.headers.get('Content-Type') and 'text/html' not in response.headers.get(
            'Content-Type') and 'image/' not in response.headers.get('Content-Type'):
        return [url, response.headers.get('Content-Length')]
    return False


async def scan(target_url):
    async with g['semaphore']:
        response = await request(target_url, selfscan)
        if not response:
            return False
        url, size = response
        logger.debug("[*] finded backup file : %s size: %d M" % (url, int(size) // 1024 // 1024))
        return url, size


def get_scanlist_from_url(url: str):#组合字典

    file_dic = ['.git/config', '.svn/entries', 'WEB-INF/web.xml', 'web.rar', 'web.tar.gz', 'wwwroot.gz', 'ftp.rar',
                '__zep__/js.zip', 'flashfxp.rar', 'flashfxp.tar', 'faisunzip.zip', 'ftp.tar.gz',
                'wwwroot.sql', 'www.rar', 'flashfxp.zip', 'ftp.tar', 'data.zip', 'wwwroot.tar', 'www.tar.gz',
                'data.rar', 'admin.rar', 'ftp.zip',
                'web.tar', 'admin.zip', 'www.tar', 'wwwroot.zip', 'admin.tar', 'backup.zip', 'flashfxp.tar.gz',
                'bbs.zip', 'wwwroot.sql.zip',
                'www.zip', 'web.zip', 'wwwroot.rar', 'data.tar', 'admin.tar.gz', 'wwwroot.tar.gz', 'data.tar.gz']

    url = url.replace('http://', '').replace('https://', '')
    host_items = url.split('.')
    for suffix in suffixes:
        file_dic.append("".join(host_items[1:]) + suffix)
        file_dic.append(host_items[1] + suffix)
        file_dic.append(host_items[-2] + suffix)
        file_dic.append("".join(host_items) + suffix)
        file_dic.append(url + suffix)
    return list(set(file_dic))


async def start(url):
    async with g['semaphore']:#信号量 控制总并发量
        tasks = []
        scanlist = get_scanlist_from_url(url)# 字典
        for item in scanlist:
            target_url = url + "/" + item # 组合url
            task = asyncio.Task(scan(target_url))# 添加任务
            tasks.append(task)
        await asyncio.wait(tasks) #  开始协程任务
        await session_closed(url) # 断开
        for task in tasks:
            if task.result():# 获取结果 如果结果不为FALSE 就返回
                return task.result()
        return False# 否则返回FALSE


def main(url_list):#创建任务开始任务
    loop = asyncio.get_event_loop()
    tasks = []
    for url in url_list:
        task = loop.create_task(start(url))#这里不执行
        tasks.append(task)
    loop.run_until_complete(asyncio.wait(tasks))#开始执行


if __name__ == "__main__":
    with open('Log20182917082907.txt','r',encoding='utf-8')as f:
    	urls = f.read()
    	url_list = urls.split('\n')
    print(len(get_scanlist_from_url("http://www.cidp.edu.cn")))
    # now = time.time()
    # g['semaphore'] = asyncio.Semaphore(2000)
    # main(url_list)
    # print(time.time() - now)
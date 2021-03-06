# -*- coding: utf-8 -*-
import scrapy
import time
import json
import urllib3
import random
from os import path
import os
import urllib.parse as ps


class WordbookSpider(scrapy.Spider):
    wl = []
    failedwds = []
    name = 'wordbook'
    allowed_domains = ['www.shanbay.com']
    book = '34'
    file = None
    tmp_fp = None
    succ_fp = None
    successws = []
    proxys = [
        "http://124.207.82.166:8008"
    ]
    proxyManagers = []
    localManager = None

    def randproxy(self):
        if len(self.proxyManagers) > 0:
            return random.choice(self.proxyManagers)
        else:
            return self.localManager

    def start_requests(self):
        url = "http://www.shanbay.com/wordbook/"
        book = getattr(self, 'book', None)  # 获取tag值，也就是爬取时传过来的参数
        if book is not None:
            self.book = book
        url = url + self.book  # 构造url
        file = getattr(self, 'file')
        if file is None:
            self.file = "shanbei_wordbook_" + self.book + ".json"
        else:
            self.file = file
        tmpfile = "shanbei_wordbook_" + self.book + "_tmp.json"
        self.tmp_fp = open(tmpfile, 'a', encoding='utf-8')

        successfile = "shanbei_wordbook_" + self.book + "_success.txt"
        self.succ_fp = open(successfile, 'a', encoding='utf-8')

        # self.successws = self.succ_fp.readlines()

        self.localManager = urllib3.PoolManager(num_pools=5)
        for proxy in self.proxys:
            try:
                if proxy == "" or proxy == "http://127.0.0.1" or "http://localhost":
                    pool = self.localManager
                else:
                    pool = urllib3.ProxyManager(proxy_url=proxy, num_pools=5)
            except Exception as e:
                print("can not conn:", proxy, e)
                continue
            self.proxyManagers.append(pool)

        yield scrapy.Request(url, self.parse)  # 发送请求爬取参数内容

    def parse(self, response):
        ll = response.xpath('//*[@id="wordbook-wordlist-container"]')
        for l in ll:
            wa = l.css('a::attr(href)').extract()
            for w in wa:
                next_page = response.urljoin(w) + "?page=1"
                yield scrapy.Request(next_page, callback=self.parsewds)

    # 避免一次性操作失败,可以分文件存储或者每一次查找到结果后存储到临时文件,最后统一处理格式
    def parsewds(self, response):
        ll = response.xpath('/html/body/div[3]/div/div[1]/div[2]/div/table')
        wl = ll.xpath("//td[@class='span2']/strong//text()").extract()
        for w in wl:
            if w not in self.successws:
                # print(w)
                self.searchword(w)
                time.sleep(0.001)
                # pass
        if len(wl) > 1:
            time.sleep(1)
            ss = response.url.split('page=')
            page = int(ss[len(ss)-1])
            next_page = ss[0] + "page=" + str(page+1)
            yield scrapy.Request(next_page, callback=self.parsewds)

    def searchword(self, w, first=True):
        r = self.randproxy().request("GET", self.makesearchpath(w), retries=2)
        resp = json.loads(r.data, encoding="utf-8")
        # resp = requests.get(self.makesearchpath(w)).json(encoding="utf-8")
        print(resp)
        if resp['status_code'] == 0:
            data = resp['data']
            data['word'] = w
            self.succ_fp.write(w)
            self.succ_fp.write("\n")
            self.wl.append(data)
            json.dump(data, self.tmp_fp, ensure_ascii=False)
            self.tmp_fp.write(",\n")

        else:
            if first:
                self.searchword(w)
            else:
                self.failedwds.append(w)
        print(data)

    def makesearchurl(self, w):
        tm = int(time.time()*1000)
        url = "/api/v1/bdc/search/?version=2&word={}&_={}".format(w, tm)
        return url

    def makesearchpath(self, w):
        tm = int(time.time()*1000)
        path = "http://www.shanbay.com/api/v1/bdc/search/?version=2&word={}&_={}".format(w, tm)
        return path

    def close(self, spider, reason):
        self.wl.sort(key=lambda w: w['word'].lower())
        fp = open(self.file, 'w', encoding='utf-8')
        json.dump(self.wl, fp, ensure_ascii=False, indent=4)
        print("failed words", self.failedwds)
        fp.close()
        super().close(spider, reason)

    def download_audio(self, url, destpath):
        fp = open(destpath, 'wb')
        r = self.randproxy().request('GET', url)
        fp.write(r.data)
        fp.close()

# def reloadjson():
#     file = open('../shanbei_wordbook34_tmp.json', 'r', encoding='utf-8')
#     res = json.load(file)
#     print(res)
#     file2 = open('shanbei_wordbook34.json', 'w')
#     json.dump(res, file2, ensure_ascii=False, indent=4)


def download_audios(book=34):
    pool = urllib3.PoolManager()
    rootdir = "../.."
    filename = path.join(rootdir, 'shanbei_wordbook_{}.json'.format(book))
    file = open(filename, 'r', encoding='utf-8')
    data = json.load(file)

    ukdir = path.join(rootdir, 'audio/{}/uk'.format(book))
    usdir = path.join(rootdir, 'audio/{}/us'.format(book))
    if not path.exists(ukdir):
        os.makedirs(ukdir)
    if not path.exists(usdir):
        os.makedirs(usdir)
    for d in data:
        audio = d['audio_addresses']
        if audio:
            uk = audio['uk']
            us = audio['us']
            if uk:
                audio['uk_local'] = []
                for url in uk:
                    nm = path.basename(ps.unquote(url))
                    host = urllib3.util.parse_url(url).hostname
                    print(nm)
                    try:
                        fn = path.join(ukdir, host + "_" + nm)
                        fp = open(fn, 'wb')
                        r = pool.request('GET', url)
                        fp.write(r.data)
                        audio['uk_local'].append(path.relpath(fn, rootdir))
                    finally:
                        fp.close()
            if us:
                audio['us_local'] = []
                for url in us:
                    nm = path.basename(ps.unquote(url))
                    host = urllib3.util.parse_url(url).hostname
                    try:
                        fn = path.join(usdir, host + "_" + nm)
                        fp = open(fn, 'wb')
                        r = pool.request('GET', url)
                        fp.write(r.data)
                        audio['us_local'].append(path.relpath(fn, rootdir))
                    finally:
                        fp.close()

    nfilename = path.join(rootdir, 'shanbei_wordbook_{}_local.json'.format(book))
    nfp = open(nfilename, 'w', encoding='utf-8')
    json.dump(data, nfp, ensure_ascii=False, indent=4)
    nfp.close()


if __name__ == '__main__':
    download_audios(34)

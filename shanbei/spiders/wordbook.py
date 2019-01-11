# -*- coding: utf-8 -*-
import scrapy
import time
import json
import requests


class WordbookSpider(scrapy.Spider):
    wl = []
    failedwds = []
    name = 'wordbook'
    allowed_domains = ['www.shanbay.com']
    book = '34'
    file = None

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
        yield scrapy.Request(url, self.parse)  # 发送请求爬取参数内容

    def parse(self, response):
        ll = response.xpath('//*[@id="wordbook-wordlist-container"]')
        for l in ll:
            wa = l.css('a::attr(href)').extract()
            for w in wa:
                next_page = response.urljoin(w)
                yield scrapy.Request(next_page, callback=self.parsewds)

    # 避免一次性操作失败,可以分文件存储或者每一次查找到结果后存储到临时文件,最后统一处理格式
    def parsewds(self, response):
        ll = response.xpath('/html/body/div[3]/div/div[1]/div[2]/div/table')
        for l in ll:
            wl = l.xpath("//td[@class='span2']/strong//text()").extract()
            for w in wl:
                self.searchword(w)

    def searchword(self, w):
        resp = requests.get(self.makesearchpath(w)).json(encoding="utf-8")
        if resp['status_code'] == 0:
            data = resp['data']
            data['word'] = w
            self.wl.append(data)
        else:
            self.failedwds.append(w)
        print(data)

    def makesearchurl(self, w):
        tm = int(time.time()*1000)
        url = "/api/v1/bdc/search/?version=2&word={}&_={}".format(w, tm)
        return url

    def makesearchpath(self, w):
        tm = int(time.time()*1000)
        path = "https://www.shanbay.com/api/v1/bdc/search/?version=2&word={}&_={}".format(w, tm)
        return path

    def close(self, spider, reason):
        self.wl.sort(key=lambda w: w['word'])
        fp = open(self.file, 'w', encoding='utf-8')
        json.dump(self.wl, fp, ensure_ascii=False, indent=4)
        print("failed words", self.failedwds)
        super().close(spider, reason)

# def reloadjson():
#     file = open('../shanbei_wordbook34_tmp.json', 'r', encoding='utf-8')
#     res = json.load(file)
#     print(res)
#     file2 = open('shanbei_wordbook34.json', 'w')
#     json.dump(res, file2, ensure_ascii=False, indent=4)

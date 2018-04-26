# coding: utf-8

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from io import BytesIO
from PIL import Image
import time
import os

TEMPLATES_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/templates/'

# 参考
# https://juejin.im/post/5acf0ffcf265da23826e5e20


class CrackWeibo(object):

    def __init__(self, username, password, browser):
        self.url = 'https://passport.weibo.cn/signin/login?entry=mweibo&r=https://m.weibo.cn/'
        self.browser = browser
        self.wait = WebDriverWait(self.browser, 10)
        self.username = username
        self.password = password


    def open_url(self):
        """
        打开网页输入用户名密码并点击
        :return: None
        """
        self.browser.delete_all_cookies()
        self.browser.get(self.url)
        # presence_of_element_located: 元素加载出
        # element_to_be_clickable: 元素可点击
        username = self.wait.until(EC.presence_of_element_located((By.ID, 'loginName')))
        password = self.wait.until(EC.presence_of_element_located((By.ID, 'loginPassword')))
        submit = self.wait.until(EC.element_to_be_clickable((By.ID, 'loginAction')))
        username.send_keys(self.username)
        password.send_keys(self.password)
        time.sleep(0.5)
        submit.click()
        time.sleep(1.5)


    def password_error(self):
        """
        判断是否密码错误
        :return:
        text_to_be_present_in_element 某个元素文本包含某文字
        """
        try:
            return WebDriverWait(self.browser, 5).until(
                EC.text_to_be_present_in_element((By.ID, 'errorMsg'), '用户名或密码错误'))
        except TimeoutException:
            return False
    
    def login_successfully(self):
        """
        判断是否登录成功
        :return:
        """
        try:
            return bool(
                WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'drop-title'))))
        except TimeoutException:
            return False

    def get_fialied(self):
        """
         账号异常或限制访问
        """
        if self.browser.title == '解除帐号异常' or self.browser.title == '':
            return True
        else:
            return False
    def get_position(self):
        """
        获取验证码位置
        :return: 验证码位置元组
        """
        try:
            img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'patt-shadow')))
        except TimeoutException:
            print('未出现验证码')
            return (None,None,None,None)
        else:
            time.sleep(2)
            location = img.location
            size = img.size
            top, bottom, left, right = int(location['y']), int(location['y'] + size['height']), int(location['x']), int(location['x'] + size['width'])
            return (top, bottom, left, right)


    def get_screenshot(self):
        """
        获取网页截图
        :return: 截图对象
        """
        screenshot = self.browser.get_screenshot_as_png()
        screenshot = Image.open(BytesIO(screenshot))
        return screenshot


    def get_image(self, name='captcha.png'):
        """
        获取验证码图片
        :return: 图片对象
        """
        top, bottom, left, right = self.get_position()
        if not (top and  bottom and left and right):
            return None
        else:
            print('验证码位置', top, bottom, left, right)
            screenshot = self.get_screenshot()
            captcha = screenshot.crop((left, top, right, bottom))
            captcha.save(name)
            return captcha

    def is_pixel_equal(self, image1, image2, x, y):
        """
        判断两个像素是否相同
        :param image1: 图片1
        :param image2: 图片2
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """
        # 取两个图片的像素点
        pixel1 = image1.load()[x, y]
        pixel2 = image2.load()[x, y]
        threshold = 20
        if abs(pixel1[0] - pixel2[0]) < threshold and abs(pixel1[1] - pixel2[1]) < threshold and abs(
                pixel1[2] - pixel2[2]) < threshold:
            return True
        else:
            return False
    

    def same_image(self, image, template):
        """
        识别相似验证码
        :param image: 待识别验证码
        :param template: 模板
        :return:
        """
        # 相似度阈值
        threshold = 0.99
        count = 0
        for x in range(image.width):
            for y in range(image.height):
                # 判断像素是否相同
                if self.is_pixel_equal(image, template, x, y):
                    count += 1
        result = float(count) / (image.width * image.height)
        if result > threshold:
            print('成功匹配')
            return True
        return False

    def detect_image(self, image):
        """
        匹配图片
        :param image: 图片
        :return: 拖动顺序
        """
        for template_name in os.listdir(TEMPLATES_FOLDER):
            print('正在匹配', template_name)
            template = Image.open(TEMPLATES_FOLDER + template_name)
            if self.same_image(image, template):
                # 返回顺序
                numbers = [int(number) for number in list(template_name.split('.')[0])]
                print('拖动顺序', numbers)
                return numbers

    def move(self, numbers):
        """
        根据顺序拖动
        :param numbers:
        :return:
        """
        # 获得四个按点
        try:
            circles = self.browser.find_elements_by_css_selector('.patt-wrap .patt-circ')
            dx = dy = 0
            for index in range(4):
                circle = circles[numbers[index] - 1]
                # 如果是第一次循环
                if index == 0:
                    # 点击第一个按点
                    ActionChains(self.browser) \
                        .move_to_element_with_offset(circle, circle.size['width'] / 2, circle.size['height'] / 2) \
                        .click_and_hold().perform()
                else:
                    # 小幅移动次数
                    times = 30
                    # 拖动
                    for i in range(times):
                        ActionChains(self.browser).move_by_offset(dx / times, dy / times).perform()
                        time.sleep(1 / times)
                # 如果是最后一次循环
                if index == 3:
                    # 松开鼠标
                    ActionChains(self.browser).release().perform()
                else:
                    # 计算下一次偏移
                    dx = circles[numbers[index + 1] - 1].location['x'] - circle.location['x']
                    dy = circles[numbers[index + 1] - 1].location['y'] - circle.location['y']
        except:
            return False

    def get_cookies(self):
        """
        获取Cookies
        :return:
        """
        return self.browser.get_cookies()



    def main(self):
        """
        破解入口
        :return:
        """
        self.open_url()
        if self.get_fialied():
            return {
                    'status': 4,
                    'content': '登录失败'
              }
        if self.password_error():
            return {
                'status': 2,
                'content': '用户名或密码错误'
                }
        # 如果不需要验证码直接登录成功
        if self.login_successfully():
            print("登陆成功")
            cookies = self.get_cookies()
            return {
                'status': 1,
                'content': cookies
              }
        # 获取验证码图片
        image = self.get_image('captcha.png')
        if image:
            numbers = self.detect_image(image)
            self.move(numbers)
            if self.login_successfully():
                cookies = self.get_cookies()
                return {
                    'status': 1,
                    'content': cookies
                }
            elif self.password_error():
                return {
                    'status': 2,
                    'content': '用户名或密码错误'
                    }
            else:
                return {
                    'status': 3,
                    'content': '登录失败'
              }
        else:
            return {
                    'status': 4,
                    'content': '登录失败'
               }


if __name__ == '__main__':
    options = Options()
    options.add_argument('--headless')  # 无头参数
    # 使用第三方firfox浏览器驱动
    browser = webdriver.Firefox(executable_path='geckodriver', firefox_options=options)
    browser = webdriver.Firefox()
    result = CrackWeibo('14760253606', 'gmidy8470', browser).main()
    print(result)

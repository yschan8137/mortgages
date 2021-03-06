import pandas as pd
import datetime as dt
from IPython.display import display, display_html, HTML
import math
import json
import requests
from bs4 import BeautifulSoup
from io import StringIO
import numpy as np
from ipywidgets import *

#-----------------------------------------------------------------

class mortgages:
  
  def __init__(self):
    style = {'description_width': 'initial'}
    self.widget_amount = BoundedIntText(description='房屋總價(萬)：', min=0, max= 9999, value= 1000,style = style, continuous_update=True) #貸款金額
    self.widget_int = BoundedFloatText(description='房貸利率', min=0, value=1.31, style= style, continuous_update=True)
    self.widget_period = IntSlider(description='貸款年限：', min= 10, max= 40, step=10, continuous_update=True) 
    self.widget_down_payment = IntSlider(description='頭期款成數：' ,min=0, max=100, step=1, value=20, style=style, continuous_update=True) 
    self.widget_first_purchase = Dropdown(options=[('首購', 1), ('非首購', 0)], value= 1,description='購屋身分', continuous_update= True)
    self.widget_buffer_period = IntSlider(description='寬限期：',min=0, max= 5, step=1, value=0, style=style, continuous_update=True) 
    self.widget_prepay = BoundedIntText(description= '提前還款(萬)：', min=0, value=0 , step= 1,disable= False, style=style, continuous_update=True)
    self.widget_subsity = Dropdown(options= [(keys, int(values[:-2])) for keys, values in self.subsity_limit().items()],
                        description= '住宅利息補貼：',
                        value= 0, 
                        style=style, continuous_update=True
                        )
    self.widget_prepay_time = widgets.IntSlider(description= '提前還款時點(月)：', min=0, style=style, layout=Layout(width='100%'), continuous_update=True)
    self.widget_subsity_time = widgets.IntSlider(description= '補貼申請時間(月)：', min=1, max= 24,style=style, layout=Layout(width='100%'), continuous_update=True)
    self.widget_subsity_duration = widgets.IntSlider(description= '補貼貸款年限(年)：',min=1, max=20, step=1, layout=Layout(width='100%'), style=style, continuous_update=True)
    self.widget_int= Dropdown(description='貸款利率', options= self.prgm(period= self.widget_period.value),style= style)
    self.widget_output= Output()
  
  #查詢貸款利率
  def prgm(self, period= 40, first_purchase= 1, mortgage_ratio= 20):
    down_payment = self.widget_amount.value * (mortgage_ratio / 100)
    amount = self.widget_amount.value
    src = f'https://mortgage.591.com.tw/search/?first_purchase={first_purchase}&price={amount}&purchase={down_payment}&mortgage_ratio={mortgage_ratio}&mortgage_time={period}&target_user=0&bank_id=&order_field=&firstRow=0'
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
        }
    res = requests.get(src, 
        headers= headers, 
        )
    #soup = BeautifulSoup(res.text, 'html.parser')
    data = pd.read_json(res.text, dtype=True, )
    df = pd.DataFrame(data.data.data)
    apr_remark = df.apr_remark
    n = len(apr_remark)
    kite = {}
    example = []
    count = 0
    for i in range(0, n):
      example.append({**apr_remark}[i].replace('總費用年百分率試算範例', ''))
      #example[-1] = u"':'".join(example[-1].split('：')).split('\n')
      example[-1] = example[-1].replace('：', "\n")
      #print(''.join(example[-1].split("\n")).split('：'))
      example[-1] = example[-1].split('\n')
      #df = pd.DataFrame((np.array(example[-1][2::2]).T).to_list(), columns= example[-1][1::2]) 

      for key, value in zip(example[-1][1::2],example[-1][2::2]):
        count += 1
        kite.update({key[2:]: value})
      if count == len(kite):
        dff = pd.DataFrame(kite, index= [count])
      elif count > len(kite):
        df_kite = pd.DataFrame(kite, index=[count])
        dff = dff.append(df_kite, ignore_index=False)
    dff.reset_index(inplace=True, drop=True)
    dff.rename(columns={'貸款金額': 'mortgage_amount', '貸款期間': 'mortgage_time', '貸款利率': 'seg_min', '相關費用總金額': 'fee', '總費用年百分率': 'apr_rate'}, inplace=True)
    dff = pd.concat([df[['bank_name', 'title', 'seg_min', 'mortgage_time', 'type', 'interest_type']], dff[['fee', 'apr_rate']]], axis= 1)
    dff.index = dff.index + 1
    return dff
  
  #查詢自購住宅利息補貼上限
  def subsity_limit(self): #各縣市自購住宅利息補貼上限
    url_homepage = 'https://pip.moi.gov.tw/V3/B/SCRB0108.aspx?KeyID=GroupB'
    url_exam = 'https://pip.moi.gov.tw/V3/B/SCRB0108.aspx?KeyID=HS202128'
    headers = {
        'content-type': 'text/html; charset=utf-8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
        }
    res_exam = requests.get(url= url_exam, headers= headers)
    info_exam = BeautifulSoup(res_exam.text, 'html.parser')
    res_homepage = requests.get(url= url_homepage, headers= headers)
    info_homepage = BeautifulSoup(res_homepage.text, 'html.parser')
    res_limit = info_homepage.find_all('td', headers="gb01c1")
    list_limit = {}
    for limit in [i.text.splitlines() for i in res_limit][0][1:]:
      list_limit[limit.split('最高為新臺幣')[0] + '(' + limit.split('最高為新臺幣')[1] + ')'] = limit.split('最高為新臺幣')[1]
    list_limit['不申請'] =  '0萬元'
    return list_limit 

  #分期付款
  def installment(self, i, period, down_payment= 20, buffer_period= 0, prepay= 0, subsity= 0, **kwargs):
    DP = 0 #進位到小數點第幾位
    INT = (i / 100) #暫不考慮多段式利率
    buffer = [1] #是否在寬限期內(0:是 | 1:不是)
    i_sub = 0.312 / 100
    loan_EP = [self.widget_amount.value * (1 - (down_payment / 100)) * 10000]
    loan_ET = [self.widget_amount.value * (1 - (down_payment / 100)) * 10000]
    EPR = [(((1 + (INT / 12))**((period - buffer_period)* 12)) * (INT / 12)) / (((1 + (INT / 12))**((period - buffer_period)* 12)) - 1)] #平均攤還率 --> 用在本息均攤每期金額計算
    ET = [self.widget_amount.value * (down_payment / 100) * 10000] #(本息均攤)金額
    ETP = [0] #(本息均攤)本金
    INT_ET = [0] #每月本息均攤利息
    INT_Sub_ET = [0] #本息均攤利息補償項 --> 如果提前還款會多出利息，新增補償項抵銷本金多刪除利息的部份
    EP = [self.widget_amount.value * (down_payment / 100) * 10000] #(本金攤還)金額
    EPP = [0]#self.widget_amount.value * (1 - (down_payment / 100)) * 10000 / (period * 12)] #(本金攤還)本金
    INT_EP = [0]
    RES_ET = [self.widget_amount.value * (1 - (down_payment / 100)) * 10000] #(本息攤還)本金餘額
    RES_EP = [self.widget_amount.value * (1 - (down_payment / 100)) * 10000] #(本金攤還)本金餘額
    prepay_ET = [0] #(本息均攤)提前還款金額
    prepay_EP = [0] #(本金均攤)提前還款金額
    subsity_ET = [0] #提前還款金額 --> 只要在變動時點擴充即可，後續就取最新金額就好，注意清單長度不會等於實際結果長度
    subsity_EP = [0] #自購款利息補貼金額 --> 只要在變動時點擴充即可，後續就取最新金額就好，注意清單長度不會等於實際結果長度
    prepay_t = [1] #提前還款時點
    subsity_t = [1] #自購屋補助時點
    EP_subsity = [0] #自購利息補貼貸款本金餘額
    EPP_subsity = [0]
    RES_EP_subsity = [0]
    INT_EP_subsity = [0]
    EPR_subsity = [0]
    ET_subsity = [0] #自購利息補貼貸款本息均攤金額
    ETP_subsity = [0]
    RES_ET_subsity = [0]
    INT_ET_subsity = [0]
    for t in range(0, period * 12):
      if buffer_period > 0:
        if buffer_period > 5:
          raise ValueError('寬限期不可超過5年')
        if t <= buffer_period * 12 - 1:
          buffer.append(0)
        if t > buffer_period * 12 - 1:
          buffer.append(1)
      else:
        pass
      if t < period * 12 - 1:
        if prepay == 0 and subsity == 0:
          #正常本金攤還
          EPP.append(round(loan_EP[-1] * buffer[-1] / ((period - buffer_period)* 12), DP)) #算每期本金攤還本金
          INT_EP.append(round(RES_EP[-1] * (INT / 12), DP)) 
          RES_EP.append(round((RES_EP[-1] - EPP[-1]), DP)) #本金攤還餘額 <-- 上一期餘額扣掉本期應付本金
          EP.append(round((EPP[-1] + INT_EP[-1]), DP))# - INT_Sub_EP[-1]))
          #正常本息均攤
          ET.append(round(((loan_ET[-1]) * EPR[-1]) * buffer[-1] - (RES_ET[-1] * (INT / 12))* (buffer[-1] - 1), DP)) #先算出本息攤還金額
          INT_ET.append(round(RES_ET[-1] * (INT / 12), DP)) #本期利息 <-- 以上一期餘額算
          ETP.append(round((ET[-1] - INT_ET[-1]) * buffer[-1], DP)) #本息攤還本金 <-- 本息攤還金額扣掉利息
          RES_ET.append(round((RES_ET[-1] - ETP[-1]), DP)) #最後算本息攤還餘額
        elif prepay != 0 or subsity != 0:
          if prepay != 0:
            try:
              prepay_t.append(kwargs['prepay_time'])
              if prepay_t[-1] <= 24:
                raise ValueError('注意是否產生提前還款違約金[各銀行提前還款違約金比較功能...待開發中]')
            except KeyError:
              raise KeyError('請輸入提前還款時間[prepay_time]')
            if t < prepay_t[-1]:
              EPP.append(round((loan_EP[-1] * buffer[-1] / ((period - buffer_period)* 12)), DP)) #每期本金均攤攤還本金
            if t == prepay_t[-1] -1:
              if prepay == 'all':
                prepay_ET.append(RES_ET[-1])
                prepay_EP.append(RES_EP[-1])
              else:
                prepay_ET.append(prepay * 10000)
                prepay_EP.append(prepay * 10000)
            if t == prepay_t[-1]:           
              loan_EP.append(RES_EP[-1] - prepay_EP[-2])
              loan_ET.append(RES_ET[-1] - prepay_ET[-2])
              prepay_ET.append(0)
              prepay_EP.append(0)  
              #降低當期本金計算基準
            #if t >= prepay_t[-1]:
              #本金攤還本金
              EPP.append(round((loan_EP[-1] * buffer[-1] / ((period - buffer_period)* 12 - prepay_t[-1])), DP)) #每期本金均攤攤還本金
              #更新平均攤還率
              EPR.append((((1 + (INT / 12))**((period - buffer_period)* 12 - prepay_t[-1])) * (INT / 12)) / (((1 + (INT / 12))**((period - buffer_period) * 12 - prepay_t[-1])) - 1))
          if subsity != 0:
            try:
              subsity_t.append(kwargs['subsity_time'])
              if subsity_t[-1] > 24:
                raise ValueError('要在貸款後2年內申請自購住宅利息補貼') 
            except KeyError:
              raise KeyError('請輸入住宅利息補貼時間[subsity_time]')
            try:
              subsity_duration = kwargs['subsity_duration'] * 12
              if subsity_duration > 240:
                raise ValueError('自購利息補貼年限不得超過20年')
            except KeyError:
              raise KeyError('請輸入住宅利息補貼還款年限[subsity_duration]') 
            if t < subsity_t[-1] - 1:
              EPP.append(round(loan_EP[-1] * buffer[-1]   / ((period - buffer_period)* 12), DP)) #每期本金均攤攤還本金
              ##填空以便做成DataFrame
              EPP_subsity.append(0)
              RES_EP_subsity.append(0)
              INT_EP_subsity.append(0)
              ETP_subsity.append(0)
              RES_ET_subsity.append(0)
              INT_ET_subsity.append(0)
              EP_subsity.append(0)
              ET_subsity.append(0)
            if t == subsity_t[-1] -1:
              subsity_ET.append(subsity * 10000)
              subsity_EP.append(subsity * 10000)
              #自購利息補貼貸款及本金
              EPP_subsity.append(round((RES_EP_subsity[-1]  / subsity_duration), DP))
              RES_EP_subsity.append(subsity_EP[-1])
              RES_ET_subsity.append(subsity_ET[-1])
              ##填空以便做成DataFrame
              INT_EP_subsity.append(0)
              INT_ET_subsity.append(0)
              ETP_subsity.append(0)
              EPR_subsity.append((((1 + (i_sub / 12))**(subsity_duration)) * (i_sub / 12)) / (((1 + (i_sub / 12))**(subsity_duration)) - 1))
            if t == subsity_t[-1]:
              ETP_subsity.append(0)
              EPP_subsity.append(0)
              EPP.append(round(loan_EP[-1] * buffer[-1]   / ((period - buffer_period)* 12), DP))
              EPR.append((((1 + (INT / 12))**((period - buffer_period)* 12 - subsity_t[-1])) * (INT / 12)) / (((1 + (INT / 12))**(period * 12 - subsity_t[-1])) - 1))
              #降低當期借入本金計算基準
              loan_EP.append(RES_EP[-1] - subsity_EP[-2])
              loan_ET.append(RES_ET[-1] - subsity_ET[-2])
              EP_subsity.append(0)
              ET_subsity.append(0)
            if t > subsity_t[-1] -1:
              #更新本金均攤攤還本金
              EPP.append(round((loan_EP[-1] * buffer[-1]  / ((period - buffer_period)* 12 - subsity_t[-1])), DP)) #更新每期本金攤還本金
            if t > subsity_t[-1] - 1 and t < (subsity_t[-1] + subsity_duration) - 1: #償還自購利息補貼貸款期間
              subsity_EP.append(0)
              subsity_ET.append(0)
              #本金攤還
              #EPP.append(round((loan_EP[-1] * buffer[-1]  / ((period - buffer_period)* 12 - subsity_t[-1])), DP)) #更新每期本金攤還本金
              EPP_subsity.append(round((subsity * 10000  / subsity_duration), DP)) #本金均攤每期攤還本金
              INT_EP_subsity.append(round(RES_EP_subsity[-1] * (i_sub / 12), DP))
              EP_subsity.append(round((EPP_subsity[-1] + INT_EP_subsity[-1]), DP))
              RES_EP_subsity.append(round((RES_EP_subsity[-1] - EPP_subsity[-1]), DP))
              #本息攤還
              ET_subsity.append(round((subsity * 10000 * EPR_subsity[-1]), DP))
              INT_ET_subsity.append(round(RES_ET_subsity[-1] * (i_sub / 12), DP)) #本期利息 <-- 以上一期餘額算
              ETP_subsity.append(round((ET_subsity[-1] - INT_ET_subsity[-1]), DP)) #本息攤還本金 <-- 本息攤還金額扣掉利息
              RES_ET_subsity.append(round((RES_ET_subsity[-1] - ETP_subsity[-1]), DP)) #最後算本息攤還餘額
            if t >= (subsity_t[-1] + subsity_duration) - 1: #還完自購住宅利息補貼貸款
              #EPP.append(round((loan_EP[-1] / (period * 12 - subsity_t[-1])), DP))
              #本金攤還
              EPP_subsity.append(RES_EP_subsity[-1])
              INT_EP_subsity.append(round((RES_EP_subsity[-1] * (i_sub / 12)), DP))
              EP_subsity.append(round((EPP_subsity[-1] + INT_EP_subsity[-1]), DP))
              RES_EP_subsity.append(RES_EP_subsity[-1] - EPP_subsity[-1])  
              #本息攤還
              INT_ET_subsity.append(round((RES_ET_subsity[-1] * (i_sub / 12)), DP))
              ETP_subsity.append(round(RES_ET_subsity[-1], DP))
              ET_subsity.append(round((RES_ET_subsity[-1]/(1-(i_sub / 12))), DP))
              RES_ET_subsity.append(RES_ET_subsity[-1] - ETP_subsity[-1])

          #本金攤還
          INT_EP.append(round(RES_EP[-1] * (INT / 12), DP)) 
          RES_EP.append(round(RES_EP[-1] - prepay_EP[-1] - subsity_EP[-1] - EPP[-1], DP)) #本金攤還餘額 <-- 上一期餘額扣掉提前還款、自購住宅補貼貸款及本期應付本金
          EP.append(round(EPP[-1] + INT_EP[-1] + prepay_EP[-1] + EP_subsity[-1], DP))
          #本息攤還
          ET.append(round((loan_ET[-1]) * EPR[-1] * buffer[-1] - (RES_ET[-1] * (INT / 12))* (buffer[-1] - 1) + prepay_ET[-1] + ET_subsity[-1], DP))
          INT_ET.append(round(RES_ET[-1] * (INT / 12), DP))
          ETP.append(round(ET[-1] - INT_ET[-1] - ET_subsity[-1], DP))
          RES_ET.append(round((RES_ET[-1] - subsity_ET[-1] - ETP[-1]), DP))
    #最後一期
    if t == period * 12 - 1:
      ##
      ETP_subsity.append(round((RES_ET_subsity[-1]/(1-(i_sub / 12))), DP))
      EPP_subsity.append(round((EPP_subsity[-1] + INT_EP_subsity[-1]), DP))
      EP_subsity.append(round(RES_EP_subsity[-1] + INT_EP_subsity[-1], DP))
      ET_subsity.append(round((RES_ET_subsity[-1]/(1-(INT_Sub_ET[-1] / 12))),DP))
      #本金攤還
      INT_EP.append(round((RES_EP[-1] * (INT / 12)), DP))
      EP.append(round((RES_EP[-1] + INT_EP[-1] + EP_subsity[-1]), DP))
      RES_EP.append(RES_EP[-1] - RES_EP[-1])  
      #本息攤還
      EPP.append(RES_EP[-1])
      INT_ET.append(round((RES_ET[-1] * (INT / 12)), DP))
      ETP.append(round(RES_ET[-1], DP))
      ET.append(round((RES_ET[-1]/(1-(INT / 12)) + prepay_ET[-1] + ET_subsity[-1]), DP))
      RES_ET.append(RES_ET[-1] - ETP[-1])
  
    #彙整結果
    #sumary = {'本息攤還利息':[],
    #      '本息均攤金額':[], 
    #      '本金均攤利息':[], 
    #      '本金均攤金額':[] 
    #      }
    df_sum = pd.DataFrame(index=['總和'])
    df_sum['本息均攤金額'] = round(sum(ET), DP)
    df_sum['本息攤還利息'] = sum(INT_ET)
    df_sum['本金均攤金額'] = round(sum(EP), DP)
    df_sum['本金均攤利息'] = sum(INT_EP)
    df = pd.DataFrame([],index=[x for x in range(0, period * 12 + 1)]).copy()
    df['本息均攤金額']= ET
    df['本息攤還本金'] = ETP
    df['本息攤還利息'] = INT_ET
    df['本息均攤剩餘本金'] = RES_ET
    df['本金均攤金額']= EP
    df['本金均攤本金'] = EPP
    df['本金均攤利息'] = INT_EP
    df['本金均攤剩餘本金'] = RES_EP
  
    if subsity == 0:
      pass
    elif subsity != 0:
      df.insert(loc=4, column= '自購補貼貸款本息均攤金額', value= ET_subsity)
      df['自購補貼貸款本金均攤金額'] = EP_subsity
    return df, INT_EP, INT_ET, EP, ET, i, subsity_EP, subsity_ET, INT_EP_subsity, INT_ET_subsity, df_sum
  
  def ARR_payment(self, **kwargs):
    display(HTML(self.installment(**kwargs)[0].to_html()))
    return

  def SUM_payment(self, **kwargs):
    result = self.installment(**kwargs)
    INT_EP = result[1]
    INT_ET = result[2]
    EP = result[3]
    ET = result[4]
    i = result[5]
    INT_EP_subsity = result[-2]
    INT_ET_subsity = result[-1]
    subsity_EP= result[6]
    subsity_ET= result[7]
    print('--------總成本---------')
    print('本息均攤法：{:,}'.format(round(sum(ET))))
    print('本金均攤法：{:,}'.format(round(sum(EP))))
    print('            ')
    print('--------利息成本--------')
    print('本息均攤法：{:,}'.format(round(sum(INT_ET))))
    print('本金均攤法：{:,}'.format(round(sum(INT_EP))))
    print('            ')  
    print('--------平均月還款--------')
    print('本息均攤法：{:,}'.format(round(np.mean(ET[1:]))))
    print('本金均攤法：{:,}'.format(round(np.mean(EP[1:]))))
    print('            ')
    print(f'貸款利率：{i} %')
    return

    #製作操控面板
  def installments(self):
    amount_ = self.widget_amount 
    int_ = self.widget_int
    period_ = self.widget_period 
    down_payment_ = self.widget_down_payment 
    buffer_period_ = self.widget_buffer_period
    prepay_ = self.widget_prepay
    subsity_ = self.widget_subsity
    prepay_time_ = self.widget_prepay_time
    subsity_time_ = self.widget_subsity_time
    subsity_duration_ = self.widget_subsity_duration
    first_purchase_ = self.widget_first_purchase
    output= self.widget_output

    #設定金額上限
    def cap_prepay(*args):
      prepay_.max = amount_.value
      return
    amount_.observe(cap_prepay, 'value')
    
    def cap_prepay_time(*args):
      prepay_time_.max = 12 * period_.value
      return
    period_.observe(cap_prepay_time, 'value', )
  
    #貸款利率清單
    def update_list(period, first_purchase):
      list_ints = {}
      result = self.prgm(period= period_.value, first_purchase= first_purchase_.value).to_dict()
      for i in zip(result['bank_name'].values(), result['title'].values(), result['seg_min'].values()):
        list_ints[f'{i[0]}({i[1]})：{i[2]}']= float(i[2])
      int_.options = list_ints
      return
      #int_.options= prgm(change.new).to_dict()['seg_min']
      #int_.value= wgets.result['apr_rate']
    update_list(period=period_, first_purchase= first_purchase_)
    ie = interactive(update_list, period= period_, first_purchase= first_purchase_)
    ie.observe(update_list, 'value')
  
    widgets_1 =interactive(self.ARR_payment,
          amount= amount_,
          period= period_,
          first_purchase= first_purchase_,
          i=  int_, 
          down_payment= down_payment_, 
          buffer_period=  buffer_period_, 
          prepay=  prepay_, 
          subsity=  subsity_, 
          prepay_time=  prepay_time_, 
          subsity_time=  subsity_time_, 
          subsity_duration=  subsity_duration_
          )
  
    widgets_2 =interactive_output(self.SUM_payment,
          {'amount': amount_,
          'period': period_,
          'first_purchase':first_purchase_,
          'i':  int_, 
          'down_payment': down_payment_, 
          'buffer_period':  buffer_period_, 
          'prepay':  prepay_, 
          'subsity':  subsity_, 
          'prepay_time':  prepay_time_, 
          'subsity_time':  subsity_time_, 
          'subsity_duration':  subsity_duration_}
          )

    control1 = VBox(widgets_1.children[0:6], 
           layout= Layout(flex='1 1 auto', width= '40%', height= 'auto')
           )
    control2 = VBox(widgets_1.children[6:-1], 
           layout= Layout(flex='1 1 auto', width= '60%', height= 'auto', overflow='auto')
           )
  
    output1 = VBox([widgets_1.children[-1]], layout= Layout(width= '50%' , height= '550px', flex_flow= 'scroll'))
  
    control1 = HBox([control1, control2], layout= Layout(flex='1 1 auto', 
                               width= 'auto',
                               height= 'auto',
                               flex_flow= 'row nowrap',
                               overflow='auto'
                               ))
    output2 = VBox([control1, widgets_2], layout= Layout(flex='1 1 auto', 
                               width= '50%' ,
                               height= 'auto',
                               #flex_flow= 'column wrap'
                               ))
    a = HBox([output2, output1], layout= Layout(flex='1 1 auto', width= 'auto' ,height= 'auto',
                               flex_flow= 'row wrap'
                               ))
    return display(a)

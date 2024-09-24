import datetime
import backtrader as bt
import matplotlib.pyplot as plt
import akshare as ak
import pandas as pd
from btplotting import BacktraderPlotting

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

symbols = ["601888", "601111", "600036", "600585", 
           "601318", "600887", "601012", "601360", "601919", "600031"]
#symbols = ["601888"]
#symbols = ["600343"]
price_limit = 50000
order_count = {}
current_strategy = 0
update_scale = 0.5
turtle_scale = 0.01

class BaseStrategy(bt.Strategy):
    def __init__(self):
        self.is_stop = False
        self.data_close = []
        self.data_high = []
        self.data_low = []
        self.data_open = []
        self.Donchian_high = []
        self.Donchian_low = []
        self.avg350 = []
        self.avg250 = []
        self.avg150 = []
        self.avg100 = []
        self.avg25 = []
        self.ATR = []
        self.cross_high = []
        self.cross_low = []
        self.buy_time = []
        self.buy_price = []
        self.buy_comm = []
        self.new_stake = []
        self.order = None
        self.cash = 1000000
        for i in range(len(symbols)):
            self.buy_time.append(0)
            self.buy_price.append(0)
            self.buy_comm.append(0)
            self.new_stake.append(0)
            self.data_open.append(self.datas[i].open)
            self.data_close.append(self.datas[i].close)
            self.data_high.append(self.datas[i].high)
            self.data_low.append(self.datas[i].low)
        for i in range(len(symbols)):
            # 参数计算 ATR
            self.ATR.append(bt.indicators.AverageTrueRange(self.datas[i], period=20, subplot=False))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, name: %s, value: %.2f, Comm %.2f, total_money %.2f' %
                      (order.executed.price,
                       order.data._name,
                       order.executed.value,
                       order.executed.comm,
                       self.broker.getvalue()), do_print=False)
                
                self.buy_price[symbols.index(order.data._name)] = order.executed.price
                self.buy_comm[symbols.index(order.data._name)] = order.executed.comm
                self.cash -= (order.executed.value + order.executed.comm)
                order_count[current_strategy]+= 1
                if self.buy_time[symbols.index(order.data._name)] == 0:
                    self.buy_time[symbols.index(order.data._name)] = 1
                else:
                    self.buy_time[symbols.index(order.data._name)] += 1
            else:
                self.log('SELL EXECUTED, Price: %.2f, name: %s, value: %.2f, Comm %.2f, total_money %.2f' %
                         (order.executed.price,
                          order.data._name,
                          order.executed.value,
                          order.executed.comm,
                          self.broker.getvalue()), do_print=False)
                self.cash += (order.executed.value - order.executed.comm)
                order_count[current_strategy] += 1
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def downcast(amount, lot):
        return abs(amount // lot * lot)

    def log(self, txt, dt=None, do_print=False):
        if do_print:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

class ATRStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        print("ATR 策略")
        self.open = 0
        for i in range(len(symbols)):
            self.avg350.append(bt.indicators.SMA(self.data_close[i], period=350, subplot=False))
            self.cross_high.append(bt.ind.CrossOver(self.data_close[i],  self.avg350[i] + 7 * self.ATR[i]))
            self.cross_low.append(bt.ind.CrossOver(self.data_close[i], self.avg350[i] - 3 * self.ATR[i]))
            self.avg25.append(bt.indicators.SMA(self.data_close[i], period=25, subplot=False))
    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
            if self.cross_high[i] > 0 and self.buy_time[i] == 0:
                self.new_stake = self.broker.getvalue() * 0.01 / self.ATR[i][0]
                self.new_stake = int(self.new_stake / 100) * 100
                position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                self.order = self.buy(self.datas[i], price=self.datas[i].close)
                #self.buy_time[i] = 1
                self.open = 0
                # 加仓
            elif self.datas[i].close > self.buy_price[i] + update_scale * self.ATR[i][0] and self.buy_time[i] > 0 and self.buy_time[i] < 4:
                self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                self.new_stake = int(self.new_stake / 100) * 100
                position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                self.order = self.buy(self.datas[i], price=self.datas[i].close)
                #self.buy_time[i] += 1
                # 出场
            elif self.cross_low[i] < 0 and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                #print(position.size)
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0
            elif self.is_stop == True and self.data_close[i] < (self.buy_price[i] - 2 * self.ATR[i][0]) and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0

class BollStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        print("布林格指标策略")
        self.boll_up = []
        self.boll_down = []
        for i in range(len(symbols)):
            self.boll_up.append(bt.indicators.BollingerBands(self.datas[i], period=350, devfactor=2.5, subplot=False))
            self.boll_down.append(bt.indicators.BollingerBands(self.datas[i], period=350, devfactor=2.5, subplot=False))
            self.cross_high.append(bt.ind.CrossOver(self.data_close[i], self.boll_up[i]))
            self.cross_low.append(bt.ind.CrossOver(self.data_close[i], self.boll_down[i]))
    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
                # 入场
            if self.cross_high[i] > 0 and self.buy_time[i] == 0:
                self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                self.new_stake = int(self.new_stake / 100) * 100
                position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                self.order = self.buy(self.datas[i], price=self.datas[i].close)
                #self.buy_time[i] = 1
                # 加仓
            elif self.datas[i].close > self.buy_price[i]  + update_scale * self.ATR[i][0] and self.buy_time[i] > 0 and self.buy_time[i] < 4:
                self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                self.new_stake = int(self.new_stake / 100) * 100
                position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                self.order = self.buy(self.datas[i], price=self.datas[i].close)
                #self.buy_time[i] += 1
                # 出场
            elif self.cross_low[i] < 0 and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0
            elif self.is_stop == True and self.data_close[i] < (self.buy_price[i] - 2 * self.ATR[i][0]) and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0

class DoncianStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        print('唐奇东策略')
        # 唐奇安通道上轨突破、唐奇安通道下轨突破
        for i in range(len(symbols)):
            # 参数计算，唐奇安通道上轨、唐奇安通道下轨、ATR
            self.avg25.append(bt.indicators.SMA(self.data_close[i], period=25, subplot=False))
            self.avg350.append(bt.indicators.SMA(self.data_close[i], period=350, subplot=False))
            self.Donchian_high.append(bt.indicators.Highest(self.data_high[i](-1), period=20, plot=False))
            self.Donchian_low.append(bt.indicators.Lowest(self.data_low[i](-1), period=10, plot=False))
            self.cross_high.append(bt.ind.CrossOver(self.data_high[i], self.Donchian_high[i]))
            self.cross_low.append(bt.ind.CrossOver(self.data_low[i], self.Donchian_low[i]))

    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
                # 入场
            if self.avg25[i] > self.avg350[i]:
                if self.cross_high[i] > 0 and self.buy_time[i] == 0:
                    self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                    self.new_stake = int(self.new_stake / 100) * 100
                    position_limit = int((price_limit / self.datas[i].high) / 100) * 100
                    cash_limit = int((self.cash / self.datas[i].high) / 100) * 100
                    self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                    self.order = self.buy(self.datas[i], price=self.datas[i].high)
                    #self.buy_time[i] = 1
                    # 加仓
                elif self.datas[i].close > self.buy_price[i] + update_scale * self.ATR[i][0] and self.buy_time[i] > 0 and self.buy_time[i] < 4:
                    self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                    self.new_stake = int(self.new_stake / 100) * 100
                    position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                    cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                    self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                    self.order = self.buy(self.datas[i], price=self.datas[i].close)
                    #self.buy_time[i] += 1
                # 出场
            else:
                if self.cross_low[i] < 0 and self.buy_time[i] > 0:
                    position = self.broker.getposition(self.datas[i])
                    self.order = self.sell(self.datas[i], price=self.data_low[i], size = position.size)
                    self.buy_time[i] = 0
                if self.is_stop == True and self.data_close[i] < (self.buy_price[i] - 2 * self.ATR[i][0]) and \
                        self.buy_time[i] > 0:
                    position = self.broker.getposition(self.datas[i])
                    self.order = self.sell(self.datas[i], price=self.datas[i].close, size=position.size)
                    self.buy_time[i] = 0

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' % (20, self.broker.getvalue()), do_print=True)

class DoncianTimeStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        print('唐奇东按时退出策略')
        self.btime = {}
        self.bcount = {}
        self.orders = {}
        for i in range(len(symbols)):
            # 参数计算，唐奇安通道上轨、唐奇安通道下轨、ATR
            self.avg25.append(bt.indicators.SMA(self.data_close[i], period=25, subplot=False))
            self.avg350.append(bt.indicators.SMA(self.data_close[i], period=350, subplot=False))
            self.Donchian_high.append(bt.indicators.Highest(self.data_high[i](-1), period=20, plot=False))
            self.cross_high.append( bt.ind.CrossOver(self.data_high[i], self.Donchian_high[i]))
            self.btime[i] = []
            self.bcount[i] = 0
            self.orders[i] = []
    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
                # 入场
            if self.avg25[i] > self.avg350[i]:
                if self.cross_high[i] > 0 and self.buy_time[i] == 0:
                    self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                    self.new_stake = int(self.new_stake / 100) * 100
                    position_limit = int((price_limit / self.data_high[i]) / 100) * 100
                    cash_limit = int((self.cash / self.datas[i].high) / 100) * 100
                    self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                    self.order = self.buy(self.datas[i], price = self.datas[i].high)
                    # 加仓
                elif self.datas[i].close > self.buy_price[i] + update_scale * self.ATR[i][0] and self.buy_time[i] > 0 and self.buy_time[i] < 4:
                    self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                    self.new_stake = int(self.new_stake / 100) * 100
                    position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                    cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                    self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                    self.order = self.buy(self.datas[i], price = self.datas[i].close)
                    # 出场
            if self.buy_time[i] > 0 and self.datas[i].datetime.datetime() > self.btime[i][self.bcount[i]] + datetime.timedelta(days=112):
                self.order = self.sell(data=self.datas[i], size=self.orders[i][self.bcount[i]], price=self.datas[i].close)
                self.buy_time[i] -= 1
                self.bcount[i] += 1

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, name: %s, value: %.2f, Comm %.2f, total_money %.2f' %
                      (order.executed.price,
                       order.data._name,
                       order.executed.value,
                       order.executed.comm,
                       self.broker.getvalue()), do_print=False)
                
                self.buy_price[symbols.index(order.data._name)] = order.executed.price
                self.buy_comm[symbols.index(order.data._name)] = order.executed.comm
                self.cash -= (order.executed.value + order.executed.comm)
                order_count[current_strategy]+= 1
                self.orders[symbols.index(order.data._name)].append(self.sizer.p.stake)
                self.btime[symbols.index(order.data._name)].append(self.datas[symbols.index(order.data._name)].datetime.datetime())
                if self.buy_time[symbols.index(order.data._name)] == 0:
                    self.buy_time[symbols.index(order.data._name)] = 1
                else:
                    self.buy_time[symbols.index(order.data._name)] += 1
            else:
                self.log('SELL EXECUTED, Price: %.2f, name: %s, value: %.2f, Comm %.2f, total_money %.2f' %
                         (order.executed.price,
                          order.data._name,
                          order.executed.value,
                          order.executed.comm,
                          self.broker.getvalue()), do_print=False)
                self.cash += (order.executed.value - order.executed.comm)
                order_count[current_strategy] += 1
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        self.order = None

class DualCrossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        for i in range(len(symbols)):
            self.avg100.append(bt.indicators.SMA(self.data_close[i], period=100, subplot=False))
            self.avg350.append(bt.indicators.SMA(self.data_close[i], period=350, subplot=False))
            self.cross_high.append(bt.ind.CrossOver(self.avg100[i], self.avg350[i]))
        print("双重平均线策略")
    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
            if self.cross_high[i] > 0 and self.buy_time[i] < 4:
                self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                self.new_stake = int(self.new_stake / 100) * 100
                position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                self.order = self.buy(self.datas[i], price=self.datas[i].close)
                self.buy_time[i] += 1
            elif self.cross_high[i] < 0 and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(data = self.datas[i], size=position.size)
                self.buy_time[i] = 0
            elif self.is_stop == True and self.data_close[i] < (self.buy_price[i] - 2 * self.ATR[i][0]) and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0

class TripleCrossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        for i in range(len(symbols)):
            self.avg150.append(bt.indicators.SMA(self.data_close[i], period=150, subplot=False))
            self.avg250.append(bt.indicators.SMA(self.data_close[i], period=250, subplot=False))
            self.avg350.append(bt.indicators.SMA(self.data_close[i], period=350, subplot=False))
            self.cross_high.append(bt.And(self.avg150[i] > self.avg350[i], self.avg250[i] > self.avg350[i], bt.ind.CrossOver(self.avg150[i], self.avg250[i])))
            self.cross_low.append(bt.And(self.avg150[i] < self.avg350[i], self.avg250[i] < self.avg350[i], bt.ind.CrossOver(self.avg250[i], self.avg150[i])))
        print("三重平均线策略")
    def next(self):
        for i in range(len(symbols)):
            if self.order:
                return
                # 入场
            if self.cross_high[i] > 0 and self.buy_time[i] < 4:
                    self.new_stake = self.broker.getvalue() * turtle_scale / self.ATR[i][0]
                    self.new_stake = int(self.new_stake / 100) * 100
                    position_limit = int((price_limit / self.datas[i].close) / 100) * 100
                    cash_limit = int((self.cash / self.datas[i].close) / 100) * 100
                    self.sizer.p.stake = max(0, min(position_limit, self.new_stake, cash_limit))
                    self.order = self.buy(self.datas[i], price=self.datas[i].close)
                    self.buy_time[i] += 1
            elif self.cross_low[i] > 0 and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0
            elif self.is_stop == True and self.data_close[i] < (self.buy_price[i] - 2 * self.ATR[i][0]) and self.buy_time[i] > 0:
                position = self.broker.getposition(self.datas[i])
                self.order = self.sell(self.datas[i], price=self.datas[i].close, size = position.size)
                self.buy_time[i] = 0


if __name__ == '__main__':
    # 创建主控制器
    strategies = [ATRStrategy, BollStrategy, DoncianStrategy, DoncianTimeStrategy, DualCrossStrategy, TripleCrossStrategy]
    #strategies = [ATRStrategy]
    for strategy in strategies:
        cerebro = bt.Cerebro()
        # 加入策略
        cerebro.addstrategy(strategy)
        order_count[current_strategy] = 0
        # 准备股票日线数据，输入到backtrader
        for symbol in symbols:
            df = ak.stock_zh_a_hist(symbol=symbol, adjust="hfq").iloc[:, :6]
            df.columns = [
                'date',
                'open',
                'close',
                'high',
                'low',
                'volume',
            ]
            df.index = pd.to_datetime(df['date'])
            data = bt.feeds.PandasData(dataname=df, fromdate=datetime.datetime(2012, 4, 1),
                                    todate=datetime.datetime(2023, 4, 1))
            cerebro.adddata(data, name = symbol)
        # broker设置资金、手续费
        cerebro.broker.setcash(1000000.0)
        cerebro.broker.setcommission(commission=0.001)
        # 设置买入策略
        #cerebro.addsizer(TestSizer)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name = "sharpe",riskfreerate = 0.02848 )
        cerebro.addanalyzer(bt.analyzers.Returns, _name = "cagr")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name = "drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name = "trade")
        print('Start: {:.2f}'.format(cerebro.broker.getvalue()))
        # 启动回测
        stats = cerebro.run()
        print('End: {:.2f}'.format(cerebro.broker.getvalue()))
        print('Sharpe: {:.2f}'.format(stats[0].analyzers.sharpe.get_analysis()['sharperatio']))
        print('CAGR: {:.2f} '.format(stats[0].analyzers.cagr.get_analysis()['rnorm100']))
        print('drawdown: {:.2f}'.format(stats[0].analyzers.drawdown.get_analysis()['max']['drawdown']))
        print('MAR: {:.2f}'.format((stats[0].analyzers.cagr.get_analysis()['rnorm100']) / stats[0].analyzers.drawdown.get_analysis()['max']['drawdown']))
        print('total order time', order_count[current_strategy])
        print('trade total: ',(stats[0].analyzers.trade.get_analysis()['total']['total']))
        print('trade won: ',(stats[0].analyzers.trade.get_analysis()['won']['total']))
        current_strategy += 1
        # 曲线绘图输出
        p = BacktraderPlotting(style='bar')
        cerebro.plot(p)
    # 曲线绘图输出
    #cerebro.plot()

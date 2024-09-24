import akshare as ak
import math

stock_name = ak.stock_sh_a_spot_em()


class Turtle:
    def __init__(self):
        self.total_budget = 1000000
        self.count = {} #记录每只股票的单方向操作次数
        #self.symbols = ["600343"]
        self.symbols = ["600343", "601111", "600036", "600519", "600754", "600887", "600522", "601360", "600703", "600031"]
        self.position = {} #记录持仓
        self.instruments = {} #记录原始价格
        self.atr_book = {} #记录N值
        self.atr_df = {} #记录各种数据
        self.last_buy_price = 0.0
        self.operation_time = 0
        start_dates = ["20130101"]
        end_dates = ["20230401"]
        dates = ak.tool_trade_date_hist_sina()
        self.exchange_date = []
        self.trade_dates = {}
        flag = 0
        for date in dates['trade_date']:
            d = str(date)
            sd = d.replace("-", "")
            if sd > start_dates[0]:
                flag = 1
            if flag == 1:
                self.exchange_date.append(d)
            if sd > end_dates[0]:
                self.exchange_date.pop()
                break
        for symbol in self.symbols:
            self.atr_book[symbol] = [0]
            self.position[symbol] = 0
            self.trade_dates[symbol] = 0
            self.count[symbol] = 4
            # stock = stock_name[stock_name["代码"] == symbol]["名称"].values[0]
            for start_date in start_dates:
                for end_date in end_dates:
                    self.df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date,
                                                 end_date=end_date, adjust="hfq")
            self.instruments[symbol] = self.df.copy()
            last_close = self.df.iloc[0]["收盘"]
            for i in range(1, len(self.df)):
                row = self.df.iloc[i]
                t = (19 * self.atr_book[symbol][-1] + max(row["最高"] - row["最低"],
                                                          row["最高"] - last_close,
                                                          last_close - row["最低"])) / 20
                last_close = row["收盘"]
                self.atr_book[symbol].append(t)

            self.atr_df[symbol] = self.instruments[symbol].copy()
            self.atr_df[symbol].reset_index()
            self.atr_df[symbol].rename(columns={"日期": "index"}, inplace=True)
            self.atr_df[symbol] = self.atr_df[symbol][self.atr_df[symbol]["开盘"].notnull()]
            self.atr_df[symbol]['10MIN'] = self.atr_df[symbol]["最低"].rolling(window=10).min()
            self.atr_df[symbol]['20MAX'] = self.atr_df[symbol]["最高"].rolling(window=20).max()
            self.atr_df[symbol]['25AVG'] = self.atr_df[symbol]["收盘"].rolling(window=25).mean()
            self.atr_df[symbol]['100AVG'] = self.atr_df[symbol]["收盘"].rolling(window=100).mean()
            self.atr_df[symbol]['150AVG'] = self.atr_df[symbol]["收盘"].rolling(window=150).mean()
            self.atr_df[symbol]['250AVG'] = self.atr_df[symbol]["收盘"].rolling(window=250).mean()
            self.atr_df[symbol]['350AVG'] = self.atr_df[symbol]["收盘"].rolling(window=350).mean()

    def clear(self):
        for symbol in self.symbols:
            if self.position[symbol] > 0:
                self.total_budget += self.position[symbol] * self.instruments[symbol].iloc[-1]["收盘"]
                self.operation_time += 1
        print("final money : {:}, total operation : {:}".format(self.total_budget, self.operation_time))

    def calc_net_value(self, date, i): #计算当前净值
        net_value = self.total_budget
        for symbol in self.symbols:
            if self.position[symbol] > 0:
                net_value += self.position[symbol] * self.instruments[symbol].iloc[i]["收盘"]
        print("date : {:}, net value : {:}".format(date, net_value))

    def buy(self, i, symbol, buying, date):
        once_budget = self.get_once_budget(buying, i, symbol) / self.atr_book[symbol][i - 1]
        actual_position_update = min((once_budget // 100) * 100,
                                     ((self.total_budget / self.instruments[symbol].iloc[i][
                                         buying]) // 100) * 100)
        self.position[symbol] += actual_position_update
        self.total_budget -= actual_position_update * self.instruments[symbol].iloc[i][buying]
        self.count[symbol] -= 1
        self.operation_time += 1
        #print(date, symbol, "Buy", "{:.2f}".format(self.total_budget))
        return self.instruments[symbol].iloc[i][buying]

    def sell(self, i, symbol, selling, date):
        self.total_budget += self.instruments[symbol].iloc[i][selling] * self.position[symbol]
        self.position[symbol] = 0
        self.count[symbol] = 4
        self.operation_time += 1
        #print(date, symbol, "Sell", self.total_budget)

    def get_once_budget(self, pricing, day, instrument_name):
        money = min(100000, self.total_budget)
        money += self.position[instrument_name] * self.instruments[instrument_name].iloc[day][pricing]
        return money * 0.01
    def get_CAGR(self):
        print('{:.2f}'.format((pow(self.total_budget / 1000000, 1/10) - 1) * 100))


class ATR(Turtle):
    def __init__(self):
        super().__init__()
        print("ATR通道突破系统")

    def solve(self):
        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if (self.instruments[symbol].iloc[i - 1]["收盘"] > self.atr_df[symbol]['350AVG'][i - 1] + 7 *
                        self.atr_book[symbol][i - 1] and self.total_budget > 0 and self.count[symbol] == 4):
                    self.last_buy_price = self.buy(i, symbol, "开盘", date)
                elif (self.instruments[symbol].iloc[i - 1]["收盘"] > self.last_buy_price + 0.5 *
                        self.atr_book[symbol][i - 1] and self.total_budget > 0 and self.count[symbol] > 0 and self.count[symbol] < 4):
                    self.last_buy_price = self.buy(i, symbol, "开盘", date)
                if (self.instruments[symbol].iloc[i - 1]["收盘"] < self.atr_df[symbol]['350AVG'][i - 1] - 3 *
                        self.atr_book[symbol][i - 1] and self.position[symbol] > 0):
                    self.sell(i, symbol, "开盘", date)
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget

class Bollinger(Turtle):
    def __init__(self):
        super().__init__()
        print("布林线突破系统")

    def solve(self):
        stds = {}
        for symbol in self.symbols:
            stds[symbol] = {}
            for index, row in self.instruments[symbol].iterrows():
                if (index < 349):
                    stds[symbol][row['日期']] = 0
                    continue
                df_data_temp = self.instruments[symbol].iloc[max(0, index - 349): index]["收盘"]
                std = df_data_temp.std()
                stds[symbol][row['日期']] = std
        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if (self.instruments[symbol].iloc[i - 1]["收盘"] >
                        self.atr_df[symbol]['350AVG'][i - 1] + 2.5 *stds[symbol][date]
                        and self.total_budget > 0 and self.count[symbol] == 4):
                    self.last_buy_price = self.buy(i, symbol, "开盘", date)
                elif (self.instruments[symbol].iloc[i - 1]["收盘"] >
                        self.last_buy_price + 0.5 * self.atr_book[symbol][i - 1]
                        and self.total_budget > 0 and self.count[symbol] > 0 and self.count[symbol] < 4):
                    self.last_buy_price = self.buy(i, symbol, "开盘", date)
                if (self.instruments[symbol].iloc[i - 1]["收盘"] < self.atr_df[symbol]['350AVG'][i - 1] - 2.5 * stds[
                    symbol][date]
                        and self.position[symbol] > 0):
                    self.sell(i, symbol, "开盘", date)
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget

class Donchian(Turtle):
    def __init__(self):
        super().__init__()
        print("唐奇安趋势系统")

    def solve(self):
        direction = 2  # 0代表买入, 1代表卖出
        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if self.atr_df[symbol]['25AVG'][i - 1] > self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 0  # 只能做多
                elif self.atr_df[symbol]['25AVG'][i - 1] < self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 1  # 只能做空
                else:
                    direction = 2  # 概率极低,但是既可以做多,也可以做空

                if self.instruments[symbol].iloc[i]["最高"] > self.atr_df[symbol]['20MAX'][
                    i - 1] and direction != 1 and self.total_budget > 0 and self.count[symbol] == 4:
                    self.last_buy_price = self.buy(i, symbol, "最高", date)
                elif self.instruments[symbol].iloc[i - 1]["收盘"] > self.last_buy_price + 0.5 * self.atr_book[symbol][i - 1] \
                        and direction != 1 and self.total_budget > 0 and self.count[symbol] > 0 and self.count[symbol] < 4:
                    self.last_buy_price = self.buy(i, symbol, "收盘", date)
                if self.instruments[symbol].iloc[i]["最低"] < self.atr_df[symbol]['10MIN'][
                    i - 1] and direction != 0 and self.position[symbol] > 0:
                    self.sell(i, symbol, "最低", date)
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget

class Donchian_Time(Turtle):
    def __init__(self):
        super().__init__()
        self.day_count = {}
        self.counts = {}
        for symbol in self.symbols:
            self.day_count[symbol] = []
            self.counts[symbol] = 0 #表示当前对应第几次到买入
        print("定时退出唐奇安趋势系统")

    def solve(self):
        direction = 2
        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if self.atr_df[symbol]['25AVG'][i - 1] > self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 0  # 只能做多
                elif self.atr_df[symbol]['25AVG'][i - 1] < self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 1  # 只能做空
                else:
                    direction = 2  # 概率极低,但是既可以做多,也可以做空
                if self.instruments[symbol].iloc[i]["最高"] > self.atr_df[symbol]['20MAX'][
                    i - 1] and self.total_budget > 0 and self.count[symbol] == 4 and direction != 1:
                    self.last_buy_price = self.buy(i, symbol, "最高", date)
                    self.day_count[symbol].append(i)
                elif self.instruments[symbol].iloc[i - 1]["收盘"] > self.last_buy_price + 0.5 * self.atr_book[symbol][i - 1] \
                        and direction != 1 and self.total_budget > 0 and self.count[symbol] > 0 and self.count[symbol] < 4:
                    self.last_buy_price = self.buy(i, symbol, "收盘", date)
                    self.day_count[symbol].append(i)
                if self.position[symbol] > 0 and i - self.day_count[symbol][self.counts[symbol]] >= 80:
                    self.sell(i, symbol, "开盘", date)
                    self.counts[symbol] += 1
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget


class DualCross(Turtle):
    def __init__(self):
        super().__init__()
        print("双重移动平均线系统")

    def solve(self):

        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if self.total_budget > 0 and self.atr_df[symbol]['100AVG'][i - 1] > self.atr_df[symbol]['350AVG'][
                    i - 1] and self.count[symbol] > 0:
                    self.buy(i, symbol, "开盘", date)
                if self.position[symbol] > 0 and self.atr_df[symbol]['100AVG'][i - 1] < self.atr_df[symbol]['350AVG'][
                    i - 1]:
                    self.sell(i, symbol, "开盘", date)
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget


class TripleCross(Turtle):
    def __init__(self):
        super().__init__()
        self.direction = 2  # 0代表买入, 1代表卖出, 2代表不能交易
        print("三重移动平均线系统")

    def solve(self):
        for date in self.exchange_date:
            for symbol in self.symbols:
                i = self.trade_dates[symbol]
                if date != self.instruments[symbol].iloc[i]["日期"]:
                    continue
                if (i == 0 or math.isnan(self.atr_df[symbol]['350AVG'][i - 1])):
                    self.trade_dates[symbol] += 1
                    continue
                if self.atr_df[symbol]['150AVG'][i - 1] > self.atr_df[symbol]['350AVG'][i - 1] \
                        and self.atr_df[symbol]['250AVG'][i - 1] > self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 0
                elif self.atr_df[symbol]['150AVG'][i - 1] < self.atr_df[symbol]['350AVG'][i - 1] \
                        and self.atr_df[symbol]['250AVG'][i - 1] < self.atr_df[symbol]['350AVG'][i - 1]:
                    direction = 1
                else:
                    direction = 2

                if self.total_budget > 0 and direction == 0 and self.atr_df[symbol]['150AVG'][i - 1] > \
                        self.atr_df[symbol]['250AVG'][i - 1] and self.count[symbol] > 0:
                    self.buy(i, symbol, "开盘", date)
                if self.position[symbol] > 0 and direction == 1 and self.atr_df[symbol]['150AVG'][i - 1] < \
                        self.atr_df[symbol]['250AVG'][i - 1]:
                    self.sell(i, symbol, "开盘", date)
                self.trade_dates[symbol] += 1
        self.clear()
        return self.total_budget


atr = ATR()
atr.solve()
print("atr CAGR:")
atr.get_CAGR()
bol = Bollinger()
bol.solve()
print("Bollinger CAGR:")
bol.get_CAGR()
don = Donchian()
don.solve()
print("Donchian CAGR:")
don.get_CAGR()
dt = Donchian_Time()
dt.solve()
print("Donchian_Time CAGR:")
dt.get_CAGR()
dbc = DualCross()
dbc.solve()
print("DualCross CAGR:")
dbc.get_CAGR()
tc = TripleCross()
tc.solve()
print("TripleCross CAGR:")
tc.get_CAGR()

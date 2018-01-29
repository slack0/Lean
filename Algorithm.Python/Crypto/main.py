# For moving avg types: https://github.com/QuantConnect/Lean/blob/bc9af8784b02715000a2030e9757ef63b484378e/Indicators/MovingAverageType.cs

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
import numpy as np

import QuantConnect.Indicators as ind
from QuantConnect.Brokerages import BrokerageName
from QuantConnect.Data.Consolidators import TradeBarConsolidator
from QuantConnect.Orders import OrderDirection

import json
import os

class IndicatorAlgo(QCAlgorithm):
    def Initialize(self):
        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.config_file = os.path.join(self.cwd,'configs','config.json')
        self.runconfig = {}

        try:
            fp = open(self.config_file, 'r')
            self.runconfig = json.load(fp)
        except IOError:
            print('config file: {} not found. Continuing with pre-configured settings'.format(self.config_file))

        #####################
        # Backtest Settings #
        #####################
        self.SetStartDate(2016, 10, 7)  # Set Start Date
        self.SetEndDate(2016, 10, 8)  # Set End Date
        self.SetCash(1000)  # Set Strategy Cash
        self.SetBrokerageModel(BrokerageName.GDAX)

        ###########################
        # Configurable parameters #
        ###########################
        # Can be ETHUSD, LTCUSD, BTCUSD, or BCCUSD
        if '__TARGET_CRYPTOS__' in self.runconfig:
            self.target_crypto = str(self.runconfig['__TARGET_CRYPTOS__'])
        else:
            self.target_crypto = "BTCUSD"

        # bollinger, momentum, or MACD
        if '__INDICATORS__' in self.runconfig:
            self.indicator_name = str(self.runconfig['__INDICATORS__'])
        else:
            self.indicator_name = "macd"

        # Number of time periods resolution to load
        if '__WARMUP_LOOKBACK__' in self.runconfig:
            self.warmup_lookback = self.runconfig['__WARMUP_LOOKBACK__']
        else:
            self.warmup_lookback = 30

        # Resolution of periods/data to use
        self.time_resolution = Resolution.Minute

        # Percent at which we will update the limit order to cause a fill
        if '__RESUBMIT_ORDER_THRESHOLD__' in self.runconfig:
            self.resubmit_order_threshold = self.runconfig['__RESUBMIT_ORDER_THRESHOLD__']
        else:
            self.resubmit_order_threshold = 0.01

        # Bar size
        if '__BAR_SIZE__' in self.runconfig:
            self.bar_size = self.runconfig['__BAR_SIZE__']
        else:
            self.bar_size = 5

        # Bollinger Variables
        if 'MOVING_AVERAGE_TYPE' in self.runconfig:
            self.moving_average_type = getattr(ind, str(self.runconfig['MOVING_AVERAGE_TYPE']))
        else:
            self.moving_average_type = ind.MovingAverageType.Exponential

        if 'BOLLINGER_PERIOD' in self.runconfig:
            self.bollinger_period = self.runconfig['BOLLINGER_PERIOD']
        else:
            self.bollinger_period = 20

        if 'BOLLINGER_K' in self.runconfig:
            self.k = self.runconfig['BOLLINGER_K']
        else:
            self.k = 2

        # Momentum Variables
        if 'MOMENTUM_PERIOD' in self.runconfig:
            self.momentum_period = self.runconfig['MOMENTUM_PERIOD']
        else:
            self.momentum_period = 5

        if 'MOMENTUM_BUY_THRESHOLD' in self.runconfig:
            self.momentum_buy_threshold = self.runconfig['MOMENTUM_BUY_THRESHOLD']
        else:
            self.momentum_buy_threshold = 2

        if 'MOMENTUM_SELL_THRESHOLD' in self.runconfig:
            self.momentum_sell_threshold = self.runconfig['MOMENTUM_SELL_THRESHOLD']
        else:
            self.momentum_sell_threshold = 0

        # MACD Variables
        if 'MACD_FAST_PERIOD' in self.runconfig:
            self.MACD_fast_period = self.runconfig['MACD_FAST_PERIOD']
        else:
            self.MACD_fast_period = 12

        if 'MACD_SLOW_PERIOD' in self.runconfig:
            self.MACD_slow_period = self.runconfig['MACD_SLOW_PERIOD']
        else:
            self.MACD_slow_period = 26

        if 'MACD_SIGNAL_PERIOD' in self.runconfig:
            self.MACD_signal_period = self.runconfig['MACD_SIGNAL_PERIOD']
        else:
            self.MACD_signal_period = 9

        if 'MACD_MOVING_AVERAGE_TYPE' in self.runconfig:
            self.MACD_moving_average_type = getattr(ind, str(self.runconfig['MACD_MOVING_AVERAGE_TYPE']))
        else:
            self.MACD_moving_average_type = ind.MovingAverageType.Exponential

        if 'MACD_TOLERANCE' in self.runconfig:
            self.MACD_tolerance = self.runconfig['MACD_TOLERANCE']
        else:
            self.MACD_tolerance = 0.0025

        # Ichimoku Variables
        if 'TENKAN_PERIOD' in self.runconfig:
            self.tenkanPeriod = self.runconfig['TENKAN_PERIOD']
        else:
            self.tenkanPeriod = 9

        if 'KIJUN_PERIOD' in self.runconfig:
            self.kijunPeriod = self.runconfig['KIJUN_PERIOD']
        else:
            self.kijunPeriod = 26

        if 'SENKOU_A_PERIOD' in self.runconfig:
            self.senkouAPeriod = self.runconfig['SENKOU_A_PERIOD']
        else:
            self.senkouAPeriod = 26

        if 'SENKOU_B_PERIOD' in self.runconfig:
            self.senkouBPeriod = self.runconfig['SENKOU_B_PERIOD']
        else:
            self.senkouBPeriod = 52

        if 'SENKOU_A_DELAYED_PERIOD' in self.runconfig:
            self.senkouADelayedPeriod = self.runconfig['SENKOU_A_DELAYED_PERIOD']
        else:
            self.senkouADelayedPeriod = 26

        if 'SENKOU_B_DELAYED_PERIOD' in self.runconfig:
            self.senkouBDelayedPeriod = self.runconfig['SENKOU_B_DELAYED_PERIOD']
        else:
            self.senkouBDelayedPeriod = 26

        ############################
        # Indicators and processes #
        ############################
        # Add Symbol
        self.AddCrypto(self.target_crypto, self.time_resolution)

        barConsolidator = TradeBarConsolidator(TimeSpan.FromMinutes(self.bar_size))
        barConsolidator.DataConsolidated += self.barHandler
        self.SubscriptionManager.AddConsolidator(self.target_crypto, barConsolidator)

        # Create charts
        pricePlot = Chart('%s Price Plot' % self.target_crypto)
        pricePlot.AddSeries(Series('Price', SeriesType.Line, 0))
        self.AddChart(pricePlot)

        holdingsPlot = Chart('%s Holdings Plot' % self.target_crypto)
        holdingsPlot.AddSeries(Series('Holdings', SeriesType.Line, 0))
        self.AddChart(holdingsPlot)

        # Create the different indicators
        if self.indicator_name == "bollinger":
            # Create bollinger band
            self.Bolband = self.BB(self.target_crypto, self.bollinger_period, self.k, self.moving_average_type,
                                   self.time_resolution)
        elif self.indicator_name == "momentum":
            # Create a momentum indicator over 3 days
            self.mom = self.MOM(self.target_crypto, self.momentum_period, self.time_resolution)
        elif self.indicator_name == "macd":
            # Create the MACD
            self.macd = self.MACD(self.target_crypto, self.MACD_fast_period, self.MACD_slow_period,
                                  self.MACD_signal_period, self.MACD_moving_average_type, self.time_resolution)
            self.RegisterIndicator(self.target_crypto, self.macd, barConsolidator)
        elif self.indicator_name == "ichimoku":
            self.ichimoku = self.ICHIMOKU(self.target_crypto, self.tenkanPeriod, self.kijunPeriod, self.senkouAPeriod,
                                          self.senkouBPeriod, self.senkouADelayedPeriod, self.senkouBDelayedPeriod,
                                          self.time_resolution * self.time_resolution)

        # Processing variables
        self.pending_limit_price = 0

        #####################
        # Scheduled Actions #
        #####################
        self.Schedule.On(self.DateRules.EveryDay(self.target_crypto), self.TimeRules.At(12, 0),
                         Action(self.PlotCryptoIndicator))

    def OnData(self, data):
        ##########################
        # OnData Processing Vars #
        ##########################
        last_price = self.Securities[self.target_crypto].Close
        buy_price = self.Securities[self.target_crypto].BidPrice
        sell_price = self.Securities[self.target_crypto].AskPrice

        ###############################
        # OnData Processing Functions #
        ###############################
        # Update limit order if the price moves
        if len(self.Transactions.GetOpenOrders(self.target_crypto)) > 0:
            open_order = self.Transactions.GetOpenOrders(self.target_crypto)[0]
            if abs(float(self.pending_limit_price - last_price) / float(
                    self.pending_limit_price)) > self.resubmit_order_threshold:
                # self.Debug("Open Order Price: %s last_price: %s percent change: %s resubmit_order_threshold: %s order direction:%s" % (self.pending_limit_price, last_price,abs(float(self.pending_limit_price - last_price) / float(self.pending_limit_price)),self.resubmit_order_threshold,open_order.Direction))
                limit_price = buy_price if open_order.Direction == 0 else sell_price
                # self.Debug("Updating order to limit price of %s, amount of %s, and direction of %s" % (str(limit_price),str(amount),str(open_order.Direction)))
                self.Transactions.CancelOrder(open_order.Id)
                self.LimitOrder(self.target_crypto, open_order.Quantity, limit_price)
                self.pending_limit_price = limit_price
            return

    def PlotCryptoIndicator(self):
        # Chart the crypto price
        self.Plot('%s Price Plot' % self.target_crypto, 'Price', self.Securities[self.target_crypto].Close)
        self.Plot('%s Holdings Plot' % self.target_crypto, 'Holdings',
                  float(self.Portfolio[self.target_crypto].Quantity))

    def barHandler(self, sender, bar):
        ##########################
        # OnData Processing Vars #
        ##########################
        holdings = self.Portfolio[self.target_crypto].Quantity
        last_price = self.Securities[self.target_crypto].Close
        buy_price = self.Securities[self.target_crypto].BidPrice
        sell_price = self.Securities[self.target_crypto].AskPrice
        amount = float(self.Portfolio.GetBuyingPower(self.target_crypto, OrderDirection.Buy) / last_price)

        if len(self.Transactions.GetOpenOrders(self.target_crypto)) > 0:
            return

        ###################
        # Indicator Logic #
        ###################
        if self.indicator_name == "bollinger":
            # buy if price closes above upper bollinger band
            # sell if price closes below middle bollinger band
            if holdings == 0 and last_price > self.Bolband.UpperBand.Current.Value:
                self.LimitOrder(self.target_crypto, amount, buy_price)
                self.pending_limit_price = buy_price
            elif holdings > 0 and last_price < self.Bolband.MiddleBand.Current.Value:
                self.LimitOrder(self.target_crypto, -holdings, sell_price)
                self.pending_limit_price = sell_price
        elif self.indicator_name == "momentum":
            mom = self.mom.Current.Value
            if holdings == 0 and mom > self.momentum_buy_threshold:
                self.LimitOrder(self.target_crypto, amount, buy_price)
                self.pending_limit_price = buy_price
            elif holdings > 0 and mom < self.momentum_sell_threshold:
                self.LimitOrder(self.target_crypto, -holdings, sell_price)
                self.pending_limit_price = sell_price
        elif self.indicator_name == "macd":
            if not self.macd.IsReady:
                return
            signalDeltaPercent = (self.macd.Current.Value - self.macd.Signal.Current.Value) / self.macd.Fast.Current.Value

            if holdings == 0 and signalDeltaPercent > self.MACD_tolerance:
                self.LimitOrder(self.target_crypto, amount, buy_price)
                self.pending_limit_price = buy_price
            elif holdings > 0 and signalDeltaPercent < -self.MACD_tolerance:
                self.LimitOrder(self.target_crypto, -holdings, sell_price)
                self.pending_limit_price = sell_price
        elif self.indicator_name == "ichimoku":
            if not self.ichimoku.IsReady:
                return
            # self.Debug("TenkanMax: %s Tenkan: %s" % (str(self.ichimoku.TenkanMaximum.Current.Value), str(self.ichimoku.Tenkan.Current.Value)))
            if holdings == 0 and (self.ichimoku.Tenkan.Current.Value > self.ichimoku.Kijun.Current.Value
                                  and self.ichimoku.SenkouA.Current.Value > self.ichimoku.SenkouB.Current.Value
                                  and last_price > self.ichimoku.SenkouA.Current.Value):
                self.LimitOrder(self.target_crypto, amount, buy_price)
                self.pending_limit_price = buy_price
            elif holdings > 0 and (self.ichimoku.Tenkan.Current.Value <= self.ichimoku.Kijun.Current.Value
                                   and self.ichimoku.SenkouA.Current.Value < self.ichimoku.SenkouB.Current.Value
                                   and last_price < self.ichimoku.SenkouA.Current.Value):
                self.LimitOrder(self.target_crypto, -holdings, sell_price)
                self.pending_limit_price = sell_price

    # def OnOrderEvent(self, orderEvent):
    #    order = self.Transactions.GetOrderById(orderEvent.OrderId)
    #    self.Debug("{0}: {1}: {2}".format(self.Time, order.Type, orderEvent))

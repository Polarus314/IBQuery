
# 尝试使用官方 API 从 IBKR TWS 获取市场数据，获取 NDX 指数、指数期权的行情信息，进行计算后给出 NQ 期货的合理报价
from ibapi.client import *
from ibapi.wrapper import *
from ibapi.ticktype import TickTypeEnum
import redis

class App(EClient, EWrapper):
    myRedis = None #redis对象

    def __init__(self):
        EClient.__init__(self, self)
        self.myRedis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True) # 连接到 Redis
        self.myRedis.flushdb() # 清空当前数据库中的所有数据
        self.reqId = 1  # 追踪请求 ID
        self.contractConId = None  # 用来存储 contract 的 conId

    def nextValidId(self, orderId : OrderId):
        self.orderID = orderId
        
    def nextID(self):
        self.orderID += 1
        return self.orderID
    
    def error(self, reqId, errorCode, errorString, advancedOrderReject = None):
        print(f"reqID: {reqId}, errorCode: {errorCode}, errorString:{errorString}, orderReject: {advancedOrderReject}")


    def tickPrice(self, reqId, tickType, price, attrib):
        """
        Name        ID          描述
        Bid Price   1           最高出价
        Ask Price   2           最低报价
        Last Price	4           该合约的最后价格
        High        6           当日最高价
        Low	        7           当日最低价
        Close Price	9           前一日最后收盘价
        """

        if TickTypeEnum.to_str(tickType) == "LAST":
            # print(f"LastPrice for reqId {reqId}: {price}") # 直接打印最后价格
            self.myRedis.hset(str(reqId), 'LAST', price) # 请求编号为 reqId 的最后价格
        elif TickTypeEnum.to_str(tickType) == "BID":
            self.myRedis.hset(str(reqId), 'BID', price) # 请求编号为 reqId 的 BID 报价
        elif TickTypeEnum.to_str(tickType) == "ASK":
            self.myRedis.hset(str(reqId), 'ASK', price) # 请求编号为 reqId 的 ASK 报价

        if (self.myRedis.hexists(str(reqId), "BID")) and (self.myRedis.hexists(str(reqId), "ASK")):
            mid_price = (float(self.myRedis.hget(str(reqId), "BID")) + float(self.myRedis.hget(str(reqId), "ASK"))) / 2 # bidask中间价
            self.myRedis.hset(str(reqId), "MID", mid_price) # 请求编号为 reqId 的 bidask 中间报价
        
        # 完整tickPrice信息：
        # print(f"reqID: {reqId}, tickType: {TickTypeEnum.to_str(tickType)}, price: {price}, attrib: {attrib}")
        return


    def tickSize(self, reqId, tickType, size):
        """
        Name        ID      描述
        Bid Size    0       以 BID 价格提交的数量
        Ask Size    3       以 ASK 价格提交的数量
        Last Size   5       按最后价格成交的数量
        Volume	    8       当日交易量
        """
        if TickTypeEnum.to_str(tickType) == "BID_SIZE":
            self.myRedis.hset(str(reqId), 'BID_SIZE', size) # 请求编号为 reqId 的 BID 报价的大小
            # print(f"BID_SIZE for reqId {reqId}: {size}")
        elif TickTypeEnum.to_str(tickType) == "ASK_SIZE":
            self.myRedis.hset(str(reqId), 'ASK_SIZE', size) # 请求编号为 reqId 的 ASK 报价的大小
        # 完整tickSize信息：
        # print(f"reqId: {reqId}, tickType: {TickTypeEnum.to_str(tickType)}, size: {size}")
        return
    
    def contractDetails(self, reqId, contractDetails):
        """处理合约详细信息，获取 conId"""
        print(f"ContractDetails received: {contractDetails}")
        # 一旦接收到合约详细信息，获取 conId
        contract = contractDetails.contract
        self.contractConId = contract.conId
        print(f"Received conId: {self.contractConId}")
        
        # 获取到 conId 后，发送市场数据请求
        self.reqMktData(reqId, contract, "", False, False, [])  # 获取实时行情数据

    def contractDetailsEnd(self, reqId):
        """合约详情结束"""
        # print(f"End of contract details for reqId {reqId}")
        return

    def get_stock_contract(self, symbol):
        """获取一个股票合约对象，参数是股票代码的字符串,
        若获取不到数据,请尝试更改reqMarketDataType类型"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK" # 股票类型
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract

    def get_index_contract(self, symbol, exchange):
        """获取一个指数合约对象，参数是指数代码字符串、交易所,
        若获取不到数据,请尝试更改reqMarketDataType类型"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "IND" # 指数类型
        contract.exchange = exchange
        contract.currency = "USD"
        return contract
    
    def get_futures_contract(self, symbol, expiry, exchange, currency="USD"):
        """获取期货合约对象"""
        contract = Contract()
        contract.symbol = symbol          # 期货合约的符号，比如 'ES' (E-mini S&P 500)
        contract.secType = "FUT"          # 期货合约的类型
        contract.exchange = exchange      # 交易所，默认使用 GLOBEX
        contract.currency = currency      # 货币类型，默认使用 USD
        contract.lastTradeDateOrContractMonth = expiry  # 到期日或合约月份，例如 "202303" 或 "2023-12-31"
        return contract

    def get_option_contract(self, symbol, lastTradeDateOrContractMonth, strike, right):
        """获取一个期权合约对象，参数是期权代码、最后交易日、行权价、期权类型
        若获取不到数据,请尝试更改reqMarketDataType类型"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"  # 类型:期权
        contract.exchange = "SMART"  # 交易所
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth  # 到期日
        contract.strike = strike  # 行权价
        contract.right = right  # Call 期权
        return contract

    def marketDataType(self, app, type):
        """
        API 可以在使用 reqMktData 发出市场数据请求之前通过IBApi.EClient.reqMarketDataType切换市场数据类型,
        从而从 Trader Workstation 请求实时、冻结、延迟和延迟冻结市场数据。
        ID      类型        描述
        1       实时        实时市场数据是实时回传的流数据。需要订阅市场数据才能接收实时市场数据。
        2       冻结        冻结市场数据是收盘时记录的最后数据。在 TWS 中，冻结数据以灰色数字显示。
                            当您将市场数据类型设置为冻结时，您要求 TWS 发送最后可用的报价（如果当前没有可用报价）。
                            例如，如果市场当前已关闭并且请求实时数据，则买入价和卖出价通常会返回 -1 值，以表明当前没有可用的买入/卖出数据。
        3       延迟        免费的延迟数据延迟 15 - 20 分钟。在 TWS 中，延迟数据以棕色背景显示。
                            当您将市场数据类型设置为延迟时，您是在告诉 TWS,如果用户没有必要的实时数据订阅，则自动切换到延迟市场数据。
                            如果有实时数据，则 TWS 将忽略延迟数据请求。
        4       延迟冻结    对于没有市场数据订阅的用户，请求延迟“冻结”数据。
        """
        if type == "Live":
            app.reqMarketDataType(1)
        elif type == "Frozen":
            app.reqMarketDataType(2)
        elif type == "Delayed":
            app.reqMarketDataType(3)
        elif type == "DelayedFrozen":
            app.reqMarketDataType(4)
        return
        
    def showMarkData(self, contract, reqId):
        """展示合约市场数据"""
        # 请求合约详细信息，以获取 conId
        self.reqContractDetails(reqId, contract)

    def position(self, account, contract, position, avgCost):
        """处理持仓信息"""
        symbol = contract.symbol
        secType = contract.secType
        exchange = contract.exchange
        
        # 调试信息 - 打印整个合约对象的属性
        print(f"Debug - Contract for {symbol} ({secType}):")
        if secType == "OPT":
            print(f"  Contract details: {dir(contract)}")
        
        # 更健壮的属性获取方式
        try:
            expiry = contract.lastTradeDateOrContractMonth if hasattr(contract, 'lastTradeDateOrContractMonth') else ""
            strike = contract.strike if hasattr(contract, 'strike') else 0
            right = contract.right if hasattr(contract, 'right') else ""
            
            # 尝试从contract.Contract属性中获取
            if secType == "OPT" and (not expiry or not strike or not right):
                if hasattr(contract, 'contract'):
                    inner_contract = contract.contract
                    expiry = inner_contract.lastTradeDateOrContractMonth if not expiry and hasattr(inner_contract, 'lastTradeDateOrContractMonth') else expiry
                    strike = inner_contract.strike if not strike and hasattr(inner_contract, 'strike') else strike
                    right = inner_contract.right if not right and hasattr(inner_contract, 'right') else right
        except Exception as e:
            print(f"Error getting option details: {e}")
            expiry = ""
            strike = 0
            right = ""
        
        # 尝试访问其他可能的属性名称
        if secType == "OPT" and not expiry:
            possible_expiry_attrs = ['expiry', 'expirationDate', 'expDate', 'expiration']
            for attr in possible_expiry_attrs:
                if hasattr(contract, attr):
                    expiry = getattr(contract, attr)
                    print(f"Found expiry in attribute: {attr}")
                    break
        
        position_key = f"position:{symbol}:{secType}"
        if expiry:
            position_key += f":{expiry}"
        if strike > 0:
            position_key += f":{strike}:{right}"
        
        # 将持仓信息存储到Redis
        self.myRedis.hset(position_key, "account", account)
        self.myRedis.hset(position_key, "symbol", symbol)
        self.myRedis.hset(position_key, "secType", secType)
        self.myRedis.hset(position_key, "exchange", exchange)
        self.myRedis.hset(position_key, "position", position)
        self.myRedis.hset(position_key, "avgCost", avgCost)
        
        # 存储期权特有信息
        if expiry:
            self.myRedis.hset(position_key, "expiry", expiry)
        if strike > 0:
            self.myRedis.hset(position_key, "strike", strike)
        if right:
            self.myRedis.hset(position_key, "right", right)
        
        # 打印持仓信息
        contract_desc = f"{symbol} ({secType})"
        if secType == "OPT":
            option_info = []
            if expiry: option_info.append(f"到期:{expiry}")
            if strike > 0: option_info.append(f"行权价:{strike}")
            if right: option_info.append(f"{right}")
            if option_info:
                contract_desc += f" {' '.join(option_info)}"
            else:
                contract_desc += " (期权详情未获取到)"
        elif secType == "FUT" and expiry:
            contract_desc += f" {expiry}"
        
        print(f"Position: {account}, {contract_desc}: {position} @ {avgCost}")

    def positionEnd(self):
        """持仓信息接收完毕"""
        print("======== End of Positions ========")
        
    def accountSummary(self, reqId, account, tag, value, currency):
        """处理账户摘要信息"""
        key = f"account:{account}:{tag}"
        self.myRedis.set(key, value)
        print(f"Account Summary: {account}, {tag}: {value} {currency}")

    def accountSummaryEnd(self, reqId):
        """账户摘要信息接收完毕"""
        print("======== End of Account Summary ========")




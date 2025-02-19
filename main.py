import time
import threading
import IBQ
import redis

# contract1 = app.getOPTcontract("NDX", "20271216", 21700, "C")
# contract = app.getINDcontract("NDX", "NASDAQ") # 配置 NDX 指数的合约

port = 7496  # TWS的端口号

# 初始化 API 连接
app = IBQ.App()
app.connect("127.0.0.1", port, 0)

# 运行 IB API 事件循环
threading.Thread(target=app.run, daemon=True).start()
time.sleep(1)  # 确保连接已建立

contract_tqqq = app.get_stock_contract("TQQQ")
contract_ndx = app.get_index_contract("NDX", "NASDAQ") # 配置 NDX 指数的合约
# contract_nq = app.get_futures_contract("MNQ", "20260320", "CME")


strike = 22000 # 行权价
contract_call = app.get_option_contract("NDX", "20271216", strike, "C")
contract_put = app.get_option_contract("NDX", "20271216", strike, "P")

# 设置市场数据类型为延迟数据
app.marketDataType(app, "Delayed")

# 请求并显示市场数据，使用不同的 reqId 来避免冲突
app.showMarkData(contract_call, reqId=1)  # 获取 ndx call 的行情数据
app.showMarkData(contract_put, reqId=2)  # 获取 ndx put 的行情数据
app.showMarkData(contract_ndx, reqId=3)
app.showMarkData(contract_tqqq,reqId=4)

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True) # 连接到 Redis


# 计算 TQQQ 持仓的最小值、最大值、中点值
while True:
    if (r.hget("4", "LAST") is not None) and (r.hget("3", "LAST") is not None):
        ndx_value = 40 * float(r.hget("3", "LAST")) # 期货空头的市值
        min_amount = ndx_value / (float(r.hget("4", "LAST")) * 3) # 期货空头市值除以 TQQQ 的底层市值
        max_amount = min_amount + 3200 # 最小值加上 TQQQ Long Put 保护量
        mid_amount = (min_amount + max_amount) / 2 # 最小值和最大值的中点
        print("tqqq 最小值:", min_amount) 
        print("tqqq 中点值:", mid_amount)
        print("tqqq 最大值:", max_amount)
    print()
    time.sleep(0.3)

# 根据指数期权报价推算出指数期货等效报价
# while True:
#     if (r.hget("4", "LAST") is not None) and (r.hget("1", "MID") is not None) and (r.hget("2", "MID") is not None) and (r.hget("3", "LAST") is not None):
#         call_mid = float(r.hget("1", "MID"))
#         put_mid = float(r.hget("2", "MID"))
#         ndx_last = float(r.hget("3", "LAST"))
#         print("NQ期货报价:", ndx_last + call_mid - put_mid + (ndx_last - strike))
#         print("开仓后所需 tqqq 股数:", ndx_last * 20 / (float(r.hget("4", "LAST")) * 3))

#     print()
#     time.sleep(0.5)  # 等待 0.5 秒


from ibapi.client import *
from ibapi.wrapper import *
import time
import threading
import IBQ
import redis

def get_full_option_details(app, positions_data):
    """获取期权的完整详情"""
    print("\n正在获取期权合约详情...")
    
    # 为每个期权合约请求详细信息
    req_id_start = 1000  # 使用一个不冲突的请求ID范围
    
    for key in positions_data.keys("position:*"):
        if positions_data.hget(key, "secType") == "OPT" and float(positions_data.hget(key, "position") or 0) != 0:
            # 从Redis中获取基本信息
            symbol = positions_data.hget(key, "symbol")
            
            # 创建新的期权合约对象
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "OPT"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # 请求详细信息
            req_id = req_id_start
            app.reqContractDetails(req_id, contract)
            req_id_start += 1
    
    # 给API一些时间处理请求
    time.sleep(3)
    print("期权合约详情请求完成")

# 格式化持仓显示函数
def format_position_display(symbol, secType, position, avgCost, **kwargs):
    """格式化持仓信息显示"""
    try:
        position = float(position)
        avgCost = float(avgCost)
        
        if secType == "OPT":  # 期权
            expiry = kwargs.get("expiry", "未知")
            strike = kwargs.get("strike", "未知")
            right = kwargs.get("right", "未知")
            
            # 翻译期权类型
            option_type = "看涨" if right == "C" else "看跌" if right == "P" else right
            
            return f"{symbol} (期权): {position:,.0f} 张 @ ${avgCost:,.2f}, 到期日: {expiry}, 行权价: ${float(strike) if strike != '未知' else 0:,.1f}, 类型: {option_type}"
        
        elif secType == "FUT":  # 期货
            expiry = kwargs.get("expiry", "未知")
            return f"{symbol} (期货): {position:,.0f} 张 @ ${avgCost:,.2f}, 到期: {expiry}"
        
        else:  # 股票或其他
            unit = "股" if secType == "STK" else "单位"
            return f"{symbol} ({secType}): {position:,.0f} {unit} @ ${avgCost:,.2f}"
    except Exception as e:
        return f"{symbol} ({secType}): {position} @ {avgCost} - 格式化错误: {str(e)}"

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
# app.showMarkData(contract_qqq,reqId=5)

# 请求持仓信息
print("\n正在请求持仓信息...")
app.reqPositions()

# 给API一些时间来接收持仓数据
time.sleep(3)

# 可选：请求账户摘要信息
print("\n正在请求账户摘要信息...")
app.reqAccountSummary(100, "All", "$LEDGER")
time.sleep(2)

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True) # 连接到 Redis

# 请求期权的详细信息
get_full_option_details(app, r)

# 主循环
while True:
    # 打印当前所有持仓信息
    print("\n当前持仓:")
    for key in r.keys("position:*"):
        try:
            position_value = float(r.hget(key, "position") or 0)
            if position_value != 0:  # 只显示非零持仓
                symbol = r.hget(key, "symbol")
                secType = r.hget(key, "secType")
                position = r.hget(key, "position")
                avgCost = r.hget(key, "avgCost")
                
                # 使用格式化函数
                if secType == "OPT":
                    print(format_position_display(symbol, secType, position, avgCost, 
                        expiry=r.hget(key, "expiry"), 
                        strike=r.hget(key, "strike"), 
                        right=r.hget(key, "right")))
                elif secType == "FUT":
                    print(format_position_display(symbol, secType, position, avgCost, 
                        expiry=r.hget(key, "expiry")))
                else:
                    print(format_position_display(symbol, secType, position, avgCost))
        except Exception as e:
            print(f"错误处理持仓 {key}: {str(e)}")
    
    print()
    time.sleep(5)

    
# # 计算 TQQQ 持仓的最小值、最大值、中点值
# while True:
#     if (r.hget("4", "LAST") is not None) and (r.hget("3", "LAST") is not None):
#         ndx_value = 40 * float(r.hget("3", "LAST")) # 期货空头的市值
#         min_amount = ndx_value / (float(r.hget("4", "LAST")) * 3) # 期货空头市值除以 TQQQ 的底层市值
#         max_amount = min_amount + 3200 # 最小值加上 TQQQ Long Put 保护量
#         mid_amount = (min_amount + max_amount) / 2 # 最小值和最大值的中点
#         print("tqqq 最小值:", min_amount) 
#         print("tqqq 中点值:", mid_amount)
#         print("tqqq 最大值:", max_amount)

#     print()
#     time.sleep(1)

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

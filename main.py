
from ibapi.client import *
from ibapi.wrapper import *
import time
import threading
import IBQ
import redis
import random 

def get_full_option_details(app, positions_data):
    """
    获取期权的完整详情
    
    这个函数遍历Redis中存储的所有期权持仓，并为每个非零期权持仓发送合约详情请求，
    以获取完整的期权信息（如到期日、行权价和期权类型等）。使用随机生成的请求ID，
    避免与其他请求ID冲突。
    
    参数:
        app (IBQ.App): IB API客户端实例，用于发送请求
        positions_data (redis.Redis): Redis客户端实例，包含持仓数据
    """
    print("\n正在获取期权合约详情...")
    
    # 定义请求ID的范围
    min_req_id = 1000  # 最小请求ID值
    max_req_id = 9000  # 最大请求ID值
    
    # 记录已使用的请求ID，避免重复
    used_req_ids = set()
    
    # 遍历Redis中所有持仓记录
    for key in positions_data.keys("position:*"):
        # 仅处理非零数量的期权持仓
        if positions_data.hget(key, "secType") == "OPT" and float(positions_data.hget(key, "position") or 0) != 0:
            # 从Redis获取股票代码
            symbol = positions_data.hget(key, "symbol")
            
            # 创建新的期权合约对象
            contract = Contract()
            contract.symbol = symbol      # 设置股票代码
            contract.secType = "OPT"      # 设置证券类型为期权
            contract.exchange = "SMART"   # 使用SMART路由自动选择交易所
            contract.currency = "USD"     # 设置货币为美元
            
            # 生成一个随机且唯一的请求ID
            while True:
                req_id = random.randint(min_req_id, max_req_id)
                if req_id not in used_req_ids:
                    used_req_ids.add(req_id)
                    break
            
            # 发送合约详情请求
            # print(f"请求 {symbol} 期权详情，请求ID: {req_id}")
            app.reqContractDetails(req_id, contract)  # 这将触发contractDetails回调
    
    # 给API足够的时间处理所有请求并接收响应
    time.sleep(3)  # 等待3秒钟
    print(f"期权合约详情请求完成，共发送 {len(used_req_ids)} 个请求")

# 格式化持仓显示函数
def format_position_display(symbol, secType, position, avgCost, **kwargs):
    """
    格式化持仓信息显示
    
    根据不同的证券类型(股票、期权、期货)，格式化持仓信息的显示方式，
    美化输出格式，添加适当的单位和描述信息。
    
    参数:
        symbol (str): 证券代码
        secType (str): 证券类型(如STK、OPT、FUT等)
        position (str/float): 持仓数量
        avgCost (str/float): 持仓平均成本
        **kwargs: 额外参数，可包含期权或期货的特殊信息
            - expiry: 到期日
            - strike: 行权价
            - right: 期权类型(C为看涨，P为看跌)
    
    返回:
        str: 格式化后的持仓信息字符串
    """
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

# # 请求期权的详细信息
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

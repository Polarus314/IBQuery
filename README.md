# IBQuery
一个使用Interactive Brokers (IBKR) API实现的交易持仓监控工具，可以实时获取市场数据并展示账户持仓情况，支持股票、期权和期货。

# 免责声明
本软件仅供教育和研究目的使用。交易金融产品涉及风险，请在使用此代码进行真实交易前充分了解相关风险。作者对使用本软件造成的任何损失不承担责任。

注意：使用此软件需要有效的Interactive Brokers账户，并且可能需要特定的市场数据订阅。

# 功能特点
- 连接到Interactive Brokers Trader Workstation (TWS)或IB Gateway
- 获取和显示股票、指数、期权和期货的实时行情数据
- 监控和显示账户中的所有持仓信息，支持多种证券类型
- 获取期权的完整合约细节（到期日、行权价、期权类型等）
- 自动刷新持仓显示，呈现最新的持仓状态
- 使用Redis高效存储和管理市场数据与持仓信息
- 格式化输出，使持仓信息清晰易读

# 安装指南
## 前提条件
1. 安装并运行Interactive Brokers Trader Workstation (TWS)或IB Gateway
2. 安装Redis服务器
3. 安装Python 3.7或更高版本

使用前先要用 pip 安装 redis 和 ibapi 两个依赖：
```bash
pip install redis
pip install ibapi
```


## 配置TWS/IB Gateway：
- 启动TWS/IB Gateway
- 登录到您的IB账户
- 在TWS中启用API连接（设置 -> API -> 启用ActiveX和Socket客户端）
- 默认端口为7496（TWS）或4002（IB Gateway）
- 使用前请配置 IBKR TWS API 设置，允许 API 连接、确认端口号

下载后在目录下使用如下控制台命令运行：
```bash
python3 main.py
```
用法示例在 main.py 文件中


# 代码结构
项目包含两个主要的Python文件：

## IBQ.py
封装了与Interactive Brokers API交互的核心功能：

- 连接到TWS/IB Gateway
- 接收和处理市场数据
- 处理持仓和账户信息回调
- 将数据存储到Redis中
## main.py
程序的入口点，负责：

- 初始化IB API连接
- 请求市场数据和持仓信息
- 处理期权合约的详细信息
- 展示格式化的持仓信息
- 定期刷新持仓显示

# 示例输出
运行程序后，您将看到类似以下的持仓信息输出：
```apache
当前持仓:
TQQQ (STK): 6,325 股 @ $86.01
BIL (STK): 1,700 股 @ $91.56
VZ (期权): -5 张 @ $51.29, 到期日: 20240419, 行权价: $40.00, 类型: 看涨
MSFT (期权): -5 张 @ $264.63, 到期日: 20240419, 行权价: $400.00, 类型: 看涨
```
# 配置说明
如需修改连接设置或数据参数，可以在main.py中调整以下内容：

- port：TWS/IB Gateway的连接端口，默认为7496（TWS）
- 市场数据类型：可以设置为"Live"、"Frozen"、"Delayed"或"DelayedFrozen"
- 合约定义：可以自定义需要请求的股票、指数、期权或期货合约

# 常见问题
## 连接错误
- 确保TWS/IB Gateway已启动并登录
- 检查API设置是否已启用
- 验证连接端口是否正确
## 数据显示为"未知"
- 期权详情可能需要额外请求，程序会自动尝试获取
- 检查您的市场数据订阅是否支持请求的证券
## Redis连接错误
- 确保Redis服务器正在运行
- 检查默认连接设置（localhost:6379）

# 交易逻辑详解

## 🎯 从nof1.ai学到的核心逻辑

### 1. AI如何做出交易决策？

基于对 `UserPrompt.md` 和 `ChatOfTheThought.md` 的分析，AI的决策过程如下：

#### 决策树

```
每个币种的决策流程：

1. 是否有持仓？
   ├─ 有 → 检查失效条件
   │      ├─ 触发失效 → close_position
   │      └─ 未触发 → 分析技术指标
   │                  ├─ 趋势反转 → close_position
   │                  └─ 趋势延续 → hold
   │
   └─ 无 → 寻找入场机会
          ├─ 找到强信号 → entry
          └─ 无明确信号 → no_action
```

#### 关键判断因素

从 `ChatOfTheThought.md` 提取的AI思维模式：

```python
# 对于持仓（以ETH为例）
if position_exists:
    # 1. 检查失效条件
    if current_price < invalidation_price:
        decision = "close_position"
        reason = "Invalidation triggered"
    
    # 2. 分析当前状态
    elif rsi_7 < 30:  # 超卖
        if macd < 0 but macd_4h > 0:
            decision = "hold"
            reason = "Short-term oversold, but 4H trend still up"
        else:
            decision = "close_position"
            reason = "Momentum lost"
    
    elif rsi_7 > 70:  # 超买
        if price_above_profit_target:
            decision = "close_position"
            reason = "Take profit"
        else:
            decision = "hold"
            reason = "Let winner run"
    
    else:
        decision = "hold"
        reason = "No clear signal to exit"
```

### 2. 何时开仓？

从nof1.ai的实际运行数据推断的入场条件：

#### 多头入场信号

```python
def check_long_entry(data):
    """检查做多机会"""
    
    # 必要条件：
    conditions = []
    
    # 1. 短期趋势向上
    if data['current_price'] > data['ema_20']:
        conditions.append("Price above EMA20")
    
    # 2. RSI超卖反弹
    if 25 < data['rsi_7'] < 40:  # 刚走出超卖区
        conditions.append("RSI oversold bounce")
    
    # 3. MACD金叉或向上
    if data['macd'] > data['macd_signal']:
        conditions.append("MACD bullish")
    
    # 4. 长期趋势支撑
    if data['ema_20_4h'] > data['ema_50_4h']:
        conditions.append("4H trend up")
    
    # 5. 资金费率为负（多头不拥挤）
    if data['funding_rate'] < 0:
        conditions.append("Negative funding (shorts pay longs)")
    
    # 需要至少3个条件满足
    if len(conditions) >= 3:
        return True, conditions
    
    return False, []
```

#### 空头入场信号

```python
def check_short_entry(data):
    """检查做空机会"""
    
    conditions = []
    
    # 1. 短期趋势向下
    if data['current_price'] < data['ema_20']:
        conditions.append("Price below EMA20")
    
    # 2. RSI超买回落
    if 60 < data['rsi_7'] < 75:
        conditions.append("RSI overbought reversal")
    
    # 3. MACD死叉或向下
    if data['macd'] < data['macd_signal']:
        conditions.append("MACD bearish")
    
    # 4. 长期趋势压制
    if data['ema_20_4h'] < data['ema_50_4h']:
        conditions.append("4H trend down")
    
    # 5. 资金费率为正（空头机会）
    if data['funding_rate'] > 0.0001:
        conditions.append("Positive funding (longs pay shorts)")
    
    if len(conditions) >= 3:
        return True, conditions
    
    return False, []
```

### 3. 止损止盈如何设置？

从实际持仓数据分析（`UserPrompt.md` line 213）：

```python
# ETH持仓示例
position = {
    'entry_price': 3844.03,
    'stop_loss': 3714.95,      # -3.36% from entry
    'profit_target': 4227.35,  # +9.97% from entry
    'leverage': 15,
    'risk_usd': 624.38
}

# 风险回报比
risk_distance = 3844.03 - 3714.95  # 129.08
reward_distance = 4227.35 - 3844.03  # 383.32
risk_reward_ratio = 383.32 / 129.08  # ≈ 2.97:1
```

#### 止损设置逻辑

```python
def calculate_stop_loss(entry_price, atr, side='long'):
    """
    基于ATR动态设置止损
    
    Args:
        entry_price: 入场价格
        atr: 14周期ATR
        side: 'long' or 'short'
    
    Returns:
        stop_loss_price
    """
    # 通常使用1.5-2倍ATR作为止损距离
    sl_distance = atr * 1.5
    
    if side == 'long':
        stop_loss = entry_price - sl_distance
    else:  # short
        stop_loss = entry_price + sl_distance
    
    # 确保止损距离在3%-10%之间
    sl_percent = abs(stop_loss - entry_price) / entry_price * 100
    
    if sl_percent < 3:
        # 止损太近，调整到最小3%
        if side == 'long':
            stop_loss = entry_price * 0.97
        else:
            stop_loss = entry_price * 1.03
    
    elif sl_percent > 10:
        # 止损太远，调整到最大10%
        if side == 'long':
            stop_loss = entry_price * 0.90
        else:
            stop_loss = entry_price * 1.10
    
    return stop_loss
```

#### 止盈设置逻辑

```python
def calculate_take_profit(entry_price, stop_loss, min_rr_ratio=1.5):
    """
    基于止损和最小风险回报比设置止盈
    
    Args:
        entry_price: 入场价格
        stop_loss: 止损价格
        min_rr_ratio: 最小风险回报比（默认1.5:1）
    
    Returns:
        take_profit_price
    """
    risk_distance = abs(entry_price - stop_loss)
    reward_distance = risk_distance * min_rr_ratio
    
    if stop_loss < entry_price:
        # 做多
        take_profit = entry_price + reward_distance
    else:
        # 做空
        take_profit = entry_price - reward_distance
    
    return take_profit
```

### 4. 杠杆如何选择？

从实际持仓数据观察到的模式：

```python
# 杠杆与置信度的关系
leverage_map = {
    0.75: 15,  # 高置信度 → 高杠杆
    0.70: 15,
    0.65: 10,  # 中等置信度 → 中等杠杆
    0.60: 8,
    0.55: 5,   # 低置信度 → 低杠杆
    0.50: 5
}

def get_leverage(confidence, market_volatility):
    """
    根据置信度和市场波动性选择杠杆
    
    Args:
        confidence: AI置信度 (0.5-1.0)
        market_volatility: 市场波动率（ATR/价格）
    
    Returns:
        leverage: 杠杆倍数 (5-15)
    """
    # 基础杠杆（基于置信度）
    if confidence >= 0.75:
        base_leverage = 15
    elif confidence >= 0.70:
        base_leverage = 12
    elif confidence >= 0.65:
        base_leverage = 10
    elif confidence >= 0.60:
        base_leverage = 8
    else:
        base_leverage = 5
    
    # 根据波动性调整
    if market_volatility > 0.05:  # 高波动
        adjusted_leverage = max(base_leverage - 3, 5)
    elif market_volatility > 0.03:  # 中等波动
        adjusted_leverage = max(base_leverage - 1, 5)
    else:  # 低波动
        adjusted_leverage = base_leverage
    
    return min(adjusted_leverage, 15)  # 上限15倍
```

### 5. 仓位大小如何计算？

```python
def calculate_position_size(
    account_value,
    risk_percent,
    entry_price,
    stop_loss,
    leverage
):
    """
    计算仓位大小
    
    Args:
        account_value: 账户总价值
        risk_percent: 风险百分比（如2%）
        entry_price: 入场价格
        stop_loss: 止损价格
        leverage: 杠杆倍数
    
    Returns:
        position_size: 仓位大小（币数量）
    """
    # 1. 计算愿意承受的风险金额
    risk_usd = account_value * (risk_percent / 100)
    
    # 2. 计算每单位价格的风险
    risk_per_unit = abs(entry_price - stop_loss)
    
    # 3. 计算基础仓位（不考虑杠杆）
    base_position = risk_usd / risk_per_unit
    
    # 4. 实际仓位（杠杆不改变风险，只是需要的保证金更少）
    position_size = base_position
    
    # 5. 计算所需保证金
    required_margin = (position_size * entry_price) / leverage
    
    # 6. 检查保证金是否充足
    if required_margin > account_value * 0.3:
        # 单笔最多使用30%的资金作为保证金
        position_size = (account_value * 0.3 * leverage) / entry_price
    
    return position_size, risk_usd, required_margin
```

### 6. 失效条件的作用

失效条件 (`invalidation_condition`) 是nof1.ai的关键创新：

```python
# 示例失效条件
invalidation_conditions = {
    'ETH': 'If the price closes below 3800 on a 3-minute candle',
    'BTC': 'If the price closes below 105000 on a 3-minute candle',
    'SOL': 'If the price closes below 175 on a 3-minute candle'
}

def check_invalidation(position, current_price, candle_close_price):
    """
    检查失效条件是否触发
    
    失效条件 vs 止损的区别：
    - 止损：技术性保护，防止亏损扩大
    - 失效条件：策略性退出，入场逻辑不再成立
    
    失效条件通常比止损更宽松，作为最后防线
    """
    condition = position['exit_plan']['invalidation_condition']
    
    # 解析条件
    if 'closes below' in condition:
        threshold = float(condition.split('below')[1].split('on')[0].strip())
        
        # 必须是K线收盘价，而非实时价
        if candle_close_price < threshold:
            return True, f"Price closed below {threshold}"
    
    elif 'closes above' in condition:
        threshold = float(condition.split('above')[1].split('on')[0].strip())
        
        if candle_close_price > threshold:
            return True, f"Price closed above {threshold}"
    
    return False, None
```

## 💡 实战交易示例

### 场景1：BTC突破入场

```python
# 市场状态
market_data = {
    'current_price': 110000,
    'ema_20': 109500,
    'macd': 150,  # 正值且上升
    'rsi_7': 55,  # 中性
    'rsi_14': 52,
    'ema_20_4h': 108000,
    'ema_50_4h': 107000,  # 4H上升趋势
    'funding_rate': -0.00001,  # 轻微负值
    'atr': 1200
}

# AI决策
decision = {
    'signal': 'entry',
    'side': 'long',  # 做多
    'entry_price': 110000,
    'stop_loss': 108200,  # -1.64% (1.5倍ATR)
    'take_profit': 113700,  # +3.36% (RR=2:1)
    'leverage': 10,
    'confidence': 0.70,
    'invalidation_condition': 'If the price closes below 107500 on a 3-minute candle',
    'justification': 'Breakout above EMA20, MACD bullish, 4H trend up, negative funding'
}

# 仓位计算（账户10000 USDT）
risk_usd = 10000 * 0.02  # 200 USDT风险
risk_per_btc = 110000 - 108200  # 1800 USDT
position_size = 200 / 1800  # 0.111 BTC
required_margin = (0.111 * 110000) / 10  # 1221 USDT

# 执行
# 1. 开仓：买入0.111 BTC @ 110000
# 2. 止损：108200（自动触发）
# 3. 止盈：113700（自动触发）
# 4. 失效：如果3分钟K线收盘价 < 107500，立即平仓
```

### 场景2：ETH超卖反弹

```python
# 市场状态（ETH从高位回调）
market_data = {
    'current_price': 3850,
    'ema_20': 3900,
    'macd': -50,  # 负值但开始收窄
    'rsi_7': 28,  # 超卖
    'rsi_14': 35,
    'ema_20_4h': 3800,
    'ema_50_4h': 3750,  # 4H仍是上升趋势
    'funding_rate': 0.00005,  # 轻微正值
    'atr': 80
}

# AI决策
decision = {
    'signal': 'entry',
    'side': 'long',
    'entry_price': 3850,
    'stop_loss': 3730,  # -3.12% (1.5倍ATR)
    'take_profit': 4030,  # +4.68% (RR=1.5:1)
    'leverage': 12,  # 中高置信度
    'confidence': 0.72,
    'invalidation_condition': 'If the price closes below 3700 on a 3-minute candle',
    'justification': 'RSI oversold bounce, 4H trend intact, MACD divergence'
}
```

### 场景3：持仓管理 - HOLD

```python
# 现有ETH持仓
position = {
    'entry_price': 3850,
    'current_price': 3920,  # +1.82% 未实现盈利
    'stop_loss': 3730,
    'take_profit': 4030,
    'unrealized_pnl': +70 USD
}

# 当前市场状态
current_data = {
    'current_price': 3920,
    'rsi_7': 42,  # 从超卖恢复到中性
    'macd': -20,  # 仍负但收窄
    'ema_20': 3885,  # 价格已回到EMA上方
}

# AI决策
decision = {
    'signal': 'hold',
    'justification': 'Price above EMA20, RSI normalized, trend developing'
}
```

### 场景4：失效条件触发

```python
# ETH持仓
position = {
    'entry_price': 3850,
    'current_price': 3710,  # -3.64% 亏损
    'stop_loss': 3730,  # 已触及
    'invalidation_condition': 'If the price closes below 3700 on a 3-minute candle'
}

# 3分钟K线收盘
candle_close = 3695  # < 3700

# AI决策
decision = {
    'signal': 'close_position',
    'justification': 'Invalidation triggered: price closed below 3700'
}

# 执行立即平仓，不等止损单
```

## 🎓 关键经验总结

从nof1.ai的运行模式中学到的核心原则：

1. **多时间框架分析**：3分钟决策，4小时确认趋势
2. **动态止损**：基于ATR而非固定百分比
3. **风险回报优先**：最小1.5:1，理想2-3:1
4. **失效条件保护**：策略层面的安全阀
5. **资金费率参考**：判断市场情绪和拥挤度
6. **保守杠杆**：5-15倍，绝不过度
7. **严格风控**：单笔2%，这是铁律

这些原则被编码到系统的每个层面，确保AI的决策既有进攻性，又有足够的保护。


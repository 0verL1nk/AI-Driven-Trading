# Tests

测试文件目录 / Test files directory

## 测试文件 / Test Files

### `test_system.py`
系统组件测试 - 测试各个模块是否正确导入和初始化
- 配置加载
- 指标引擎（纯pandas实现）
- Prompt构建器
- 市场数据收集器
- API配置

运行：
```bash
python tests/test_system.py
```

### `test_real_data.py`
真实市场数据测试 - 测试从交易所获取真实数据
- OHLCV K线数据
- 实时价格
- 技术指标计算
- Funding rate（资金费率）
- Open interest（持仓量）
- 多时间周期数据
- 所有交易对测试

运行：
```bash
python tests/test_real_data.py
```

## 运行所有测试 / Run All Tests

```bash
# 系统组件测试
python tests/test_system.py

# 真实数据测试（需要网络连接）
python tests/test_real_data.py
```

## 注意事项 / Notes

1. `test_system.py` - 离线测试，不需要API密钥
2. `test_real_data.py` - 需要网络连接到交易所API
3. 测试数据获取使用的是公开API，不需要API密钥
4. 真实交易需要配置API密钥在 `.env` 文件中


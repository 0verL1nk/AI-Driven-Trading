'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchAccountHistory } from '@/lib/api'
import { format } from 'date-fns'

export default function AccountChart({ account }: { account: any }) {
  const [history, setHistory] = useState<any[]>([])
  const [timeRange, setTimeRange] = useState<'ALL' | '72H' | '24H' | '6H'>('24H')
  const mode = 'fast' // 默认使用快速模式

  useEffect(() => {
    loadHistory()
    
    // Auto-refresh history every 3 seconds for real-time curve updates
    const interval = setInterval(loadHistory, 3000)
    return () => clearInterval(interval)
  }, [timeRange])

  const loadHistory = async () => {
    try {
      let hours: number
      switch (timeRange) {
        case '6H': hours = 6; break
        case '24H': hours = 24; break
        case '72H': hours = 72; break
        case 'ALL': hours = 24 * 30; break // 30 days
        default: hours = 24
      }
      
      const data = await fetchAccountHistory(hours, mode)
      
      const formatted = data.map((d: any) => ({
        time: new Date(d.timestamp).getTime(),
        value: d.total_value,
        label: format(new Date(d.timestamp), 'MMM dd HH:mm'),
      }))
      
      setHistory(formatted)
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const currentValue = account?.total_value || 10000
  const returnPct = account?.total_return || 0

  // 格式化数字，智能省略不必要的小数点
  const formatNumber = (num: number, decimals: number): string => {
    const fixed = num.toFixed(decimals)
    // 如果小数部分全是0，则去掉小数点
    return parseFloat(fixed).toString()
  }

  // 计算数据范围，用于动态格式化
  const getYAxisFormatter = () => {
    if (history.length === 0) {
      return (value: number) => `$${value.toFixed(0)}`
    }
    
    const values = history.map(d => d.value)
    const maxValue = Math.max(...values)
    const minValue = Math.min(...values)
    const range = maxValue - minValue
    
    // 根据数据范围动态选择格式
    return (value: number) => {
      // 如果最大值超过100万，使用M格式
      if (maxValue >= 1000000) {
        return `$${formatNumber(value / 1000000, 1)}M`
      }
      // 如果最大值超过10万，使用k格式（不带小数）
      else if (maxValue >= 100000) {
        return `$${Math.round(value / 1000)}k`
      }
      // 如果最大值超过1万，使用k格式（智能小数）
      else if (maxValue >= 10000) {
        return `$${formatNumber(value / 1000, 1)}k`
      }
      // 如果最大值超过1000，使用k格式（智能小数）
      else if (maxValue >= 1000) {
        return `$${formatNumber(value / 1000, 1)}k`
      }
      // 如果范围较小且数值也小，显示两位小数
      else if (range < 10 && maxValue < 100) {
        return `$${formatNumber(value, 2)}`
      }
      // 如果数值较小，显示整数
      else if (maxValue < 1000) {
        return `$${value.toFixed(0)}`
      }
      // 默认显示整数
      return `$${value.toFixed(0)}`
    }
  }

  return (
    <div>
      {/* Stats */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <div className="text-4xl font-bold">
            ${currentValue.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
          <div className={`text-lg ${returnPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
          </div>
        </div>
        
        {/* Time Range Buttons */}
        <div className="flex space-x-2">
          {(['6H', '24H', '72H', 'ALL'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 text-sm rounded ${
                timeRange === range
                  ? 'bg-white text-black'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-96">
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis 
                dataKey="label" 
                stroke="#666"
                tick={{ fill: '#666', fontSize: 12 }}
              />
              <YAxis 
                stroke="#666"
                tick={{ fill: '#666', fontSize: 12 }}
                domain={['auto', 'auto']}
                tickFormatter={getYAxisFormatter()}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: '4px',
                }}
                labelStyle={{ color: '#fff' }}
                formatter={(value: any) => [
                  `$${parseFloat(value).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}`,
                  'Account Value'
                ]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#00ff00"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            No data available yet. Start trading to see the chart.
          </div>
        )}
      </div>
    </div>
  )
}


'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchAccountHistory } from '@/lib/api'
import { format } from 'date-fns'

export default function AccountChart({ account }: { account: any }) {
  const [history, setHistory] = useState<any[]>([])
  const [timeRange, setTimeRange] = useState<'ALL' | '72H'>('ALL')

  useEffect(() => {
    loadHistory()
  }, [timeRange])

  const loadHistory = async () => {
    try {
      const hours = timeRange === '72H' ? 72 : 24 * 30 // 30 days for ALL
      const data = await fetchAccountHistory(hours)
      
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
          <button
            onClick={() => setTimeRange('ALL')}
            className={`px-4 py-2 text-sm rounded ${
              timeRange === 'ALL'
                ? 'bg-white text-black'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            ALL
          </button>
          <button
            onClick={() => setTimeRange('72H')}
            className={`px-4 py-2 text-sm rounded ${
              timeRange === '72H'
                ? 'bg-white text-black'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            72H
          </button>
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
                domain={['dataMin - 100', 'dataMax + 100']}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: '4px',
                }}
                labelStyle={{ color: '#fff' }}
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


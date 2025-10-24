import { format } from 'date-fns'
import { parseUTCTime } from '@/lib/utils'

export default function TradesList({ trades }: { trades: any[] }) {
  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}M`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}H ${mins}M`
  }

  const formatCoin = (symbol: string) => {
    // Extract coin from symbol like "BTC/USDT:USDT" -> "BTC"
    return symbol.split('/')[0] || symbol
  }

  return (
    <div className="space-y-4">
      {trades && trades.length > 0 ? (
        trades.map((trade, index) => {
          const pnl = trade.pnl || 0
          const pnlPercent = trade.pnl_percent || 0
          const coin = formatCoin(trade.symbol)
          const closeTime = trade.close_timestamp ? format(parseUTCTime(trade.close_timestamp), 'MM/dd, h:mm a') : '-'

          return (
            <div
              key={trade.id || index}
              className="border border-gray-800 rounded p-3 hover:bg-gray-900/50 transition"
            >
              {/* Header */}
              <div className="mb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-white">{coin}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      trade.side === 'long' ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                    }`}>
                      {trade.side?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {closeTime}
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Holding time: {formatDuration(trade.duration_minutes || 0)}
                </div>
              </div>

              {/* Price and Quantity */}
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">Price:</span>
                  <span className="text-white">
                    ${trade.entry_price?.toFixed(4) || 0} → ${trade.exit_price?.toFixed(4) || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Quantity:</span>
                  <span className="text-white">
                    {trade.side === 'short' ? '-' : ''}{trade.quantity?.toFixed(2) || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Notional:</span>
                  <span className="text-white">
                    ${trade.entry_notional?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 0} → 
                    ${trade.exit_notional?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 0}
                  </span>
                </div>
                {trade.leverage && trade.leverage > 1 && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Leverage:</span>
                    <span className="text-white">{trade.leverage}x</span>
                  </div>
                )}
              </div>

              {/* P&L */}
              <div className="mt-2 pt-2 border-t border-gray-800">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Net P&L:</span>
                  <div className="text-right">
                    <div className={`font-bold ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                    </div>
                    <div className={`text-xs ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Reason */}
              {trade.reason && trade.reason !== 'manual_close' && (
                <div className="mt-2 text-xs text-gray-500">
                  Closed by: {trade.reason.replace('_', ' ')}
                </div>
              )}
            </div>
          )
        })
      ) : (
        <div className="text-center text-gray-500 py-8">
          No completed trades yet
        </div>
      )}
    </div>
  )
}


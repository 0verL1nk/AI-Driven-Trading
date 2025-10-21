import { format } from 'date-fns'

export default function PositionsList({ positions }: { positions: any[] }) {
  return (
    <div className="space-y-4">
      {positions && positions.length > 0 ? (
        positions.map((p, index) => {
          const pnl = p.unrealized_pnl || 0
          const pnlPercent = p.entry_price > 0
            ? ((p.current_price - p.entry_price) / p.entry_price) * 100 * (p.side === 'long' ? 1 : -1)
            : 0

          return (
            <div
              key={p.id || index}
              className="border border-gray-800 rounded p-3 hover:bg-gray-900/50 transition"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-white">{p.symbol || 'UNKNOWN'}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    p.side === 'long' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                  }`}>
                    {p.side?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
                <div className={`font-bold ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                </div>
              </div>

              {/* Details */}
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-500">Entry Price:</span>
                  <span className="text-white">${p.entry_price?.toFixed(2) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Current Price:</span>
                  <span className="text-white">${p.current_price?.toFixed(2) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Quantity:</span>
                  <span className="text-white">{p.quantity?.toFixed(4) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Leverage:</span>
                  <span className="text-white">{p.leverage || 1}x</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Return:</span>
                  <span className={pnlPercent >= 0 ? 'text-green-500' : 'text-red-500'}>
                    {pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Opened */}
              {p.timestamp && (
                <div className="mt-2 text-xs text-gray-500 border-t border-gray-800 pt-2">
                  Opened: {format(new Date(p.timestamp), 'MMM dd, HH:mm')}
                </div>
              )}
            </div>
          )
        })
      ) : (
        <div className="text-center text-gray-500 py-8">
          No active positions
        </div>
      )}
    </div>
  )
}


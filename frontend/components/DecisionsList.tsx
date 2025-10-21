import { format } from 'date-fns'

export default function DecisionsList({ decisions }: { decisions: any[] }) {
  const getDecisionColor = (decision: string) => {
    if (decision === 'buy' || decision === 'long') return 'text-green-500'
    if (decision === 'sell' || decision === 'short') return 'text-red-500'
    return 'text-gray-400'
  }

  const getSideLabel = (side: string) => {
    if (!side) return 'HOLD'
    return side.toUpperCase()
  }

  return (
    <div className="space-y-4">
      {decisions && decisions.length > 0 ? (
        decisions.map((d, index) => (
          <div
            key={d.id || index}
            className="border border-gray-800 rounded p-3 hover:bg-gray-900/50 transition"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className={`font-bold ${getDecisionColor(d.decision || d.side)}`}>
                  {d.coin || 'UNKNOWN'}
                </span>
                <span className="text-xs text-gray-500">
                  {getSideLabel(d.side)}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {d.timestamp ? format(new Date(d.timestamp), 'MM/dd HH:mm') : '-'}
              </div>
            </div>

            {/* Details */}
            <div className="text-sm space-y-1">
              {d.entry_price > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Entry:</span>
                  <span className="text-white">${d.entry_price.toFixed(2)}</span>
                </div>
              )}
              {d.stop_loss > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Stop Loss:</span>
                  <span className="text-red-500">${d.stop_loss.toFixed(2)}</span>
                </div>
              )}
              {d.take_profit > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Take Profit:</span>
                  <span className="text-green-500">${d.take_profit.toFixed(2)}</span>
                </div>
              )}
              {d.leverage > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Leverage:</span>
                  <span className="text-white">{d.leverage}x</span>
                </div>
              )}
              {d.confidence > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Confidence:</span>
                  <span className="text-white">{(d.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>

            {/* Reasoning */}
            {d.reasoning && (
              <div className="mt-2 text-xs text-gray-400 border-t border-gray-800 pt-2">
                <span className="text-gray-500">Reason:</span>{' '}
                {d.reasoning.length > 100
                  ? `${d.reasoning.substring(0, 100)}...`
                  : d.reasoning}
              </div>
            )}

            {/* AI Thinking Process (Collapsible) */}
            {d.thinking && d.thinking.trim() !== '' && (
              <details className="mt-2 border-t border-gray-800 pt-2">
                <summary className="text-xs text-blue-400 cursor-pointer hover:text-blue-300 flex items-center gap-1">
                  <span>💭</span>
                  <span>AI Thinking Process</span>
                  <span className="text-gray-600 text-[10px]">
                    ({d.thinking.length} chars)
                  </span>
                </summary>
                <div className="mt-2 text-xs text-gray-300 bg-gray-950/50 rounded p-2 max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {d.thinking}
                </div>
              </details>
            )}
          </div>
        ))
      ) : (
        <div className="text-center text-gray-500 py-8">
          No AI decisions yet
        </div>
      )}
    </div>
  )
}


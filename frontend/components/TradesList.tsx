import { useState, useEffect, useRef, useCallback } from 'react'
import { format } from 'date-fns'
import { parseUTCTime } from '@/lib/utils'
import { fetchTrades } from '@/lib/api'

export default function TradesList() {
  const [trades, setTrades] = useState<any[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const pageSize = 10

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

  const loadTrades = useCallback(async (page: number) => {
    if (loading || !hasMore) return
    
    setLoading(true)
    try {
      const response = await fetchTrades(page, pageSize)
      
      if (response.data && response.data.length > 0) {
        setTrades(prev => page === 1 ? response.data : [...prev, ...response.data])
        setTotal(response.total)
        setTotalPages(response.total_pages)
        setHasMore(page < response.total_pages)
      } else {
        setHasMore(false)
      }
    } catch (error) {
      console.error('Error loading trades:', error)
    } finally {
      setLoading(false)
    }
  }, [loading, hasMore, pageSize])

  // 初始加载
  useEffect(() => {
    loadTrades(1)
  }, [])

  // 无限滚动监听
  useEffect(() => {
    if (loading || !hasMore) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading && hasMore) {
          setCurrentPage(prev => {
            const nextPage = prev + 1
            loadTrades(nextPage)
            return nextPage
          })
        }
      },
      { threshold: 0.1 }
    )

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [loading, hasMore, loadTrades])

  return (
    <div className="space-y-3">
      {/* 统计信息 */}
      {total > 0 && (
        <div className="text-sm text-gray-400 pb-2 border-b border-gray-800">
          Showing {trades.length} of {total} trades
        </div>
      )}

      {/* 交易列表 */}
      {trades.length > 0 ? (
        <>
          {trades.map((trade, index) => {
            const pnl = trade.pnl || 0
            const pnlPercent = trade.pnl_percent || 0
            const coin = formatCoin(trade.symbol)
            const closeTime = trade.close_timestamp ? format(parseUTCTime(trade.close_timestamp), 'MM/dd, h:mm a') : '-'

            return (
              <div
                key={`${trade.id}-${index}`}
                className="border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg font-bold text-white">{coin}</span>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      trade.side === 'long' 
                        ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                        : 'bg-red-500/20 text-red-400 border border-red-500/30'
                    }`}>
                      {trade.side?.toUpperCase()}
                    </span>
                    {trade.leverage && trade.leverage > 1 && (
                      <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
                        {trade.leverage}x
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    {closeTime}
                  </div>
                </div>

                {/* Price Info */}
                <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                  <div>
                    <div className="text-gray-500 text-xs mb-1">Entry Price</div>
                    <div className="text-white font-mono">${trade.entry_price?.toFixed(4) || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs mb-1">Exit Price</div>
                    <div className="text-white font-mono">${trade.exit_price?.toFixed(4) || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs mb-1">Quantity</div>
                    <div className="text-white font-mono">{trade.quantity?.toFixed(4) || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs mb-1">Duration</div>
                    <div className="text-white">{formatDuration(trade.duration_minutes || 0)}</div>
                  </div>
                </div>

                {/* P&L */}
                <div className="pt-3 border-t border-gray-800">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Profit & Loss</span>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                      </div>
                      <div className={`text-xs ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pnl >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Reason */}
                {trade.reason && trade.reason !== 'manual_close' && (
                  <div className="mt-2 text-xs text-gray-500 italic">
                    Exit reason: {trade.reason.replace(/_/g, ' ')}
                  </div>
                )}
              </div>
            )
          })}

          {/* 加载更多触发器 */}
          {hasMore && (
            <div ref={loadMoreRef} className="py-4 text-center">
              {loading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-gray-600 border-t-white rounded-full animate-spin"></div>
                  <span className="text-sm text-gray-400">Loading more trades...</span>
                </div>
              ) : (
                <div className="text-sm text-gray-500">Scroll for more</div>
              )}
            </div>
          )}

          {/* 已加载全部 */}
          {!hasMore && trades.length > 0 && (
            <div className="py-4 text-center text-sm text-gray-500">
              All {total} trades loaded
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-gray-500 py-12 border border-gray-800 rounded-lg">
          <div className="text-4xl mb-2">📊</div>
          <div>No completed trades yet</div>
          <div className="text-xs text-gray-600 mt-1">Trades will appear here once positions are closed</div>
        </div>
      )}
    </div>
  )
}

export default function PriceBar({ prices }: { prices: any[] }) {
  const coinColors: {[key: string]: string} = {
    'BTC': 'bg-orange-500',
    'ETH': 'bg-blue-500',
    'SOL': 'bg-purple-500',
    'BNB': 'bg-yellow-500',
    'DOGE': 'bg-yellow-600',
    'XRP': 'bg-gray-400',
  }

  return (
    <div className="border-b border-gray-800 bg-gray-900/20">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center space-x-8 overflow-x-auto">
          {prices && prices.length > 0 ? (
            prices.map((coin) => {
              const symbol = coin.symbol || 'Unknown'
              const price = coin.price || 0
              const color = coinColors[symbol] || 'bg-gray-500'
              
              return (
                <div key={symbol} className="flex items-center space-x-2 shrink-0">
                  <div className={`w-4 h-4 rounded-full ${color}`} />
                  <span className="font-bold text-sm">{symbol}</span>
                  <span className="text-white text-sm">
                    ${price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}
                  </span>
                </div>
              )
            })
          ) : (
            <div className="text-gray-500 text-sm">Loading prices...</div>
          )}
        </div>
      </div>
    </div>
  )
}


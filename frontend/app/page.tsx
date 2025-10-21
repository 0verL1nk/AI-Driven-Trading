'use client'

import { useState, useEffect } from 'react'
import PriceBar from '@/components/PriceBar'
import AccountChart from '@/components/AccountChart'
import DecisionsList from '@/components/DecisionsList'
import PositionsList from '@/components/PositionsList'
import TradesList from '@/components/TradesList'
import { fetchAccount, fetchPrices, fetchDecisions, fetchPositions, fetchTrades } from '@/lib/api'

export default function Home() {
  const [account, setAccount] = useState<any>(null)
  const [prices, setPrices] = useState<any[]>([])
  const [decisions, setDecisions] = useState<any[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'decisions' | 'positions' | 'trades'>('decisions')

  useEffect(() => {
    // Initial load
    loadData()
    
    // Refresh every 3 seconds for real-time updates
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [accountData, pricesData, decisionsData, positionsData, tradesData] = await Promise.all([
        fetchAccount(),
        fetchPrices(),
        fetchDecisions(),
        fetchPositions(),
        fetchTrades(),
      ])
      
      setAccount(accountData)
      setPrices(pricesData)
      setDecisions(decisionsData)
      setPositions(positionsData)
      setTrades(tradesData)
    } catch (error) {
      console.error('Error loading data:', error)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-gray-800 p-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">
            <span className="text-white">Beta</span>
            <span className="text-gray-500">Lexa</span>
          </h1>
          <div className="flex space-x-6 text-sm">
            <a href="#" className="text-white hover:text-gray-300">LIVE</a>
            <a href="#" className="text-gray-500 hover:text-gray-300">LEADERBOARD</a>
            <a href="#" className="text-gray-500 hover:text-gray-300">MODELS</a>
          </div>
        </div>
      </header>

      {/* Price Bar */}
      <PriceBar prices={prices} />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Chart (2/3) */}
          <div className="lg:col-span-2">
            <div className="bg-gray-900/30 rounded-lg p-6">
              <h2 className="text-xl mb-4">TOTAL ACCOUNT VALUE</h2>
              <AccountChart account={account} />
            </div>
          </div>

          {/* Right: Decisions/Positions (1/3) */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900/30 rounded-lg p-4">
              {/* Tabs */}
              <div className="flex space-x-2 mb-4 border-b border-gray-800">
                <button
                  onClick={() => setActiveTab('decisions')}
                  className={`px-4 py-2 text-sm ${
                    activeTab === 'decisions'
                      ? 'text-white border-b-2 border-white'
                      : 'text-gray-500'
                  }`}
                >
                  DECISIONS
                </button>
                <button
                  onClick={() => setActiveTab('positions')}
                  className={`px-4 py-2 text-sm ${
                    activeTab === 'positions'
                      ? 'text-white border-b-2 border-white'
                      : 'text-gray-500'
                  }`}
                >
                  POSITIONS
                </button>
                <button
                  onClick={() => setActiveTab('trades')}
                  className={`px-4 py-2 text-sm ${
                    activeTab === 'trades'
                      ? 'text-white border-b-2 border-white'
                      : 'text-gray-500'
                  }`}
                >
                  TRADES
                </button>
              </div>

              {/* Content */}
              <div className="h-[600px] overflow-y-auto">
                {activeTab === 'decisions' ? (
                  <DecisionsList decisions={decisions} />
                ) : activeTab === 'positions' ? (
                  <PositionsList positions={positions} />
                ) : (
                  <TradesList trades={trades} />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


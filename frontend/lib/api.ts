// 使用相对路径，通过 Next.js rewrites 代理到后端
// 在 next.config.js 中配置了 /api/* 会转发到 NEXT_PUBLIC_API_URL
const API_BASE = ''  // 空字符串表示使用相对路径

export async function fetchAccount() {
  const res = await fetch(`${API_BASE}/api/account`)
  if (!res.ok) throw new Error('Failed to fetch account')
  return res.json()
}

export async function fetchPrices() {
  const res = await fetch(`${API_BASE}/api/prices`)
  if (!res.ok) throw new Error('Failed to fetch prices')
  return res.json()
}

export async function fetchDecisions(limit: number = 20) {
  const res = await fetch(`${API_BASE}/api/decisions?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch decisions')
  return res.json()
}

export async function fetchPositions() {
  const res = await fetch(`${API_BASE}/api/positions`)
  if (!res.ok) throw new Error('Failed to fetch positions')
  return res.json()
}

export async function fetchAccountHistory(hours: number = 24, mode: string = 'auto', since?: string) {
  let url = `${API_BASE}/api/account_history?hours=${hours}&mode=${mode}`
  if (since) {
    url += `&since=${encodeURIComponent(since)}`
  }
  
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch account history')
  const response = await res.json()
  
  // 兼容旧格式：如果返回的是数组，直接返回；如果是对象，返回data字段
  if (Array.isArray(response)) {
    return response
  }
  return response.data || []
}

export async function fetchPriceHistory(symbol: string, hours: number = 24) {
  const res = await fetch(`${API_BASE}/api/price_history/${symbol}?hours=${hours}`)
  if (!res.ok) throw new Error('Failed to fetch price history')
  return res.json()
}

export async function fetchTrades(page: number = 1, pageSize: number = 10) {
  const res = await fetch(`${API_BASE}/api/trades?page=${page}&page_size=${pageSize}`)
  if (!res.ok) throw new Error('Failed to fetch trades')
  return res.json()
}


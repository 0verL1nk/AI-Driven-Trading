/**
 * 时间处理工具函数
 */

/**
 * 将UTC时间转换为本地时间（UTC+8）
 * 后端SQLite返回的是UTC时间，需要手动转换为中国时区
 */
export const parseUTCTime = (timestamp: string | null | undefined): Date => {
  if (!timestamp) {
    return new Date()
  }
  
  // 解析UTC时间
  const utcDate = new Date(timestamp)
  
  // 加8小时转换为中国时区 (UTC+8)
  const localDate = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000)
  
  return localDate
}

/**
 * 格式化数字，智能省略不必要的小数点
 */
export const formatNumber = (num: number, decimals: number): string => {
  const fixed = num.toFixed(decimals)
  // 如果小数部分全是0，则去掉小数点
  return parseFloat(fixed).toString()
}


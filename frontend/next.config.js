/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // 使用环境变量配置API地址
    // 开发环境: NEXT_PUBLIC_API_URL=http://localhost:8000
    // 生产环境: NEXT_PUBLIC_API_URL=http://trade.overlink.top
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;


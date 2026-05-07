export function isH5(): boolean {
  return uni.getSystemInfoSync().uniPlatform === 'web' || typeof window !== 'undefined'
}

export function isWeixinMP(): boolean {
  // #ifdef MP-WEIXIN
  return true
  // #endif
  // #ifndef MP-WEIXIN
  return false
  // #endif
}

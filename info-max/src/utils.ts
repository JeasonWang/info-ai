import type { InfoItem } from '@/types'

interface TextSegment {
  kind: 'text' | 'link' | 'hashtag'
  text: string
}

type RichBlock =
  | { type: 'heading'; text: string }
  | { type: 'quote'; text: string }
  | { type: 'code'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'paragraph'; segments: TextSegment[] }

export function formatDateTime(value: string | null) {
  if (!value) return '暂无时间'
  return value.replace('T', ' ')
}

export function getContentMode(content: string) {
  const trimmed = content.trim()
  if (!trimmed) return 'plain'
  if (/<[a-z][\s\S]*>/i.test(trimmed)) return 'html'
  if (/^#{1,6}\s/m.test(trimmed) || /```[\s\S]*```/.test(trimmed)) return 'markdown'
  return 'plain'
}

export function getMediaUrls(info: InfoItem) {
  const imageMatches = info.content.match(/https?:\/\/\S+\.(png|jpg|jpeg|gif|webp)/gi) ?? []
  const videoMatches = info.content.match(/https?:\/\/\S+\.(mp4|webm|mov)/gi) ?? []
  return {
    images: Array.from(new Set(imageMatches)),
    videos: Array.from(new Set(videoMatches)),
  }
}

export function getStatusTone(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

export function summarize(content: string, length = 140) {
  if (content.length <= length) return content
  return `${content.slice(0, length)}...`
}

function decodeHtml(input: string) {
  return input
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

function stripHtml(html: string) {
  return decodeHtml(
    html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|div|li|h[1-6]|blockquote)>/gi, '\n')
      .replace(/<[^>]+>/g, ''),
  )
}

function tokenizeInline(text: string): TextSegment[] {
  const segments: TextSegment[] = []
  const matcher = /(https?:\/\/[^\s]+|#[^#\s]+(?:\[[^\]]+\])?#?)/g
  let cursor = 0

  for (const match of text.matchAll(matcher)) {
    const token = match[0]
    const index = match.index ?? 0
    if (index > cursor) {
      segments.push({ kind: 'text', text: text.slice(cursor, index) })
    }
    segments.push({
      kind: token.startsWith('http') ? 'link' : 'hashtag',
      text: token,
    })
    cursor = index + token.length
  }

  if (cursor < text.length) {
    segments.push({ kind: 'text', text: text.slice(cursor) })
  }

  return segments.length ? segments : [{ kind: 'text', text }]
}

export function formatRichContent(content: string): RichBlock[] {
  const source = getContentMode(content) === 'html' ? stripHtml(content) : content
  const normalized = source.replace(/\r\n/g, '\n').trim()

  if (!normalized) {
    return [{ type: 'paragraph', segments: [{ kind: 'text', text: '暂无正文内容' }] }]
  }

  const lines = normalized.split('\n')
  const blocks: RichBlock[] = []
  const listBuffer: string[] = []
  const codeBuffer: string[] = []
  let inCode = false

  const flushList = () => {
    if (listBuffer.length) {
      blocks.push({ type: 'list', items: [...listBuffer] })
      listBuffer.length = 0
    }
  }

  const flushCode = () => {
    if (codeBuffer.length) {
      blocks.push({ type: 'code', text: codeBuffer.join('\n') })
      codeBuffer.length = 0
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()

    if (line.startsWith('```')) {
      if (inCode) {
        flushCode()
        inCode = false
      } else {
        flushList()
        inCode = true
      }
      continue
    }

    if (inCode) {
      codeBuffer.push(rawLine)
      continue
    }

    if (!line || line === '-' || line === '—') {
      flushList()
      continue
    }

    const headingMatch = line.match(/^#{1,6}\s+(.+)$/)
    if (headingMatch) {
      flushList()
      blocks.push({ type: 'heading', text: headingMatch[1] })
      continue
    }

    if (line.startsWith('>')) {
      flushList()
      blocks.push({ type: 'quote', text: line.replace(/^>\s?/, '') })
      continue
    }

    const listMatch = line.match(/^[-*•]\s+(.+)$/)
    if (listMatch) {
      listBuffer.push(listMatch[1])
      continue
    }

    flushList()
    blocks.push({ type: 'paragraph', segments: tokenizeInline(line) })
  }

  flushList()
  flushCode()

  return blocks
}

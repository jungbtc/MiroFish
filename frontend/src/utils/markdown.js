const HTML_ENTITIES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}

const ALLOWED_URL_SCHEMES = new Set(['http', 'https', 'mailto'])

const HEADING_PATTERN = /^(#{1,4})[ \t]+(.+?)\s*$/
const UNORDERED_LIST_PATTERN = /^(\s*)[-+*][ \t]+(.+)$/
const ORDERED_LIST_PATTERN = /^(\s*)(\d+)\.[ \t]+(.+)$/

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => HTML_ENTITIES[character])
}

function decodeSchemeEntities(value) {
  return value
    .replace(/&#(x[\da-f]+|\d+);?/gi, (match, entity) => {
      const radix = entity[0].toLowerCase() === 'x' ? 16 : 10
      const digits = radix === 16 ? entity.slice(1) : entity
      const codePoint = Number.parseInt(digits, radix)

      if (!Number.isFinite(codePoint) || codePoint > 0x10ffff) return match

      try {
        return String.fromCodePoint(codePoint)
      } catch {
        return match
      }
    })
    .replace(/&colon;?/gi, ':')
    .replace(/&tab;?/gi, '\t')
    .replace(/&newline;?/gi, '\n')
}

/**
 * Returns a safe Markdown link destination, or null when its scheme is unsafe.
 * Relative URLs are supported, but protocol-relative URLs are deliberately
 * rejected so every external link has an explicit, allow-listed scheme.
 */
export function sanitizeMarkdownUrl(value) {
  if (typeof value !== 'string') return null

  const url = value.trim()
  if (!url || /[\u0000-\u001f\u007f]/.test(url)) return null
  if (/^[\\/]{2}/.test(url)) return null

  // Browsers normalize character references and some whitespace while
  // interpreting schemes. Normalize those characters for validation too.
  const normalized = decodeSchemeEntities(url).replace(/[\u0000-\u0020\u007f]/g, '')
  const schemeMatch = normalized.match(/^([a-z][a-z\d+.-]*):/i)

  if (schemeMatch) {
    return ALLOWED_URL_SCHEMES.has(schemeMatch[1].toLowerCase()) ? url : null
  }

  // A colon before the first path/query/fragment separator is an unknown
  // scheme, even when it uses characters outside the standard scheme regex.
  const colonIndex = normalized.indexOf(':')
  const separatorIndex = normalized.search(/[/?#]/)
  if (colonIndex >= 0 && (separatorIndex < 0 || colonIndex < separatorIndex)) {
    return null
  }

  return url
}

function renderStyledText(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_\n]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
    .replace(/_([^_\n]+)_/g, '<em>$1</em>')
}

function findLinkEnd(value, startIndex) {
  let nestedParentheses = 0
  let quote = null

  for (let index = startIndex; index < value.length; index += 1) {
    const character = value[index]

    if (character === '\\') {
      index += 1
      continue
    }

    if (quote) {
      if (character === quote) quote = null
      continue
    }

    if (character === '"' || character === "'") {
      quote = character
    } else if (character === '(') {
      nestedParentheses += 1
    } else if (character === ')') {
      if (nestedParentheses === 0) return index
      nestedParentheses -= 1
    }
  }

  return -1
}

function parseLinkDestination(value) {
  let destination = value.trim()

  if (destination.startsWith('<') && destination.endsWith('>')) {
    destination = destination.slice(1, -1).trim()
  } else {
    const destinationMatch = destination.match(
      /^(\S+?)(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?$/
    )
    if (!destinationMatch) return null
    destination = destinationMatch[1]
  }

  return destination.replace(/\\([\\()])/g, '$1')
}

function renderInline(value, allowLinks = true) {
  const source = String(value)
  const rendered = []
  let plainText = ''

  const flushPlainText = () => {
    if (!plainText) return
    rendered.push(renderStyledText(plainText))
    plainText = ''
  }

  for (let index = 0; index < source.length; index += 1) {
    if (source[index] === '`') {
      const codeEnd = source.indexOf('`', index + 1)
      if (codeEnd >= 0) {
        flushPlainText()
        rendered.push(
          `<code class="inline-code">${escapeHtml(source.slice(index + 1, codeEnd))}</code>`
        )
        index = codeEnd
        continue
      }
    }

    if (allowLinks && source[index] === '[') {
      const labelEnd = source.indexOf('](', index + 1)
      if (labelEnd >= 0) {
        const destinationEnd = findLinkEnd(source, labelEnd + 2)
        if (destinationEnd >= 0) {
          flushPlainText()

          const label = source.slice(index + 1, labelEnd)
          const destination = parseLinkDestination(
            source.slice(labelEnd + 2, destinationEnd)
          )
          const safeUrl = destination && sanitizeMarkdownUrl(destination)

          if (safeUrl) {
            const externalAttributes = /^https?:/i.test(safeUrl)
              ? ' target="_blank" rel="noopener noreferrer"'
              : ''
            rendered.push(
              `<a class="md-link" href="${escapeHtml(safeUrl)}"${externalAttributes}>${renderInline(label, false)}</a>`
            )
          } else {
            // Keep the useful label visible without creating a dangerous link.
            rendered.push(renderInline(label, false))
          }

          index = destinationEnd
          continue
        }
      }
    }

    plainText += source[index]
  }

  flushPlainText()
  return rendered.join('')
}

function hasTablePipe(value) {
  let inCode = false

  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === '\\') {
      index += 1
      continue
    }
    if (value[index] === '`') inCode = !inCode
    if (value[index] === '|' && !inCode) return true
  }

  return false
}

function splitTableRow(value) {
  let source = value.trim()
  if (source.startsWith('|')) source = source.slice(1)
  if (source.endsWith('|') && !source.endsWith('\\|')) source = source.slice(0, -1)

  const cells = []
  let cell = ''
  let inCode = false

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]

    if (character === '\\' && source[index + 1] === '|') {
      cell += '|'
      index += 1
      continue
    }

    if (character === '`') inCode = !inCode

    if (character === '|' && !inCode) {
      cells.push(cell.trim())
      cell = ''
    } else {
      cell += character
    }
  }

  cells.push(cell.trim())
  return cells
}

function getTableDefinition(lines, index) {
  if (index + 1 >= lines.length || !hasTablePipe(lines[index])) return null

  const headers = splitTableRow(lines[index])
  const delimiters = splitTableRow(lines[index + 1])
  if (
    headers.length !== delimiters.length ||
    delimiters.length === 0 ||
    !delimiters.every(cell => /^:?-{3,}:?$/.test(cell))
  ) {
    return null
  }

  const alignments = delimiters.map(cell => {
    if (cell.startsWith(':') && cell.endsWith(':')) return 'center'
    if (cell.endsWith(':')) return 'right'
    if (cell.startsWith(':')) return 'left'
    return null
  })

  const rows = []
  let nextIndex = index + 2

  while (
    nextIndex < lines.length &&
    lines[nextIndex].trim() &&
    hasTablePipe(lines[nextIndex])
  ) {
    const row = splitTableRow(lines[nextIndex]).slice(0, headers.length)
    while (row.length < headers.length) row.push('')
    rows.push(row)
    nextIndex += 1
  }

  return { headers, alignments, rows, nextIndex }
}

function tableCellClass(alignment) {
  return alignment ? ` class="md-align-${alignment}"` : ''
}

function renderTable(table) {
  const header = table.headers
    .map((cell, index) => `<th${tableCellClass(table.alignments[index])}>${renderInline(cell)}</th>`)
    .join('')
  const body = table.rows
    .map(row => `<tr>${row.map((cell, index) => `<td${tableCellClass(table.alignments[index])}>${renderInline(cell)}</td>`).join('')}</tr>`)
    .join('')
  const tableBody = body ? `<tbody>${body}</tbody>` : ''

  return `<div class="md-table-wrapper"><table class="md-table"><thead><tr>${header}</tr></thead>${tableBody}</table></div>`
}

function isBlockStart(lines, index) {
  const line = lines[index]
  if (line == null || !line.trim()) return true
  if (/^\s*```/.test(line)) return true
  if (HEADING_PATTERN.test(line)) return true
  if (/^\s*>[ \t]?/.test(line)) return true
  if (UNORDERED_LIST_PATTERN.test(line) || ORDERED_LIST_PATTERN.test(line)) return true
  if (/^\s*---\s*$/.test(line)) return true
  return Boolean(getTableDefinition(lines, index))
}

/**
 * Render the limited Markdown used by report and interaction views.
 *
 * Raw HTML is always escaped. Every HTML tag in the returned string is
 * generated here, which makes the result safe to use with Vue's v-html.
 */
export function renderMarkdown(content) {
  if (content == null || content === '') return ''

  let source = String(content).replace(/\r\n?/g, '\n')
  // Section titles are already rendered by both consuming components.
  source = source.replace(/^##[ \t]+[^\n]+\n+/, '')

  const lines = source.split('\n')
  const blocks = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]

    if (!line.trim()) {
      index += 1
      continue
    }

    if (/^\s*```/.test(line)) {
      const codeLines = []
      index += 1
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        codeLines.push(lines[index])
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push(`<pre class="code-block"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
      continue
    }

    const table = getTableDefinition(lines, index)
    if (table) {
      blocks.push(renderTable(table))
      index = table.nextIndex
      continue
    }

    const heading = line.match(HEADING_PATTERN)
    if (heading) {
      const level = heading[1].length + 1
      blocks.push(`<h${level} class="md-h${level}">${renderInline(heading[2])}</h${level}>`)
      index += 1
      continue
    }

    if (/^\s*---\s*$/.test(line)) {
      blocks.push('<hr class="md-hr">')
      index += 1
      continue
    }

    if (/^\s*>[ \t]?/.test(line)) {
      const quoteLines = []
      while (index < lines.length) {
        const quote = lines[index].match(/^\s*>[ \t]?(.*)$/)
        if (!quote) break
        quoteLines.push(renderInline(quote[1]))
        index += 1
      }
      blocks.push(`<blockquote class="md-quote">${quoteLines.join('<br>')}</blockquote>`)
      continue
    }

    const unorderedItem = line.match(UNORDERED_LIST_PATTERN)
    const orderedItem = line.match(ORDERED_LIST_PATTERN)
    if (unorderedItem || orderedItem) {
      const ordered = Boolean(orderedItem)
      const pattern = ordered ? ORDERED_LIST_PATTERN : UNORDERED_LIST_PATTERN
      const tag = ordered ? 'ol' : 'ul'
      const listClass = ordered ? 'md-ol' : 'md-ul'
      const itemClass = ordered ? 'md-oli' : 'md-li'
      const items = []
      let firstNumber = 1

      while (index < lines.length) {
        const item = lines[index].match(pattern)
        if (!item) break

        const indentation = item[1].replace(/\t/g, '  ').length
        const textIndex = ordered ? 3 : 2
        if (ordered && items.length === 0) firstNumber = Number.parseInt(item[2], 10)
        items.push(
          `<li class="${itemClass}" data-level="${Math.floor(indentation / 2)}">${renderInline(item[textIndex])}</li>`
        )
        index += 1
      }

      const startAttribute = ordered && firstNumber !== 1 ? ` start="${firstNumber}"` : ''
      blocks.push(`<${tag} class="${listClass}"${startAttribute}>${items.join('')}</${tag}>`)
      continue
    }

    const paragraphLines = []
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) {
      paragraphLines.push(renderInline(lines[index]))
      index += 1
    }
    blocks.push(`<p class="md-p">${paragraphLines.join('<br>')}</p>`)
  }

  return blocks.join('')
}

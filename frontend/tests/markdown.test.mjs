import assert from 'node:assert/strict'
import test from 'node:test'

import {
  escapeHtml,
  renderMarkdown,
  sanitizeMarkdownUrl
} from '../src/utils/markdown.js'

test('escapes raw HTML in regular text and code blocks', () => {
  const html = renderMarkdown([
    '<img src=x onerror="alert(1)">',
    '',
    '```html',
    '<script>alert(1)</script>',
    '```'
  ].join('\n'))

  assert.doesNotMatch(html, /<img\b/i)
  assert.doesNotMatch(html, /<script\b/i)
  assert.match(html, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/)
  assert.match(html, /<pre class="code-block"><code>&lt;script&gt;alert\(1\)&lt;\/script&gt;<\/code><\/pre>/)
})

test('renders the supported report Markdown features', () => {
  const html = renderMarkdown([
    '# Heading',
    '',
    '**Bold** and *emphasis* with `inline code`.',
    '',
    '- first',
    '  - nested',
    '',
    '3. third',
    '4. fourth',
    '',
    '> quoted [source](https://example.com/report)',
    '',
    '| Name | Score |',
    '| :--- | ---: |',
    '| Alice | 10 |'
  ].join('\n'))

  assert.match(html, /<h2 class="md-h2">Heading<\/h2>/)
  assert.match(html, /<strong>Bold<\/strong>/)
  assert.match(html, /<em>emphasis<\/em>/)
  assert.match(html, /<code class="inline-code">inline code<\/code>/)
  assert.match(html, /<ul class="md-ul"><li class="md-li" data-level="0">first<\/li><li class="md-li" data-level="1">nested<\/li><\/ul>/)
  assert.match(html, /<ol class="md-ol" start="3">/)
  assert.match(html, /<blockquote class="md-quote">quoted <a class="md-link" href="https:\/\/example\.com\/report" target="_blank" rel="noopener noreferrer">source<\/a><\/blockquote>/)
  assert.match(html, /<table class="md-table">/)
  assert.match(html, /<th class="md-align-left">Name<\/th>/)
  assert.match(html, /<th class="md-align-right">Score<\/th>/)
  assert.match(html, /<td class="md-align-right">10<\/td>/)
})

test('removes the duplicated leading section heading', () => {
  const html = renderMarkdown('## Outer section title\n\n# Inner heading')

  assert.doesNotMatch(html, /Outer section title/)
  assert.equal(html, '<h2 class="md-h2">Inner heading</h2>')
})

test('allows only explicit safe URL schemes and safe relative links', () => {
  assert.equal(sanitizeMarkdownUrl('https://example.com'), 'https://example.com')
  assert.equal(sanitizeMarkdownUrl('mailto:team@example.com'), 'mailto:team@example.com')
  assert.equal(sanitizeMarkdownUrl('../reports/1'), '../reports/1')
  assert.equal(sanitizeMarkdownUrl('#summary'), '#summary')

  assert.equal(sanitizeMarkdownUrl('javascript:alert(1)'), null)
  assert.equal(sanitizeMarkdownUrl('data:text/html,attack'), null)
  assert.equal(sanitizeMarkdownUrl('vbscript:attack'), null)
  assert.equal(sanitizeMarkdownUrl('//example.com'), null)
  assert.equal(sanitizeMarkdownUrl('jav&#x61;script:alert(1)'), null)
  assert.equal(sanitizeMarkdownUrl('java\tscript:alert(1)'), null)
})

test('keeps unsafe link labels visible without emitting anchors', () => {
  const html = renderMarkdown([
    '[JavaScript](javascript:alert(1))',
    '[Data](data:text/html,attack)',
    '[Encoded](jav&#x61;script:alert(1))',
    '[Web](https://example.com)',
    '[Email](mailto:team@example.com)',
    '[Local](../reports/1)'
  ].join('\n'))

  assert.match(html, /JavaScript/)
  assert.match(html, /Data/)
  assert.match(html, /Encoded/)
  assert.doesNotMatch(html, /href="(?:javascript|data|vbscript):/i)
  assert.equal((html.match(/<a\b/g) || []).length, 3)
})

test('escapeHtml covers characters that can break text or attributes', () => {
  assert.equal(
    escapeHtml('&<>"\''),
    '&amp;&lt;&gt;&quot;&#39;'
  )
})

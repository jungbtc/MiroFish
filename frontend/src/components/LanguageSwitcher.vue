<template>
  <div v-if="availableLocales.length > 1" class="language-switcher" ref="switcherRef" @keydown.esc="open = false">
    <button
      class="switcher-trigger"
      type="button"
      aria-label="Change language"
      aria-haspopup="menu"
      :aria-expanded="open"
      aria-controls="forefold-language-menu"
      @click="toggleDropdown"
    >
      {{ currentLabel }}
      <span class="caret" aria-hidden="true">{{ open ? '⌃' : '⌄' }}</span>
    </button>
    <ul v-if="open" id="forefold-language-menu" class="switcher-dropdown" role="menu">
      <li
        v-for="loc in availableLocales"
        :key="loc.key"
        role="none"
      >
        <button
          type="button"
          role="menuitemradio"
          class="switcher-option"
          :class="{ active: loc.key === locale }"
          :aria-checked="loc.key === locale"
          @click="switchLocale(loc.key)"
        >
          <span>{{ loc.label }}</span>
          <span v-if="loc.key === locale" aria-hidden="true">✓</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '@/i18n/index.js'

const { locale } = useI18n({ useScope: 'global' })
const open = ref(false)
const switcherRef = ref(null)

const currentLabel = computed(() => {
  const found = availableLocales.find(l => l.key === locale.value)
  return found ? found.label : locale.value
})

const toggleDropdown = () => {
  open.value = !open.value
}

const switchLocale = (key) => {
  locale.value = key
  localStorage.setItem('locale', key)
  document.documentElement.lang = key
  open.value = false
}

const onClickOutside = (e) => {
  if (switcherRef.value && !switcherRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.documentElement.lang = locale.value
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.language-switcher {
  position: relative;
  display: inline-block;
  font-family: var(--mf-font, system-ui, sans-serif);
}

.switcher-trigger {
  min-height: 36px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: 999px;
  color: var(--mf-secondary, #6e6e73);
  background: rgba(118, 118, 128, 0.09);
  font: 600 11px/1 var(--mf-font, system-ui, sans-serif);
  cursor: pointer;
  transition: color 160ms ease, background 160ms ease;
}

.switcher-trigger:hover {
  color: var(--mf-ink, #1d1d1f);
  background: rgba(118, 118, 128, 0.15);
}

.caret {
  color: var(--mf-tertiary, #86868b);
  font-size: 10px;
}

.switcher-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: max-content;
  min-width: 150px;
  padding: 6px;
  list-style: none;
  border: 1px solid rgba(29, 29, 31, 0.10);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.14);
  backdrop-filter: blur(22px);
  z-index: 1000;
}

.switcher-option {
  width: 100%;
  min-height: 36px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border: 0;
  border-radius: 8px;
  color: var(--mf-ink, #1d1d1f);
  background: transparent;
  font-size: 12px;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
  transition: background 140ms ease;
}

.switcher-option:hover {
  background: rgba(118, 118, 128, 0.10);
}

.switcher-option.active {
  color: var(--mf-blue, #0071e3);
  font-weight: 650;
}


</style>

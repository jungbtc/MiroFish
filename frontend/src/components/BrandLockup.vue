<template>
  <RouterLink
    class="brand-lockup"
    :class="{ dark: theme === 'dark' }"
    to="/"
    aria-label="Go to FOREFOLD home"
  >
    <span class="brand-icon-frame" aria-hidden="true">
      <img :src="BRAND_ICON_PATH" alt="" />
    </span>
    <span class="brand-name">{{ BRAND_NAME }}</span>
    <span v-if="suffix" class="brand-suffix">{{ suffix }}</span>
  </RouterLink>
</template>

<script setup>
import { BRAND_ICON_PATH, BRAND_NAME } from '../constants/brand'

defineProps({
  suffix: { type: String, default: '' },
  theme: { type: String, default: 'light' }
})
</script>

<style scoped>
.brand-lockup {
  --brand-icon-size: 36px;
  --brand-name-size: 14px;
  min-height: 44px;
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #1d1d1f;
  text-decoration: none;
}

.brand-lockup.dark { color: #fff; }

.brand-icon-frame {
  width: var(--brand-icon-size);
  height: var(--brand-icon-size);
  flex: 0 0 var(--brand-icon-size);
  overflow: hidden;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: calc(var(--brand-icon-size) * 0.28);
  background: #f7f9ff;
  box-shadow: 0 5px 16px rgba(45, 74, 120, 0.16);
}

.brand-icon-frame img {
  width: 128%;
  max-width: none;
  height: 128%;
  object-fit: cover;
}

.brand-name {
  font-size: var(--brand-name-size);
  font-weight: 760;
  letter-spacing: 0.055em;
  white-space: nowrap;
}

.brand-suffix {
  padding-left: 10px;
  border-left: 1px solid currentColor;
  color: color-mix(in srgb, currentColor 62%, transparent);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.09em;
  white-space: nowrap;
}
</style>

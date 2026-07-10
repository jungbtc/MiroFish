<template>
  <section class="model-settings" aria-labelledby="model-settings-title">
    <div class="settings-header">
      <div>
        <span class="settings-kicker">{{ $t('home.modelSettingsKicker') }}</span>
        <h3 id="model-settings-title">{{ $t('home.modelSettingsTitle') }}</h3>
      </div>
      <span class="required-badge">{{ $t('home.requiredSelection') }}</span>
    </div>

    <div class="setting-group">
      <span class="setting-label">{{ $t('home.modelLabel') }}</span>
      <div class="model-options">
        <button
          v-for="option in modelOptions"
          :key="option.id"
          type="button"
          class="model-option"
          :class="{ selected: model === option.id }"
          :aria-pressed="model === option.id"
          @click="$emit('update:model', option.id)"
        >
          <span class="model-option-head">
            <strong>{{ option.name }}</strong>
            <span v-if="option.recommended" class="recommended-badge">
              {{ $t('home.recommended') }}
            </span>
          </span>
          <span>{{ $t(option.descriptionKey) }}</span>
        </button>
      </div>
    </div>

    <div class="setting-group">
      <span class="setting-label">{{ $t('home.reasoningLabel') }}</span>
      <div class="effort-options">
        <button
          v-for="option in effortOptions"
          :key="option.id"
          type="button"
          class="effort-option"
          :class="{ selected: reasoningEffort === option.id }"
          :aria-pressed="reasoningEffort === option.id"
          @click="$emit('update:reasoningEffort', option.id)"
        >
          <span>{{ $t(option.labelKey) }}</span>
          <small v-if="option.recommended">{{ $t('home.recommended') }}</small>
        </button>
      </div>
      <p class="reasoning-help">{{ $t('home.reasoningHelp') }}</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  model: {
    type: String,
    required: true
  },
  reasoningEffort: {
    type: String,
    required: true
  }
})

defineEmits(['update:model', 'update:reasoningEffort'])

const modelOptions = [
  {
    id: 'gpt-5.4-mini',
    name: 'GPT-5.4 mini',
    descriptionKey: 'home.modelMiniDesc',
    recommended: true
  },
  {
    id: 'gpt-5.4-nano',
    name: 'GPT-5.4 nano',
    descriptionKey: 'home.modelNanoDesc',
    recommended: false
  }
]

const effortOptions = [
  { id: 'none', labelKey: 'home.effortNone' },
  { id: 'low', labelKey: 'home.effortLow', recommended: true },
  { id: 'medium', labelKey: 'home.effortMedium' },
  { id: 'high', labelKey: 'home.effortHigh' },
  { id: 'xhigh', labelKey: 'home.effortXHigh' }
]
</script>

<style scoped>
.model-settings {
  border: 1px solid #dedede;
  background: #fafafa;
  padding: 18px;
}

.settings-header,
.model-option-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.settings-kicker,
.setting-label,
.required-badge,
.recommended-badge,
.effort-option small {
  font-family: var(--font-mono, monospace);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.settings-kicker {
  display: block;
  margin-bottom: 4px;
  color: #777;
  font-size: 10px;
}

h3 {
  margin: 0;
  font-size: 16px;
}

.required-badge,
.recommended-badge {
  font-size: 9px;
  padding: 3px 6px;
  border: 1px solid #ff4500;
  color: #ff4500;
}

.setting-group {
  margin-top: 16px;
}

.setting-label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-size: 10px;
}

.model-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.model-option,
.effort-option {
  border: 1px solid #d8d8d8;
  background: #fff;
  color: #222;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.model-option {
  padding: 12px;
  text-align: left;
}

.model-option > span:last-child {
  display: block;
  margin-top: 7px;
  color: #666;
  font-size: 11px;
  line-height: 1.45;
}

.model-option.selected,
.effort-option.selected {
  border-color: #ff4500;
  background: #fff7f3;
}

.effort-options {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}

.effort-option {
  min-height: 48px;
  padding: 8px 4px;
  font-size: 11px;
}

.effort-option span,
.effort-option small {
  display: block;
}

.effort-option small {
  margin-top: 3px;
  color: #ff4500;
  font-size: 7px;
}

.reasoning-help {
  margin: 9px 0 0;
  color: #777;
  font-size: 10px;
  line-height: 1.5;
}

@media (max-width: 720px) {
  .model-options {
    grid-template-columns: 1fr;
  }

  .effort-options {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>

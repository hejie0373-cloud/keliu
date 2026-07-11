<script setup lang="ts">
defineProps<{
  modelValue: string
  options: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

function choose(value: string) {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<template>
  <div class="auth-tabs" role="tablist" aria-label="认证方式" :style="{ '--tab-count': options.length }">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="tab"
      :aria-selected="modelValue === option.value"
      :class="{ active: modelValue === option.value }"
      @click="choose(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.auth-tabs {
  display: grid;
  grid-template-columns: repeat(var(--tab-count), minmax(0, 1fr));
  gap: 6px;
  padding: 5px;
  margin: 20px 0 24px;
  border: 1px solid rgba(120, 153, 173, 0.24);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.64), rgba(231, 242, 246, 0.72)),
    rgba(234, 243, 247, 0.86);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82), 0 10px 24px rgba(33, 63, 92, 0.08);
}

button {
  min-height: 42px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #5c6877;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 720;
  cursor: pointer;
  transform: translateZ(0);
  transition: color 180ms ease, background 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

button:hover {
  color: #0d7188;
  transform: translateY(-1px);
}

button.active {
  background: linear-gradient(180deg, #ffffff 0%, #f7fbfc 100%);
  color: #0b718a;
  box-shadow: 0 10px 22px rgba(29, 61, 89, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

button:focus-visible {
  outline: 3px solid rgba(15, 111, 136, 0.2);
  outline-offset: 2px;
}

@media (max-width: 380px) {
  .auth-tabs {
    gap: 4px;
  }

  button {
    font-size: 0.8rem;
  }
}
</style>

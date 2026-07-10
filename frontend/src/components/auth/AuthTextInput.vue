<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: string
    label: string
    type?: string
    placeholder?: string
    autocomplete?: string
    maxlength?: number
    inputmode?: 'none' | 'text' | 'tel' | 'url' | 'email' | 'numeric' | 'decimal' | 'search'
  }>(),
  {
    type: 'text',
    placeholder: '',
    autocomplete: undefined,
    maxlength: undefined,
    inputmode: 'text',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  enter: []
}>()
</script>

<template>
  <label class="auth-field">
    <span class="auth-label">{{ label }}</span>
    <span class="auth-control">
      <span v-if="$slots.prefix" class="auth-prefix">
        <slot name="prefix" />
      </span>
      <input
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :maxlength="maxlength"
        :inputmode="inputmode"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @keyup.enter="emit('enter')"
      >
      <span v-if="$slots.action" class="auth-action">
        <slot name="action" />
      </span>
    </span>
  </label>
</template>

<style scoped>
.auth-field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.auth-label {
  color: #263344;
  font-size: 0.84rem;
  font-weight: 720;
}

.auth-control {
  min-height: 52px;
  display: flex;
  align-items: stretch;
  overflow: hidden;
  border: 1px solid rgba(151, 171, 191, 0.42);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
  transition: border-color 180ms ease, box-shadow 180ms ease, background 180ms ease, transform 180ms ease;
}

.auth-control:hover {
  border-color: rgba(15, 111, 136, 0.34);
  background: rgba(255, 255, 255, 0.86);
}

.auth-control:focus-within {
  border-color: #0f8aa5;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 0 0 4px rgba(15, 138, 165, 0.12),
    0 14px 28px rgba(24, 64, 87, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.96);
  transform: translateY(-1px);
}

.auth-prefix,
.auth-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.auth-prefix {
  min-width: 56px;
  padding: 0 12px;
  border-right: 1px solid rgba(211, 224, 235, 0.8);
  color: #526273;
  background: linear-gradient(180deg, rgba(246, 250, 251, 0.92), rgba(236, 244, 247, 0.86));
  font-size: 0.86rem;
  font-weight: 700;
}

.auth-action {
  border-left: 1px solid rgba(211, 224, 235, 0.8);
}

input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  padding: 0 14px;
  color: #111827;
  background: transparent;
  font: inherit;
  font-size: 0.95rem;
  font-weight: 620;
}

input::placeholder {
  color: #8a97a8;
  font-weight: 500;
}
</style>

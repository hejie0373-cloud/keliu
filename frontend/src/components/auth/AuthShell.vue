<script setup lang="ts">
import AuthParticleCanvas from './AuthParticleCanvas.vue'

withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: '客留',
    description: '商家经营工作台',
  },
)
</script>

<template>
  <main class="auth-shell">
    <AuthParticleCanvas />
    <div class="auth-aurora auth-aurora-one" aria-hidden="true" />
    <div class="auth-aurora auth-aurora-two" aria-hidden="true" />
    <div class="auth-grid" aria-hidden="true" />

    <section class="auth-center" data-auth-reveal>
      <div class="auth-panel" data-auth-reveal>
        <slot />
      </div>

      <p class="auth-footnote">安全连接 · 邮箱验证 · 商家数据工作台</p>
    </section>
  </main>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: grid;
  place-items: center;
  padding: 44px 20px;
  background:
    radial-gradient(circle at 18% 16%, rgba(25, 170, 151, 0.18), transparent 28%),
    radial-gradient(circle at 82% 14%, rgba(74, 128, 221, 0.16), transparent 30%),
    radial-gradient(circle at 50% 88%, rgba(218, 174, 86, 0.14), transparent 24%),
    linear-gradient(135deg, #f6fbfa 0%, #edf5f8 45%, #f8fafc 100%);
  color: #172033;
}

.auth-shell::before {
  content: '';
  position: absolute;
  inset: -1px;
  background:
    linear-gradient(110deg, rgba(255, 255, 255, 0.88), transparent 36%, rgba(255, 255, 255, 0.48)),
    radial-gradient(circle at 50% 50%, transparent 0 34%, rgba(255, 255, 255, 0.5) 62%, rgba(255, 255, 255, 0.86) 100%);
  pointer-events: none;
  z-index: 0;
}

.auth-aurora {
  position: absolute;
  width: 42vw;
  min-width: 420px;
  aspect-ratio: 1;
  border-radius: 999px;
  filter: blur(28px);
  opacity: 0.55;
  mix-blend-mode: multiply;
  pointer-events: none;
  z-index: 0;
}

.auth-aurora-one {
  left: -12vw;
  top: 9vh;
  background: radial-gradient(circle, rgba(42, 191, 169, 0.22), transparent 62%);
  animation: floatGlow 12s ease-in-out infinite;
}

.auth-aurora-two {
  right: -14vw;
  bottom: -12vh;
  background: radial-gradient(circle, rgba(216, 166, 65, 0.18), transparent 64%);
  animation: floatGlow 15s ease-in-out infinite reverse;
}

.auth-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(15, 111, 136, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 111, 136, 0.055) 1px, transparent 1px);
  background-size: 78px 78px;
  mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.5), transparent 68%);
  pointer-events: none;
  z-index: 0;
}

.auth-center {
  width: min(486px, 100%);
  position: relative;
  z-index: 2;
  display: grid;
  justify-items: center;
  gap: 20px;
  perspective: 1200px;
}

.auth-panel {
  width: 100%;
  position: relative;
  overflow: hidden;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.96), rgba(248, 252, 253, 0.86)),
    rgba(255, 255, 255, 0.9);
  box-shadow:
    0 34px 90px rgba(24, 43, 69, 0.22),
    0 14px 34px rgba(15, 111, 136, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(26px) saturate(1.16);
  transform-style: preserve-3d;
}

.auth-panel::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(217, 173, 85, 0.82), transparent);
}

.auth-panel::after {
  content: '';
  position: absolute;
  width: 180px;
  height: 180px;
  right: -86px;
  top: -86px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(217, 173, 85, 0.14), transparent 68%);
  pointer-events: none;
}

.auth-footnote {
  margin: 0;
  color: #5d6b7c;
  font-size: 0.78rem;
  line-height: 1.6;
  text-align: center;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.75);
}

@keyframes floatGlow {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }

  50% {
    transform: translate3d(5vw, -3vh, 0) scale(1.08);
  }
}

@media (max-width: 520px) {
  .auth-shell {
    place-items: start center;
    padding: 22px 14px 28px;
  }

  .auth-aurora {
    min-width: 300px;
  }

  .auth-panel {
    padding: 22px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-aurora {
    animation: none;
  }
}
</style>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { gsap } from 'gsap'
import {
  AdditiveBlending,
  BufferGeometry,
  Clock,
  Color,
  Float32BufferAttribute,
  PerspectiveCamera,
  Points,
  Scene,
  ShaderMaterial,
  WebGLRenderer,
} from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)

const vertexShader = `
uniform float uTime;
uniform float uPixelRatio;
uniform float uPositionRandom;
uniform float uDepth;
uniform float uFlow;

attribute float aScale;
attribute float aRandom;
attribute float aPhase;
attribute float aOrbit;
attribute vec3 aScatter;
attribute vec3 aColor;

varying vec3 vColor;
varying float vAlpha;

vec3 mod289(vec3 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 mod289(vec4 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 permute(vec4 x) {
  return mod289(((x * 34.0) + 1.0) * x);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

void main() {
  vec3 p = position;
  float flow = uTime * (0.08 + aOrbit * 0.018) + aPhase;
  float noise = snoise(vec3(position.xy * 0.85, flow));
  float pulse = sin(uTime * 1.2 + aPhase) * 0.5 + 0.5;

  p += aScatter * uPositionRandom;
  p.z += aScatter.z * uDepth;
  p += normalize(vec3(position.xy, 0.42)) * noise * uPositionRandom * (0.16 + aRandom * 0.12);

  float orbitSpin = flow * uFlow;
  float s = sin(orbitSpin);
  float c = cos(orbitSpin);
  p.xy = mat2(c, -s, s, c) * p.xy;

  vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  float size = (4.2 + aScale * 7.8 + pulse * 1.6) * uPixelRatio;
  gl_PointSize = size * (1.0 / max(0.2, -mvPosition.z));

  vColor = aColor;
  vAlpha = 0.26 + pulse * 0.44 + (1.0 - clamp(uPositionRandom / 5.8, 0.0, 1.0)) * 0.24;
}
`

const fragmentShader = `
precision mediump float;

varying vec3 vColor;
varying float vAlpha;

void main() {
  vec2 uv = gl_PointCoord - vec2(0.5);
  float dist = length(uv);
  float core = smoothstep(0.5, 0.0, dist);
  float glow = smoothstep(0.5, 0.12, dist) * 0.55;
  float alpha = (core + glow) * vAlpha;

  if (alpha < 0.02) discard;
  gl_FragColor = vec4(vColor, alpha);
}
`

let renderer: WebGLRenderer | null = null
let scene: Scene | null = null
let camera: PerspectiveCamera | null = null
let halo: Points<BufferGeometry, ShaderMaterial> | null = null
let material: ShaderMaterial | null = null
let resizeObserver: ResizeObserver | null = null
let animationId = 0
let pointerX = 0
let pointerY = 0
let reduceMotion = false
let entranceTween: gsap.core.Tween | null = null
const clock = new Clock()

function pushParticle(
  positions: number[],
  scatter: number[],
  scale: number[],
  random: number[],
  phase: number[],
  orbit: number[],
  colors: number[],
  x: number,
  y: number,
  z: number,
  orbitIndex: number,
) {
  const burstRadius = 3.3 + Math.random() * 4.2
  const burstAngle = Math.random() * Math.PI * 2
  const burstHeight = (Math.random() - 0.5) * 4.2
  const palette =
    Math.random() > 0.82
      ? new Color('#d9ad55')
      : Math.random() > 0.38
        ? new Color('#44b7ff')
        : new Color('#16b6a3')

  positions.push(x, y, z)
  scatter.push(
    Math.cos(burstAngle) * burstRadius,
    burstHeight,
    Math.sin(burstAngle) * burstRadius + (Math.random() - 0.5) * 2.4,
  )
  scale.push(Math.random())
  random.push(Math.random())
  phase.push(Math.random() * Math.PI * 2)
  orbit.push(orbitIndex)
  colors.push(palette.r, palette.g, palette.b)
}

function createHaloGeometry(width: number) {
  const positions: number[] = []
  const scatter: number[] = []
  const scale: number[] = []
  const random: number[] = []
  const phase: number[] = []
  const orbit: number[] = []
  const colors: number[] = []

  const compact = width < 768
  const orbitCount = compact ? 4 : 6
  const pointsPerOrbit = compact ? 320 : 560

  for (let lane = 0; lane < orbitCount; lane += 1) {
    const radiusX = 2.65 + lane * 0.22
    const radiusY = 1.2 + lane * 0.1
    const tilt = -0.34 + lane * 0.08

    for (let i = 0; i < pointsPerOrbit; i += 1) {
      const t = (i / pointsPerOrbit) * Math.PI * 2
      const jitter = (Math.random() - 0.5) * 0.075
      const tube = (Math.random() - 0.5) * (compact ? 0.1 : 0.16)
      const x = Math.cos(t + jitter) * radiusX + tube
      const y = Math.sin(t + jitter) * radiusY * Math.cos(tilt) + (Math.random() - 0.5) * 0.05
      const z = Math.sin(t) * radiusY * Math.sin(tilt) + (Math.random() - 0.5) * 0.42

      pushParticle(positions, scatter, scale, random, phase, orbit, colors, x, y, z, lane)
    }
  }

  const ambientCount = compact ? 380 : 780
  for (let i = 0; i < ambientCount; i += 1) {
    const angle = Math.random() * Math.PI * 2
    const r = 1.8 + Math.random() * 3.8
    const x = Math.cos(angle) * r
    const y = (Math.random() - 0.5) * 2.4
    const z = Math.sin(angle) * r * 0.35 + (Math.random() - 0.5) * 1.6

    pushParticle(positions, scatter, scale, random, phase, orbit, colors, x, y, z, orbitCount + 1)
  }

  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  geometry.setAttribute('aScatter', new Float32BufferAttribute(scatter, 3))
  geometry.setAttribute('aScale', new Float32BufferAttribute(scale, 1))
  geometry.setAttribute('aRandom', new Float32BufferAttribute(random, 1))
  geometry.setAttribute('aPhase', new Float32BufferAttribute(phase, 1))
  geometry.setAttribute('aOrbit', new Float32BufferAttribute(orbit, 1))
  geometry.setAttribute('aColor', new Float32BufferAttribute(colors, 3))

  return geometry
}

function sizeRenderer() {
  if (!canvasRef.value || !renderer || !camera || !material) return

  const { width, height } = canvasRef.value.getBoundingClientRect()
  if (width === 0 || height === 0) return

  const pixelRatio = Math.min(window.devicePixelRatio, 2)
  renderer.setPixelRatio(pixelRatio)
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  material.uniforms.uPixelRatio.value = pixelRatio

  if (halo) {
    halo.scale.setScalar(width < 768 ? 0.72 : 1)
  }
}

function renderFrame() {
  if (!renderer || !scene || !camera || !halo || !material) return

  const elapsed = clock.getElapsedTime()
  material.uniforms.uTime.value = elapsed

  halo.rotation.x = -0.26 + pointerY * 0.1
  halo.rotation.y = 0.16 + pointerX * 0.18 + elapsed * 0.015
  halo.rotation.z = -0.09 + Math.sin(elapsed * 0.22) * 0.02

  camera.position.x += (pointerX * 0.28 - camera.position.x) * 0.04
  camera.position.y += (-pointerY * 0.18 - camera.position.y) * 0.04
  camera.lookAt(0, 0, 0)

  renderer.render(scene, camera)
  animationId = window.requestAnimationFrame(renderFrame)
}

function handlePointerMove(event: PointerEvent) {
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  pointerX = (event.clientX - rect.left) / rect.width - 0.5
  pointerY = (event.clientY - rect.top) / rect.height - 0.5
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const width = window.innerWidth

  scene = new Scene()
  camera = new PerspectiveCamera(42, 1, 0.1, 100)
  camera.position.set(0, 0, 7.6)

  material = new ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uTime: { value: 0 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      uPositionRandom: { value: reduceMotion ? 0.85 : 6.2 },
      uDepth: { value: reduceMotion ? 0.75 : 4.8 },
      uFlow: { value: 0.14 },
    },
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    vertexColors: true,
  })

  halo = new Points(createHaloGeometry(width), material)
  halo.position.set(0, 0.05, -0.16)
  scene.add(halo)

  renderer = new WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
  })
  renderer.setClearColor(0x000000, 0)

  resizeObserver = new ResizeObserver(sizeRenderer)
  resizeObserver.observe(canvas)
  canvas.addEventListener('pointermove', handlePointerMove, { passive: true })
  sizeRenderer()
  clock.start()

  if (!reduceMotion) {
    entranceTween = gsap.to(material.uniforms.uPositionRandom, {
      value: 0.34,
      duration: 3,
      ease: 'power3.inOut',
      onUpdate: () => {
        if (material) material.uniforms.uDepth.value = 0.7 + material.uniforms.uPositionRandom.value * 0.18
      },
    })
    gsap.to(material.uniforms.uDepth, {
      value: 0.62,
      duration: 3,
      ease: 'power3.inOut',
    })
  }

  renderFrame()
})

onUnmounted(() => {
  if (animationId) window.cancelAnimationFrame(animationId)
  entranceTween?.kill()
  resizeObserver?.disconnect()
  canvasRef.value?.removeEventListener('pointermove', handlePointerMove)
  halo?.geometry.dispose()
  halo?.material.dispose()
  renderer?.dispose()
  renderer = null
  scene = null
  camera = null
  halo = null
  material = null
  entranceTween = null
})
</script>

<template>
  <canvas ref="canvasRef" class="auth-particles" aria-hidden="true" />
</template>

<style scoped>
.auth-particles {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: auto;
  opacity: 0.95;
  mask-image:
    radial-gradient(ellipse 34% 35% at 50% 50%, transparent 0 48%, rgba(0, 0, 0, 0.34) 62%, #000 100%),
    linear-gradient(#000, #000);
  mask-composite: add;
}
</style>

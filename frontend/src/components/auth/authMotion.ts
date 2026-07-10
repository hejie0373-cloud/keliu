import { gsap } from 'gsap'

function reduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function revealAuthSurface(root: HTMLElement | null) {
  if (!root || reduceMotion()) return () => undefined

  const cleanupFns: Array<() => void> = []

  const ctx = gsap.context(() => {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

    tl.from('[data-auth-reveal]', {
      autoAlpha: 0,
      y: 28,
      rotationX: -4,
      duration: 0.8,
      stagger: 0.11,
    })
      .from(
        '[data-auth-item]',
        {
          autoAlpha: 0,
          y: 16,
          scale: 0.985,
          duration: 0.54,
          stagger: 0.06,
        },
        '-=0.45',
      )
      .from(
        '.brand-emblem',
        {
          scale: 0.82,
          rotation: -8,
          duration: 0.56,
          ease: 'back.out(1.8)',
        },
        '-=0.62',
      )

    const panel = root.querySelector<HTMLElement>('.auth-panel')
    const buttons = gsap.utils.toArray<HTMLElement>('.primary-btn', root)

    if (panel) {
      const rotateX = gsap.quickTo(panel, 'rotationX', { duration: 0.45, ease: 'power3.out' })
      const rotateY = gsap.quickTo(panel, 'rotationY', { duration: 0.45, ease: 'power3.out' })
      const y = gsap.quickTo(panel, 'y', { duration: 0.45, ease: 'power3.out' })

      const movePanel = (event: PointerEvent) => {
        const rect = panel.getBoundingClientRect()
        const px = (event.clientX - rect.left) / rect.width - 0.5
        const py = (event.clientY - rect.top) / rect.height - 0.5
        rotateX(py * -4)
        rotateY(px * 5)
        y(-3)
      }

      const resetPanel = () => {
        rotateX(0)
        rotateY(0)
        y(0)
      }

      panel.addEventListener('pointermove', movePanel, { passive: true })
      panel.addEventListener('pointerleave', resetPanel)
      cleanupFns.push(() => {
        panel.removeEventListener('pointermove', movePanel)
        panel.removeEventListener('pointerleave', resetPanel)
      })
    }

    buttons.forEach((button) => {
      const enter = () => {
        gsap.to(button, {
          y: -2,
          scale: 1.01,
          duration: 0.22,
          ease: 'power2.out',
          overwrite: 'auto',
        })
      }
      const leave = () => {
        gsap.to(button, {
          y: 0,
          scale: 1,
          duration: 0.24,
          ease: 'power2.out',
          overwrite: 'auto',
        })
      }

      button.addEventListener('pointerenter', enter)
      button.addEventListener('pointerleave', leave)
      cleanupFns.push(() => {
        button.removeEventListener('pointerenter', enter)
        button.removeEventListener('pointerleave', leave)
      })
    })
  }, root)

  return () => {
    cleanupFns.forEach((cleanup) => cleanup())
    ctx.revert()
  }
}

export function pulsePanel(target: HTMLElement | null) {
  if (!target || reduceMotion()) return

  gsap.fromTo(
    target,
    { autoAlpha: 0, y: 16, scale: 0.985 },
    { autoAlpha: 1, y: 0, scale: 1, duration: 0.34, ease: 'power3.out', overwrite: 'auto' },
  )
}

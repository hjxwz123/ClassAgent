<template>
  <svg
    class="brand-logo"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="50 54 300 244"
    aria-hidden="true"
    focusable="false"
  >
    <defs>
      <linearGradient id="brand-logo-cyan-data" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#00E5FF" />
        <stop offset="100%" stop-color="#00B8D4" />
      </linearGradient>

      <mask id="brand-logo-corner-cutout" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="400">
        <rect width="400" height="400" fill="white" />
        <circle cx="260" cy="140" r="54" fill="black" />
      </mask>

      <filter id="brand-logo-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="6" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <g transform="translate(0, -10)">
      <rect
        x="80"
        y="140"
        width="180"
        height="130"
        rx="16"
        fill="none"
        stroke="currentColor"
        stroke-width="14"
        mask="url(#brand-logo-corner-cutout)"
      />
      <line x1="120" y1="180" x2="200" y2="180" stroke="currentColor" stroke-width="12" stroke-linecap="round" />
      <rect x="212" y="172" width="16" height="16" rx="4" transform="rotate(45 220 180)" fill="currentColor" />
      <rect x="247" y="127" width="26" height="26" rx="6" transform="rotate(45 260 140)" fill="#00B8D4" />
      <rect
        x="282"
        y="82"
        width="36"
        height="36"
        rx="8"
        transform="rotate(45 300 100)"
        fill="url(#brand-logo-cyan-data)"
        filter="url(#brand-logo-glow)"
      />
    </g>
  </svg>
</template>

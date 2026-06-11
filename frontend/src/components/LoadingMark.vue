<template>
  <svg class="loading-mark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" aria-hidden="true">
    <defs>
      <filter id="loading-mark-node-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <g transform="translate(0, -10)">
      <line x1="50" y1="150" x2="150" y2="50" stroke="#2C2B29" stroke-width="4" stroke-linecap="round" />

      <g transform="translate(75, 125)">
        <rect x="-8" y="-8" width="16" height="16" rx="3" transform="rotate(45 0 0)" fill="#F4F4F0">
          <animate attributeName="opacity" values="0.2; 1; 0.2" dur="1.5s" keyTimes="0; 0.2; 1" repeatCount="indefinite" />
          <animateTransform attributeName="transform" type="scale" values="1; 1.2; 1" dur="1.5s" keyTimes="0; 0.2; 1" additive="sum" repeatCount="indefinite" />
        </rect>
      </g>

      <g transform="translate(100, 100)">
        <rect x="-11" y="-11" width="22" height="22" rx="4" transform="rotate(45 0 0)" fill="#00B8D4">
          <animate attributeName="opacity" values="0.2; 1; 0.2" dur="1.5s" keyTimes="0; 0.35; 1" repeatCount="indefinite" />
          <animateTransform attributeName="transform" type="scale" values="1; 1.2; 1" dur="1.5s" keyTimes="0; 0.35; 1" additive="sum" repeatCount="indefinite" />
        </rect>
      </g>

      <g transform="translate(125, 75)">
        <rect x="-14" y="-14" width="28" height="28" rx="6" transform="rotate(45 0 0)" fill="#00E5FF" filter="url(#loading-mark-node-glow)">
          <animate attributeName="opacity" values="0.2; 1; 0.2" dur="1.5s" keyTimes="0; 0.5; 1" repeatCount="indefinite" />
          <animateTransform attributeName="transform" type="scale" values="1; 1.2; 1" dur="1.5s" keyTimes="0; 0.5; 1" additive="sum" repeatCount="indefinite" />
        </rect>
      </g>

      <circle r="3" fill="#FFFFFF" filter="url(#loading-mark-node-glow)">
        <animateMotion dur="1.5s" repeatCount="indefinite" path="M 50 150 L 150 50" keyTimes="0; 0.6; 1" keyPoints="0; 1; 1" calcMode="linear" />
        <animate attributeName="opacity" values="0; 1; 0; 0" keyTimes="0; 0.1; 0.5; 1" dur="1.5s" repeatCount="indefinite" />
      </circle>
    </g>

    <text v-if="label" x="100" y="175" font-family="'ClassAgent Mono', SFMono-Regular, Consolas, monospace" font-size="10" font-weight="700" fill="#666560" text-anchor="middle" letter-spacing="5">
      LOADING
      <animate attributeName="opacity" values="0.3; 1; 0.3" dur="1.5s" repeatCount="indefinite" />
    </text>
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label?: boolean }>(), {
  label: true,
});
</script>

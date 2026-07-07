// 从 StudentView.vue 抽出的下拉气泡按钮。自带 document 监听关闭，无父作用域响应式闭包。
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, Transition, type PropType } from "vue";
import { ChevronDown } from "../../../icons";

type SelectOption = { label: string; value: string | number; danger?: boolean };

export const PopoverButton = defineComponent({
  props: {
    label: { type: String, required: true },
    items: { type: Array as PropType<SelectOption[]>, default: () => [] },
    placement: { type: String as PropType<"top" | "bottom">, default: "bottom" }
  },
  emits: ["select"],
  setup(p, { emit: update }) {
    const open = ref(false);
    const root = ref<HTMLElement | null>(null);
    function close() { open.value = false; }
    function onPointerDown(event: PointerEvent) { if (!root.value?.contains(event.target as Node)) close(); }
    function onKeydown(event: KeyboardEvent) { if (event.key === "Escape") close(); }
    onMounted(() => {
      document.addEventListener("pointerdown", onPointerDown);
      document.addEventListener("keydown", onKeydown);
    });
    onBeforeUnmount(() => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeydown);
    });
    const popStyle = computed(() => p.placement === "top" ? {
      top: "auto",
      right: "0",
      bottom: "calc(100% + 10px)",
      transformOrigin: "bottom center"
    } : undefined);
    return () => h("div", { ref: root, class: ["popover-button select-menu", `placement-${p.placement}`] }, [
      h("button", {
        type: "button",
        "aria-haspopup": "listbox",
        "aria-expanded": open.value,
        onClick: () => { open.value = !open.value; },
        onKeydown: (event: KeyboardEvent) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            open.value = !open.value;
          }
        }
      }, [p.label, h(ChevronDown, { size: 14 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop", role: "listbox", style: popStyle.value }, p.items.map((item) => h("button", { type: "button", role: "option", key: item.value, onClick: () => { update("select", String(item.value)); open.value = false; } }, item.label))) : null
      })
    ]);
  }
});

import { defineComponent, h, onBeforeUnmount, onMounted, ref, Transition, type PropType } from "vue";
import { MoreHorizontal } from "lucide-vue-next";
import type { SelectMenuOption } from "./SelectMenu";

export default defineComponent({
  name: "DropdownMenu",
  props: { items: { type: Array as PropType<SelectMenuOption[]>, default: () => [] } },
  emits: ["select"],
  setup(p, { emit }) {
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
    return () => h("div", { ref: root, class: "dropdown-menu" }, [
      h("button", {
        type: "button",
        class: "dropdown-trigger",
        "aria-label": "更多操作",
        "aria-haspopup": "menu",
        "aria-expanded": open.value,
        onClick: () => { open.value = !open.value; },
        onKeydown: (event: KeyboardEvent) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            open.value = !open.value;
          }
        }
      }, [h(MoreHorizontal, { size: 16 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "dropdown-pop", role: "menu" }, p.items.map((item) =>
          h("button", {
            type: "button",
            key: item.value,
            role: "menuitem",
            class: { danger: item.danger },
            onClick: () => { emit("select", item.value); open.value = false; }
          }, item.label)
        )) : null
      })
    ]);
  }
});

import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, Transition, type PropType } from "vue";
import { ChevronDown } from "../icons";

export type SelectMenuOption = { label: string; value: string | number; danger?: boolean };

function normalizeItems(items: Array<string | SelectMenuOption>): SelectMenuOption[] {
  return items.map((item) => (typeof item === "string" ? { label: item, value: item } : item));
}

export default defineComponent({
  name: "SelectMenu",
  props: {
    modelValue: { type: [String, Number], default: "" },
    items: { type: Array as PropType<Array<string | SelectMenuOption>>, default: () => [] }
  },
  emits: ["update:modelValue"],
  setup(p, { emit }) {
    const open = ref(false);
    const root = ref<HTMLElement | null>(null);
    const options = computed(() => normalizeItems(p.items));
    const current = computed(() => options.value.find((item) => item.value === p.modelValue)?.label || options.value[0]?.label || "请选择");
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
    return () => h("div", { ref: root, class: "select-menu" }, [
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
      }, [h("span", current.value), h(ChevronDown, { size: 15 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop", role: "listbox" }, options.value.map((item) =>
          h("button", {
            type: "button",
            key: item.value,
            role: "option",
            "aria-selected": item.value === p.modelValue,
            class: { active: item.value === p.modelValue },
            onClick: () => { emit("update:modelValue", item.value); open.value = false; }
          }, item.label)
        )) : null
      })
    ]);
  }
});

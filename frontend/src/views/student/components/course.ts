// 从 StudentView.vue 抽出的课程相关小组件。原本闭包引用页面状态（selectedCourseId/courses/joinOpen）
// 与页面动作（loadActive/previewMaterial/downloadMaterial），抽出时改为 props + emits 契约，解除耦合。
import { defineComponent, h, type PropType } from "vue";
import { BookOpen, Download, Eye, FileText, Plus } from "../../../icons";
import { optionText } from "../../../utils/quiz";
import SelectMenu from "../../../components/SelectMenu";

// 顶部课程切换下拉。v-model 绑定当前课程 id；选中同一门课时 emit reload（重新拉取当前课程）；无课程时 emit join。
export const CourseSelect = defineComponent({
  props: {
    modelValue: { type: [Number, String] as PropType<number | string>, default: "" },
    courses: { type: Array as PropType<any[]>, default: () => [] }
  },
  emits: ["update:modelValue", "reload", "join"],
  setup(p, { emit: update }) {
    function updateCourse(value: string | number) {
      const nextId = Number(value);
      if (nextId === Number(p.modelValue)) {
        update("reload");
        return;
      }
      update("update:modelValue", nextId);
    }
    return () => p.courses.length
      ? h("div", { class: "course-select" }, [
        h(SelectMenu, {
          modelValue: p.modelValue,
          items: p.courses.map((course) => ({ label: course.name, value: course.id })),
          "onUpdate:modelValue": updateCourse
        })
      ])
      : h("button", { type: "button", class: "select-menu-empty", onClick: () => update("join") }, [h(Plus, { size: 14 }), "加入课程"]);
  }
});

// 未加入课程时的占位卡，点击 emit join。
export const CourseRequired = defineComponent({
  emits: ["join"],
  setup(_p, { emit: update }) {
    return () => h("article", { class: "panel-card empty" }, [
      h(BookOpen, { size: 36 }),
      h("strong", "先加入课程"),
      h("button", { type: "button", class: "btn btn-primary", onClick: () => update("join") }, [h(Plus, { size: 16 }), "加入课程"])
    ]);
  }
});

// 课程资料行，预览/下载动作 emit 回父层处理。
export const MaterialRow = defineComponent({
  props: { item: { type: Object as PropType<any>, required: true } },
  emits: ["preview", "download"],
  setup(p, { emit: update }) {
    return () => h("div", { class: "material-row" }, [
      h("span", { class: "file-badge" }, [h(FileText, { size: 16 })]),
      h("div", [h("strong", p.item.title || p.item.original_filename || "课程资料"), h("small", `${p.item.material_type || "file"} · ${p.item.size_label || optionText(p.item.size_bytes || 0)}`)]),
      h("div", { class: "material-row-actions" }, [
        h("button", { type: "button", class: "material-row-action primary", onClick: () => update("preview", p.item) }, [h(Eye, { size: 14 }), "预览"]),
        h("button", { type: "button", class: "material-row-action", onClick: () => update("download", p.item) }, [h(Download, { size: 14 }), "下载"])
      ])
    ]);
  }
});

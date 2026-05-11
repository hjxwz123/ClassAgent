import { copyToClipboard } from "./clipboard";

const copySelector = "[data-markdown-copy-code]";
let installed = false;

function setButtonState(button: HTMLButtonElement, text: string, state: "idle" | "copied" | "failed") {
  button.textContent = text;
  button.dataset.copyState = state;
}

export function installMarkdownCodeCopy() {
  if (installed || typeof document === "undefined") return;
  installed = true;

  document.addEventListener("click", async (event) => {
    const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>(copySelector) : null;
    if (!target) return;

    const frame = target.closest(".markdown-code-frame");
    const code = frame?.querySelector("pre code")?.textContent || "";
    if (!code) {
      setButtonState(target, "复制失败", "failed");
      window.setTimeout(() => setButtonState(target, "复制", "idle"), 1200);
      return;
    }

    const copied = await copyToClipboard(code);
    setButtonState(target, copied ? "已复制" : "复制失败", copied ? "copied" : "failed");
    window.setTimeout(() => setButtonState(target, "复制", "idle"), 1200);
  });
}

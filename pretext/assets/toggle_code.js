// Toggle Python Code - adds show/hide buttons to Python code blocks
(function () {
    "use strict";

    function injectStyles() {
        const style = document.createElement("style");
        style.textContent =
            ".toggle-code-btn {" +
            "  display: block;" +
            "  margin-bottom: 4px;" +
            "  padding: 2px 10px;" +
            "  cursor: pointer;" +
            "  font-size: 0.85em;" +
            "  background: #f5f5f5;" +
            "  border: 1px solid #ccc;" +
            "  border-radius: 3px;" +
            "  color: #333;" +
            "}" +
            ".toggle-code-btn:hover { background: #e8e8e8; }";
        document.head.appendChild(style);
    }

    function addToggleButtons() {
        const codeBoxes = document.querySelectorAll("div.code-box");
        if (codeBoxes.length === 0) {
            return;
        }

        injectStyles();

        codeBoxes.forEach(function (codeBox) {
            const pre = codeBox.querySelector("pre.program");
            if (!pre) {
                return;
            }

            const btn = document.createElement("button");
            btn.textContent = "Hide Code";
            btn.className = "toggle-code-btn";
            btn.setAttribute("aria-expanded", "true");

            btn.addEventListener("click", function () {
                const isExpanded = btn.getAttribute("aria-expanded") === "true";
                pre.style.display = isExpanded ? "none" : "";
                btn.textContent = isExpanded ? "Show Code" : "Hide Code";
                btn.setAttribute("aria-expanded", isExpanded ? "false" : "true");
            });

            codeBox.insertBefore(btn, codeBox.firstChild);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addToggleButtons);
    } else {
        addToggleButtons();
    }
})();

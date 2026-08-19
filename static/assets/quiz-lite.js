// Self-contained quiz for the static site: grades in the browser, stores nothing.
// (The learn-server quiz widget is deliberately not shipped here — its persistence
// API doesn't exist on a static host.)
window.initQuizLite = (root) => {
  root.querySelectorAll('.q[data-type="mcq"]').forEach((q) => {
    const key = parseInt(q.dataset.answer, 10);
    const lis = [...q.querySelectorAll(".choices > li")];
    lis.forEach((li, i) => {
      li.tabIndex = 0;
      const pick = () => {
        if (q.dataset.done) return;
        q.dataset.done = "1";
        lis[key].classList.add("correct");
        if (i !== key) li.classList.add("wrong");
      };
      li.addEventListener("click", pick);
      li.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); }
      });
    });
  });
  root.querySelectorAll('.q[data-type="recall"]').forEach((q) => {
    const ans = q.querySelector(".answer");
    if (!ans) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "reveal";
    btn.textContent = "Show answer";
    btn.addEventListener("click", () => {
      const open = ans.classList.toggle("open");
      btn.textContent = open ? "Hide answer" : "Show answer";
    });
    ans.before(btn);
  });
};

// 좋아요는 같은 출처에만 전송하며, 글 작성 중인 입력값을 유지합니다.
document.querySelectorAll(".like-form").forEach((form) => {
  const button = form.querySelector("button");
  const target = form.elements.namedItem("liked");
  const feedback = form.parentElement.querySelector(".social-feedback");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (button.disabled) return;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    feedback.hidden = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
        body: new URLSearchParams({ liked: target.value }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "좋아요를 저장하지 못했어요.");
      button.setAttribute("aria-pressed", String(result.liked));
      button.querySelector("[data-like-icon]").textContent = result.liked ? "♥" : "♡";
      button.querySelector("[data-like-count]").textContent = result.count;
      target.value = result.liked ? "false" : "true";
      feedback.textContent = result.liked ? "마음이 전해졌어요." : "좋아요를 해제했어요.";
      feedback.hidden = false;
    } catch (error) {
      feedback.textContent = error instanceof TypeError
        ? "연결을 확인해주세요. 새로고침하면 저장 상태를 확인할 수 있어요."
        : error.message;
      feedback.hidden = false;
    } finally {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  });
});
